"""
基准测试 API - GAOKAO-Bench 高考题数据集评测

功能:
1. 导入 GAOKAO-Bench 数据集（支持本地文件和GitHub URL）
2. 批量运行模型回答
3. 自动对比标准答案评分
4. 错题/低分题快速进入自我迭代
5. 生成详细评测报告
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, String
from typing import List, Optional, Dict
from pydantic import BaseModel
import httpx
import json
import asyncio
import os
import re
from datetime import datetime

from app.core.database import get_session as get_async_session, AsyncSessionLocal
from app.core.config import settings
from app.services.experts.llm_service import llm_service
from app.services.experts.expert_pool import expert_pool
from app.services.iteration.quality_checker import quality_checker
from app.services.iteration.data_generator import data_generator
from app.services.iteration.knowledge_generator import knowledge_generator
from app.services.benchmark.report_saver import report_saver
from app.models.database import BenchmarkDataset, BenchmarkResult, Expert, Knowledge

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


# ============= 选择题模板生成 =============

async def generate_choice_template(
    question: str,
    correct_answer: str,
    model_answer: str,
    subject: str
) -> str:
    """
    生成选择题的标准解题模板范式
    
    包含：
    1. 题目类型识别
    2. 涉及知识点
    3. 解题思路/步骤
    4. 标准解答过程
    5. 易错点提示
    """
    
    system_prompt = f"""你是一位{subject}学科的专家教师，擅长将具体题目的解法提炼为标准解题模板。

任务：将这道选择题的解答过程，转化为**可复用的解题模板范式**。

模板必须包含以下结构：

## 一、题目类型识别
- 题型归类（如：三角函数求值、导数应用、立体几何证明等）
- 核心考查点

## 二、涉及知识点
- 列出本题涉及的所有公式、定理、概念
- 标注重点公式

## 三、解题思路/通用步骤
提供解决这类题的**标准思维路径**：
1. 第一步：...
2. 第二步：...
3. ...

## 四、本题详细解答
基于上述思路，给出本题的具体解答：
- 推导过程（详细数学步骤）
- 最终答案

## 五、易错点与技巧
- 常见错误警示
- 快速解题技巧
- 同类题变式提示

要求：
- 使用 LaTeX 格式书写数学公式
- 语言简洁专业，便于学生理解和记忆
- 模板应能套用到同类题目上"""

    user_prompt = f"""【题目】
{question}

【标准答案】
{correct_answer}

【学生/系统的错误答案】
{model_answer}

请按照上述模板结构，生成标准解题范式。"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.CLOUD_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.CLOUD_API_KEY}"},
                json={
                    "model": settings.CLOUD_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2500
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[GenerateTemplate] 生成模板失败: {e}")
        # 失败时返回基础模板
        return f"""## 参考答案
{correct_answer}

## 解析
{model_answer}

## 提示
本题涉及相关{subject}知识点，建议复习对应章节。"""


# ============= 数据模型 =============

class ImportDatasetRequest(BaseModel):
    source: str  # "local" | "github"
    path: Optional[str] = None  # 本地路径或GitHub URL
    subject: Optional[str] = None  # 指定学科，为null则导入全部


class StartTestRequest(BaseModel):
    expert_id: Optional[int] = None  # 为null则自动路由
    mode: str = "all"  # all, wrong, random, by_subject
    subject: Optional[str] = None  # 按学科测试
    year: Optional[str] = None  # 按年份测试
    
    # 实验控制参数（简化版：use_rag 控制是否使用知识库检索）
    experiment_id: Optional[str] = None  # 关联的实验ID
    random_seed: Optional[int] = None  # 随机种子（控制数据集shuffle）
    use_rag: bool = True  # 是否使用RAG知识检索（RAGOnly/FullSystem启用，Baseline/ExpertOnly禁用）
    use_expert_routing: bool = True  # 是否使用专家路由（ExpertOnly/FullSystem启用，Baseline/RAGOnly禁用）
    enable_iteration: bool = False  # 是否启用迭代/自动入库（默认禁用，仅FullSystem应显式启用）
    max_questions: Optional[int] = None  # 最大题目数
    use_experiment_dataset: bool = False  # 是否使用实验数据集（50题）


class AddToIterationRequest(BaseModel):
    result_ids: List[int]


class BenchmarkStats(BaseModel):
    total_questions: int
    correct_count: int
    wrong_count: int
    accuracy_rate: float
    avg_score: float
    by_subject: Dict[str, int]


class TestProgress(BaseModel):
    status: str  # running, completed, error
    current: int
    total: int
    current_question: str
    elapsed_time: int


# ============= 全局状态 =============

# 当前测试任务状态
current_test_task = {
    "is_running": False,
    "expert_id": None,
    "mode": "all",
    "total": 0,
    "current": 0,
    "current_question": "",
    "start_time": None,
    "error": None,
    "stopped": False,  # 是否被手动停止
    "task": None,  # 保存后台任务引用，用于强制取消
    "experiment_id": None,  # 关联的实验ID
    "config": {}  # 实验配置
}

# GAOKAO-Bench 数据集本地路径
# 优先从环境变量读取，否则使用默认路径
GAOKAO_BENCH_PATH = os.environ.get(
    "GAOKAO_BENCH_PATH", 
    "/Users/zizixiuixu/Downloads/GAOKAO-Bench-main"
)

# 学科映射
SUBJECT_MAPPING = {
    "Biology": "生物",
    "Chemistry": "化学", 
    "Chinese": "语文",
    "English": "英语",
    "Geography": "地理",
    "History": "历史",
    "Math": "数学",
    "Physics": "物理",
    "Political_Science": "政治"
}


# ============= API 路由 =============

@router.get("/stats", response_model=BenchmarkStats)
async def get_benchmark_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """获取基准测试统计数据"""
    # 统计总数
    total_result = await session.execute(select(func.count(BenchmarkDataset.id)))
    total_questions = total_result.scalar() or 0
    
    # 统计正确数
    correct_result = await session.execute(
        select(func.count(BenchmarkResult.id))
        .where(BenchmarkResult.is_correct == True)
    )
    correct_count = correct_result.scalar() or 0
    
    # 统计平均分
    score_result = await session.execute(
        select(func.avg(BenchmarkResult.overall_score))
    )
    avg_score = score_result.scalar() or 0
    
    # 已测试的题目数
    tested_result = await session.execute(select(func.count(BenchmarkResult.id)))
    tested_count = tested_result.scalar() or 0
    
    accuracy_rate = 0
    if tested_count > 0:
        accuracy_rate = round((correct_count / tested_count) * 100, 1)
    
    # 按学科统计
    subject_stats = {}
    for subject_cn in SUBJECT_MAPPING.values():
        count_result = await session.execute(
            select(func.count(BenchmarkDataset.id))
            .where(BenchmarkDataset.subject == subject_cn)
        )
        subject_stats[subject_cn] = count_result.scalar() or 0
    
    return BenchmarkStats(
        total_questions=total_questions,
        correct_count=correct_count,
        wrong_count=tested_count - correct_count,
        accuracy_rate=accuracy_rate,
        avg_score=round(avg_score, 2),
        by_subject=subject_stats
    )


@router.post("/import")
async def import_dataset(
    request: ImportDatasetRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    导入 GAOKAO-Bench 数据集
    
    支持:
    1. 本地导入: source="local", path=数据集根目录
    2. GitHub导入: source="github", path=原始文件URL
    """
    try:
        imported_count = 0
        
        if request.source == "local":
            # 本地文件导入
            base_path = request.path or GAOKAO_BENCH_PATH
            imported_count = await _import_from_local(session, base_path, request.subject)
        else:
            # GitHub URL导入（单文件）
            if not request.path:
                raise HTTPException(status_code=400, detail="请提供GitHub URL")
            imported_count = await _import_from_github(session, request.path)
        
        return {
            "success": True,
            "imported_count": imported_count,
            "message": f"成功导入 {imported_count} 道题目"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.get("/datasets/info")
async def get_dataset_info():
    """获取本地 GAOKAO-Bench 数据集信息"""
    try:
        data_path = os.path.join(GAOKAO_BENCH_PATH, "Data", "Objective_Questions")
        
        if not os.path.exists(data_path):
            return {
                "exists": False,
                "message": "未找到本地数据集",
                "path": GAOKAO_BENCH_PATH
            }
        
        # 扫描文件
        files = []
        total_questions = 0
        
        for filename in os.listdir(data_path):
            if filename.endswith('.json'):
                filepath = os.path.join(data_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        count = len(data.get('example', []))
                        
                        # 解析学科
                        subject_en = filename.replace('2010-2022_', '').replace('_MCQs.json', '')
                        # 处理 Math_I 和 Math_II 映射到数学
                        if subject_en.startswith('Math'):
                            subject_en = 'Math'
                        subject_cn = SUBJECT_MAPPING.get(subject_en, subject_en)
                        
                        files.append({
                            "filename": filename,
                            "subject_en": subject_en,
                            "subject_cn": subject_cn,
                            "count": count
                        })
                        total_questions += count
                except Exception as e:
                    print(f"读取文件失败 {filename}: {e}")
        
        return {
            "exists": True,
            "path": GAOKAO_BENCH_PATH,
            "total_files": len(files),
            "total_questions": total_questions,
            "files": files
        }
        
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }


@router.post("/start")
async def start_benchmark(
    request: StartTestRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """启动基准测试 - 严格的重复提交检查"""
    global current_test_task
    
    # 严格检查：如果is_running为true，检查任务是否真的在运行
    if current_test_task["is_running"]:
        task = current_test_task.get("task")
        if task and not task.done():
            raise HTTPException(status_code=400, detail="已有测试正在进行")
        else:
            # 任务已结束但状态未重置，先重置状态
            print("[Benchmark] 检测到僵死任务，自动重置状态")
            current_test_task["is_running"] = False
            current_test_task["task"] = None
    
    # 再次检查，确保没有并发启动
    if current_test_task["is_running"]:
        raise HTTPException(status_code=400, detail="已有测试正在进行")
    
    # ==================== 实验模式识别与日志 ====================
    print("\n" + "="*60)
    print("[🧪 实验启动] 配置详情")
    print("="*60)
    
    # 判断实验模式（简化：只用 use_rag 和 use_expert_routing 两个开关）
    exp_mode_name = "未知模式"
    if not request.use_expert_routing and not request.use_rag:
        exp_mode_name = "📊 Baseline 基线（无路由无RAG）"
    elif request.use_expert_routing and not request.use_rag:
        exp_mode_name = "🔀 ExpertOnly 专家路由（有路由无RAG）"
    elif not request.use_expert_routing and request.use_rag:
        exp_mode_name = "📚 RAGOnly RAG增强（无路由有RAG）"
    elif request.use_expert_routing and request.use_rag:
        if request.enable_iteration:
            exp_mode_name = "🔄 FullSystem 完整系统（含自进化）"
        else:
            exp_mode_name = "✅ FullSystem 完整系统（无自进化）"
    else:
        exp_mode_name = "⚙️ 自定义配置"
    
    print(f"[模式识别] {exp_mode_name}")
    print(f"[实验ID] {request.experiment_id or 'N/A'}")
    print(f"[题目配置] 随机种子={request.random_seed}, 数量={request.max_questions or '全部'}")
    print("-"*60)
    print("[开关状态]")
    print(f"  ├─ 专家路由 (use_expert_routing): {'✅ 启用' if request.use_expert_routing else '❌ 禁用'}")
    print(f"  ├─ RAG知识检索 (use_rag): {'✅ 启用' if request.use_rag else '❌ 禁用'}")
    print(f"  └─ 自动入库/迭代 (enable_iteration): {'✅ 启用' if request.enable_iteration else '❌ 禁用'}")
    print("-"*60)
    
    # 实验目的提示
    if not request.use_expert_routing and not request.use_rag:
        print("[实验目的] 测量基线准确率（纯模型能力，无增强）")
    elif request.use_expert_routing and not request.use_rag:
        print("[实验目的] 测量专家路由贡献度（vs Baseline）")
    elif not request.use_expert_routing and request.use_rag:
        print("[实验目的] 测量RAG独立贡献度（vs Baseline）")
    elif request.use_expert_routing and request.use_rag and not request.enable_iteration:
        print("[实验目的] 测量完整系统初始性能（无自进化）")
    elif request.use_expert_routing and request.use_rag and request.enable_iteration:
        print("[实验目的] 测量自进化效果（迭代后 vs 迭代前）")
    
    print("="*60 + "\n")
    
    # 验证专家（如果指定了）
    expert = None
    if request.expert_id:
        expert = await session.get(Expert, request.experiment_id)
        if not expert:
            raise HTTPException(status_code=404, detail="专家不存在")
    
    # 构建查询 - 支持实验数据集
    print(f"[DEBUG] use_experiment_dataset={request.use_experiment_dataset}")
    if request.use_experiment_dataset:
        # 从实验数据集读取
        from sqlalchemy import text
        result = await session.execute(text("SELECT id, question, correct_answer, subject, year, category, analysis FROM experiment_dataset ORDER BY RANDOM() LIMIT 50"))
        rows = result.fetchall()
        questions = []
        for row in rows:
            # 创建临时的BenchmarkDataset对象
            q = BenchmarkDataset(
                id=row[0],
                question=row[1],
                correct_answer=row[2],
                subject=row[3],
                year=row[4],
                category=row[5],
                analysis=row[6],
                difficulty="medium",
                question_type="objective"
            )
            questions.append(q)
        print(f"[Benchmark] 从实验数据集读取 {len(questions)} 题")
    else:
        # 从标准数据集读取
        query = select(BenchmarkDataset)
        
        if request.subject:
            query = query.where(BenchmarkDataset.subject == request.subject)
        if request.year:
            query = query.where(BenchmarkDataset.year == request.year)
        
        # 先获取所有符合条件的题目（不限制数量）
        result = await session.execute(query)
        questions = list(result.scalars().all())
    
    # 应用随机种子打乱顺序（Python层面实现）
    if request.random_seed is not None:
        import random
        rng = random.Random(request.random_seed)
        rng.shuffle(questions)
        print(f"[Benchmark] 使用随机种子 {request.random_seed}，打乱顺序后选取")
    else:
        print(f"[Benchmark] 未使用随机种子，按数据库顺序选取")
    
    # 限制题目数量（在打乱后限制）
    if request.max_questions and len(questions) > request.max_questions:
        questions = questions[:request.max_questions]
    elif request.mode == "random" and len(questions) > 100:
        questions = questions[:100]
    
    if not questions:
        raise HTTPException(status_code=400, detail="没有可用的测试题目")
    
    # 🔥 关键修复：确保前一个实验的完成状态被持久化，再启动新实验
    if current_test_task["is_running"]:
        print("[Benchmark] 警告：已有实验在运行，等待其完成...")
        # 等待一小段时间，让前一个实验完成
        await asyncio.sleep(3)
    
    # 🔥 关键修复：保存前一个实验的完成状态（如果已完成）
    previous_completed = (
        not current_test_task["is_running"] and 
        current_test_task["current"] > 0 and 
        current_test_task["current"] >= current_test_task["total"]
    )
    
    # 初始化任务状态 - 完全重置所有字段
    current_test_task.clear()
    current_test_task.update({
        "is_running": True,
        "expert_id": request.expert_id,
        "mode": request.mode,
        "total": len(questions),
        "current": 0,
        "current_question": f"开始实验: {request.experiment_id or 'N/A'}",
        "start_time": datetime.now(),
        "error": None,
        "stopped": False,
        "experiment_id": request.experiment_id,
        "config": {
            "random_seed": request.random_seed,
            "use_rag": request.use_rag,
            "use_expert_routing": request.use_expert_routing,
            "enable_iteration": request.enable_iteration,
            "max_questions": request.max_questions
        },
        "task": None,
        "previous_completed": previous_completed  # 标记前一个实验已完成
    })
    
    # 后台运行测试
    task = asyncio.create_task(run_benchmark_test(
        questions, 
        request.expert_id,
        request.experiment_id,
        request.use_rag,
        request.use_expert_routing,
        request.enable_iteration
    ))
    current_test_task["task"] = task
    
    return {
        "success": True,
        "message": f"测试已启动，共 {len(questions)} 道题目"
    }


@router.post("/stop")
async def stop_benchmark():
    """停止当前基准测试"""
    global current_test_task
    
    if not current_test_task["is_running"]:
        # 检查是否有僵死任务
        task = current_test_task.get("task")
        if task and task.done():
            # 清理僵死状态
            current_test_task["is_running"] = False
            current_test_task["task"] = None
            return {"success": False, "message": "之前的测试已结束，状态已重置"}
        return {"success": False, "message": "当前没有正在进行的测试"}
    
    stopped_at = current_test_task["current"]
    current_test_task["stopped"] = True
    current_test_task["is_running"] = False
    
    # 尝试取消后台任务
    task = current_test_task.get("task")
    if task and not task.done():
        task.cancel()
        print(f"[Benchmark] 已取消后台任务，当前进度: {stopped_at}")
    
    return {
        "success": True,
        "message": "测试已停止",
        "stopped_at": stopped_at
    }


@router.post("/reset")
async def reset_benchmark():
    """重置基准测试状态（解决状态卡住问题）"""
    global current_test_task
    
    # 如果有一个正在运行的任务，尝试取消它
    task = current_test_task.get("task")
    if task and not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    
    # 保存当前进度信息用于返回
    was_running = current_test_task["is_running"]
    previous_progress = current_test_task["current"]
    previous_total = current_test_task["total"]
    
    current_test_task = {
        "is_running": False,
        "expert_id": None,
        "mode": "all",
        "total": 0,
        "current": 0,
        "current_question": "",
        "start_time": None,
        "error": None,
        "stopped": False,
        "task": None,
        "experiment_id": None,
        "config": {}
    }
    
    msg = "基准测试状态已重置"
    if was_running:
        msg = f"测试已强制停止（之前进度: {previous_progress}/{previous_total}），状态已重置"
    
    return {
        "success": True,
        "message": msg,
        "was_running": was_running,
        "previous_progress": previous_progress if was_running else 0
    }


@router.get("/progress")
async def get_test_progress(
    session: AsyncSession = Depends(get_async_session)
):
    """获取当前测试进度及最近完成的题目"""
    global current_test_task
    
    elapsed = 0
    if current_test_task["start_time"]:
        elapsed = int((datetime.now() - current_test_task["start_time"]).total_seconds())
    
    # 确定状态
    status = "idle"  # 默认空闲状态
    if current_test_task["is_running"]:
        status = "running"
    elif current_test_task.get("stopped", False):
        status = "stopped"
    elif current_test_task.get("error"):
        status = "error"
    elif current_test_task["current"] > 0 and current_test_task["current"] >= current_test_task["total"]:
        status = "completed"
    elif current_test_task["current"] > 0:
        # 有进度但不在运行，可能是异常终止
        status = "interrupted"
    
    # 获取最近完成的10道题目
    recent_results = []
    if current_test_task["current"] > 0:
        result = await session.execute(
            select(BenchmarkResult)
            .order_by(BenchmarkResult.created_at.desc())
            .limit(10)
        )
        recent = result.scalars().all()
        
        for r in recent:
            dataset = await session.get(BenchmarkDataset, r.dataset_id)
            if dataset:
                recent_results.append({
                    "id": r.id,
                    "question": dataset.question,
                    "subject": dataset.subject,
                    "year": dataset.year,
                    "correct_answer": dataset.correct_answer,
                    "model_answer": r.model_answer,
                    "is_correct": r.is_correct,
                    "overall_score": r.overall_score,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                })
    
    return {
        "status": status,
        "current": current_test_task["current"],
        "total": current_test_task["total"],
        "current_question": current_test_task["current_question"],
        "elapsed_time": elapsed,
        "experiment_id": current_test_task.get("experiment_id"),
        "recent_results": recent_results
    }


@router.get("/results")
async def get_results(
    page: int = 1,
    page_size: int = 20,
    filter: str = "all",  # 参数名改为 filter，与前端的参数名一致
    subject: Optional[str] = None,
    experiment_config: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """获取测试结果列表"""
    # 构建查询
    query = select(BenchmarkResult).join(BenchmarkDataset)

    if filter == "correct":
        query = query.where(BenchmarkResult.is_correct == True)
    elif filter == "wrong":
        query = query.where(BenchmarkResult.is_correct == False)
    elif filter == "low_score":
        query = query.where(BenchmarkResult.overall_score < 3)

    if subject:
        query = query.where(BenchmarkDataset.subject == subject)

    if experiment_config:
        query = query.where(BenchmarkResult.experiment_config == experiment_config)

    # 统计总数
    count_query = select(func.count(BenchmarkResult.id))
    if filter == "correct":
        count_query = count_query.where(BenchmarkResult.is_correct == True)
    elif filter == "wrong":
        count_query = count_query.where(BenchmarkResult.is_correct == False)
    elif filter == "low_score":
        count_query = count_query.where(BenchmarkResult.overall_score < 3)
    if experiment_config:
        count_query = count_query.where(BenchmarkResult.experiment_config == experiment_config)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(BenchmarkResult.created_at.desc())
    
    result = await session.execute(query)
    results = result.scalars().all()
    
    # 格式化结果
    items = []
    
    for r in results:
        dataset = await session.get(BenchmarkDataset, r.dataset_id)
        question = dataset.question if dataset else ""
        
        # 检查是否已加入知识库（通过is_in_iteration_queue或查询knowledge表）
        is_in_knowledge_base = r.is_in_iteration_queue
        if not is_in_knowledge_base and question:
            # 双重检查knowledge表
            from app.models.database import Knowledge
            know_result = await session.execute(
                select(Knowledge).where(Knowledge.question == question).limit(1)
            )
            is_in_knowledge_base = know_result.scalar_one_or_none() is not None
        
        items.append({
            "id": r.id,
            "question": question,
            "subject": dataset.subject if dataset else "",
            "year": dataset.year if dataset else "",
            "score": dataset.score if dataset else 0,
            "model_answer": r.model_answer,
            "correct_answer": dataset.correct_answer if dataset else "",
            "analysis": dataset.analysis if dataset else "",
            "is_correct": r.is_correct,
            "overall_score": r.overall_score,
            "accuracy_score": r.accuracy_score,
            "completeness_score": r.completeness_score,
            "educational_score": r.educational_score,
            "suggestions": r.suggestions,
            "is_in_knowledge_base": is_in_knowledge_base
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/report")
async def get_benchmark_report(
    expert_id: Optional[int] = None,
    experiment_config: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """生成详细的评测报告 - 支持按实验配置过滤"""
    # 基础统计
    query = select(BenchmarkResult)
    if expert_id:
        query = query.where(BenchmarkResult.expert_id == expert_id)
    if experiment_config:
        query = query.where(BenchmarkResult.experiment_config == experiment_config)
    
    result = await session.execute(query)
    results = result.scalars().all()
    
    if not results:
        return {
            "summary": {"total_questions": 0, "correct_count": 0, "wrong_count": 0, "accuracy_rate": 0, "avg_score": 0},
            "all_results": [],
            "by_subject": {},
            "by_year": {},
            "wrong_questions": [],
            "low_score_questions": [],
            "message": "暂无测试数据"
        }
    
    # 按学科统计
    subject_stats = {}
    year_stats = {}
    score_distribution = {
        "0-1": 0, "1-2": 0, "2-3": 0, "3-4": 0, "4-5": 0
    }
    
    # 详细题目记录
    detailed_results = []
    
    # 时间范围
    timestamps = [r.created_at for r in results if r.created_at]
    start_time = min(timestamps) if timestamps else None
    end_time = max(timestamps) if timestamps else None
    
    for r in results:
        dataset = await session.get(BenchmarkDataset, r.dataset_id)
        if not dataset:
            continue
        
        # 学科统计
        subject = dataset.subject
        if subject not in subject_stats:
            subject_stats[subject] = {
                "total": 0, "correct": 0, "total_score": 0,
                "accuracy_scores": [], "completeness_scores": [], 
                "educational_scores": []
            }
        subject_stats[subject]["total"] += 1
        if r.is_correct:
            subject_stats[subject]["correct"] += 1
        subject_stats[subject]["total_score"] += r.overall_score
        subject_stats[subject]["accuracy_scores"].append(r.accuracy_score or 0)
        subject_stats[subject]["completeness_scores"].append(r.completeness_score or 0)
        subject_stats[subject]["educational_scores"].append(r.educational_score or 0)
        
        # 年份统计
        year = dataset.year
        if year:
            if year not in year_stats:
                year_stats[year] = {"total": 0, "correct": 0}
            year_stats[year]["total"] += 1
            if r.is_correct:
                year_stats[year]["correct"] += 1
        
        # 分数分布
        score = r.overall_score or 0
        if score < 1:
            score_distribution["0-1"] += 1
        elif score < 2:
            score_distribution["1-2"] += 1
        elif score < 3:
            score_distribution["2-3"] += 1
        elif score < 4:
            score_distribution["3-4"] += 1
        else:
            score_distribution["4-5"] += 1
        
        # 详细记录
        detailed_results.append({
            "id": r.id,
            "question": dataset.question[:100] + "..." if len(dataset.question) > 100 else dataset.question,
            "subject": dataset.subject,
            "year": dataset.year,
            "correct_answer": dataset.correct_answer,
            "model_answer": r.model_answer[:200] + "..." if r.model_answer and len(r.model_answer) > 200 else r.model_answer,
            "is_correct": r.is_correct,
            "overall_score": r.overall_score,
            "accuracy_score": r.accuracy_score,
            "completeness_score": r.completeness_score,
            "educational_score": r.educational_score,
            "suggestions": r.suggestions,
            "timestamp": r.created_at.isoformat() if r.created_at else None
        })
    
    # 计算正确率和平均分
    for subject in subject_stats:
        s = subject_stats[subject]
        s["accuracy"] = round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else 0
        s["avg_score"] = round(s["total_score"] / s["total"], 2) if s["total"] > 0 else 0
        # 计算各项平均分
        s["avg_accuracy"] = round(sum(s["accuracy_scores"]) / len(s["accuracy_scores"]), 2) if s["accuracy_scores"] else 0
        s["avg_completeness"] = round(sum(s["completeness_scores"]) / len(s["completeness_scores"]), 2) if s["completeness_scores"] else 0
        s["avg_educational"] = round(sum(s["educational_scores"]) / len(s["educational_scores"]), 2) if s["educational_scores"] else 0
        # 删除原始分数列表
        del s["accuracy_scores"]
        del s["completeness_scores"]
        del s["educational_scores"]
    
    for year in year_stats:
        y = year_stats[year]
        y["accuracy"] = round(y["correct"] / y["total"] * 100, 1) if y["total"] > 0 else 0
    
    # 总分统计
    total_correct = sum(1 for r in results if r.is_correct)
    total_score = sum(r.overall_score for r in results)
    
    # 错题列表
    wrong_questions = [r for r in detailed_results if not r["is_correct"]]
    low_score_questions = [r for r in detailed_results if r["overall_score"] < 3]
    
    return {
        "experiment_info": {
            "test_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "duration_seconds": (end_time - start_time).total_seconds() if start_time and end_time else 0,
            "expert_id": expert_id,
            "rag_enabled": settings.ENABLE_RAG,
            "experiment_mode": settings.EXPERIMENT_MODE
        },
        "summary": {
            "total_questions": len(results),
            "correct_count": total_correct,
            "wrong_count": len(results) - total_correct,
            "accuracy_rate": round(total_correct / len(results) * 100, 1),
            "avg_score": round(total_score / len(results), 2),
            "total_score": round(total_score, 2),
            "max_score": max(r.overall_score for r in results),
            "min_score": min(r.overall_score for r in results)
        },
        "by_subject": subject_stats,
        "by_year": year_stats,
        "score_distribution": score_distribution,
        "wrong_questions": wrong_questions[:20],  # 前20道错题
        "low_score_questions": low_score_questions[:20],  # 前20道低分题
        "all_results": detailed_results
    }


@router.get("/report/export")
async def export_benchmark_report(
    format: str = "json",
    expert_id: Optional[int] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """导出基准测试报告"""
    try:
        report = await get_benchmark_report(expert_id=expert_id, session=session)
        
        # 检查是否有数据
        if not report or "summary" not in report:
            if format == "json":
                return {"message": "暂无测试数据", "data": []}
            else:
                return {"csv_content": "暂无测试数据\n"}
        
        if format == "json":
            return report
        elif format == "csv":
            # 生成CSV格式
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow(["题目ID", "学科", "年份", "是否正确", "总分", "准确性", "完整性", "教育价值", "正确答案", "模型回答"])
            
            # 写入数据
            for r in report.get("all_results", []):
                writer.writerow([
                    r.get("id", ""), 
                    r.get("subject", ""), 
                    r.get("year", ""), 
                    "是" if r.get("is_correct") else "否",
                    r.get("overall_score", 0), 
                    r.get("accuracy_score", 0),
                    r.get("completeness_score", 0), 
                    r.get("educational_score", 0),
                    r.get("correct_answer", ""), 
                    r.get("model_answer", "")
                ])
            
            return {"csv_content": output.getvalue()}
        else:
            raise HTTPException(status_code=400, detail="不支持的格式")
    except Exception as e:
        import traceback
        print(f"导出报告失败: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/add-to-iteration")
async def add_to_iteration(
    request: AddToIterationRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """将错题加入知识库（直接入库）"""
    from app.services.iteration.data_generator import data_generator
    
    added_count = 0
    already_in_knowledge = 0
    failed_count = 0
    
    for result_id in request.result_ids:
        result = await session.get(BenchmarkResult, result_id)
        if not result:
            continue
        
        # 获取题目信息
        dataset = await session.get(BenchmarkDataset, result.dataset_id)
        if not dataset:
            continue
        
        # 检查是否已在知识库中（通过question去重）
        from sqlalchemy import select, func
        existing = await session.execute(
            select(Knowledge).where(
                Knowledge.question == dataset.question
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            already_in_knowledge += 1
            continue
        
        try:
            # 获取专家学科信息
            expert = await session.get(Expert, result.expert_id)
            expert_subject = expert.subject if expert else "通用"
            
            # 判断是否为选择题（有A/B/C/D选项）
            is_choice_question = bool(re.search(r'[A-D][\.\s][\s\S]*?[A-D][\.\s]', dataset.question)) or \
                                bool(re.search(r'\n[\s]*[A-D][\.\s]', dataset.question))
            
            quality_result = None  # 初始化为None
            
            if is_choice_question:
                # 选择题：生成解题模板范式
                corrected_answer = await generate_choice_template(
                    dataset.question, 
                    dataset.correct_answer,
                    result.model_answer,
                    expert_subject
                )
                knowledge_type = "template"
                quality_score = 4.5
            else:
                # 非选择题：调用云端质检获取纠正后的答案
                from app.services.iteration.quality_checker import QualityChecker
                checker = QualityChecker()
                
                quality_result = await checker.check_answer(
                    question=dataset.question,
                    local_answer=result.model_answer,
                    expert_subject=expert_subject
                )
                
                if quality_result and quality_result.get("corrected_answer"):
                    corrected_answer = quality_result["corrected_answer"]
                    knowledge_type = quality_result.get("knowledge_type", "qa")
                    quality_score = quality_result.get("overall_score", result.overall_score or 3.0)
                else:
                    # 云端质检失败
                    corrected_answer = f"【参考答案】\n{dataset.correct_answer}\n\n【原答案】\n{result.model_answer}"
                    knowledge_type = "qa"
                    quality_score = result.overall_score or 3.0
            
            # 生成embedding（基于问题和答案）
            from app.utils.embedding import embedding_service
            content = f"问题：{dataset.question}\n答案：{corrected_answer}"
            embedding = embedding_service.encode(content)
            
            # 创建知识记录
            knowledge = Knowledge(
                expert_id=result.expert_id,
                question=dataset.question,
                answer=corrected_answer,
                embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                meta_data={
                    "original_answer": result.model_answer,
                    "correct_answer": dataset.correct_answer,
                    "source": "benchmark_wrong_answer",
                    "benchmark_result_id": result.id,
                    "quality_score": quality_score,
                    "knowledge_type": knowledge_type,
                    "cloud_corrected": quality_result is not None
                },
                knowledge_type=knowledge_type,
                source_type="wrong_answer_extracted",
                quality_score=quality_score
            )
            session.add(knowledge)
            
            # 更新专家知识计数
            expert = await session.get(Expert, result.expert_id)
            if expert:
                expert.knowledge_count += 1
            
            # 标记为已处理
            result.is_in_iteration_queue = True
            result.is_processed = True
            added_count += 1
            
        except Exception as e:
            print(f"[AddToKnowledge] 处理失败 (ID={result_id}): {e}")
            failed_count += 1
            continue
    
    await session.commit()
    
    msg = f"成功将 {added_count} 道错题加入知识库"
    if already_in_knowledge > 0:
        msg += f"（{already_in_knowledge} 道已存在）"
    if failed_count > 0:
        msg += f"，{failed_count} 道处理失败"
    
    return {
        "success": True,
        "added_count": added_count,
        "already_in_queue": already_in_knowledge,
        "failed_count": failed_count,
        "message": msg
    }


@router.get("/iteration-queue")
async def get_iteration_queue(
    expert_id: Optional[int] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """获取迭代队列中的错题（待处理）"""
    from sqlalchemy import select, and_
    
    query = select(BenchmarkResult, BenchmarkDataset).join(
        BenchmarkDataset, 
        BenchmarkResult.dataset_id == BenchmarkDataset.id
    ).where(
        and_(
            BenchmarkResult.is_in_iteration_queue == True,
            BenchmarkResult.is_processed == False
        )
    )
    
    if expert_id:
        query = query.where(BenchmarkResult.expert_id == expert_id)
    
    result = await session.execute(query)
    rows = result.all()
    
    items = []
    for benchmark_result, dataset in rows:
        items.append({
            "result_id": benchmark_result.id,
            "expert_id": benchmark_result.expert_id,
            "question": dataset.question,
            "correct_answer": dataset.correct_answer,
            "analysis": dataset.analysis,
            "subject": dataset.subject,
            "model_answer": benchmark_result.model_answer,
            "overall_score": benchmark_result.overall_score,
            "created_at": benchmark_result.created_at.isoformat() if benchmark_result.created_at else None
        })
    
    return {
        "items": items,
        "total": len(items)
    }


@router.post("/process-iteration-queue")
async def process_iteration_queue(
    expert_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """处理迭代队列中的错题（生成知识点和SFT数据）"""
    from sqlalchemy import select, and_
    
    # 查询该专家待处理的错题
    query = select(BenchmarkResult, BenchmarkDataset).join(
        BenchmarkDataset,
        BenchmarkResult.dataset_id == BenchmarkDataset.id
    ).where(
        and_(
            BenchmarkResult.expert_id == expert_id,
            BenchmarkResult.is_in_iteration_queue == True,
            BenchmarkResult.is_processed == False
        )
    )
    
    result = await session.execute(query)
    rows = result.all()
    
    if not rows:
        return {
            "success": False,
            "message": "该专家没有待处理的错题"
        }
    
    # 逐个处理生成知识点
    processed_count = 0
    knowledge_count = 0
    
    for benchmark_result, dataset in rows:
        try:
            # 调用知识生成器
            result_data = await knowledge_generator.process_wrong_answer(
                session=session,
                expert_id=expert_id,
                question=dataset.question,
                model_answer=benchmark_result.model_answer or "",
                correct_answer=dataset.correct_answer,
                analysis=dataset.analysis or "暂无解析",
                subject=dataset.subject
            )
            
            # 标记为已处理
            benchmark_result.is_processed = True
            
            if result_data["knowledge_ids"]:
                knowledge_count += len(result_data["knowledge_ids"])
            
            processed_count += 1
            
        except Exception as e:
            print(f"[Benchmark] 处理错题 {benchmark_result.id} 失败: {e}")
            continue
    
    await session.commit()
    
    return {
        "success": True,
        "processed_count": processed_count,
        "knowledge_count": knowledge_count,
        "message": f"成功处理 {processed_count} 道错题，生成 {knowledge_count} 条知识点"
    }


@router.post("/delete-results")
async def delete_results(
    request: AddToIterationRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """删除选中的测试结果"""
    deleted_count = 0
    
    for result_id in request.result_ids:
        result = await session.get(BenchmarkResult, result_id)
        if result:
            await session.delete(result)
            deleted_count += 1
    
    await session.commit()
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"成功删除 {deleted_count} 条测试结果"
    }


@router.get("/sft-data")
async def get_sft_data(
    expert_id: Optional[int] = None,
    is_used: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_async_session)
):
    """获取SFT微调数据（待训练队列）"""
    from app.models.database import SFTData
    
    # 构建查询
    query = select(SFTData).order_by(SFTData.created_at.desc())
    
    if expert_id:
        query = query.where(SFTData.expert_id == expert_id)
    if is_used is not None:
        query = query.where(SFTData.is_used_in_training == is_used)
    
    # 统计总数
    count_query = select(func.count(SFTData.id))
    if expert_id:
        count_query = count_query.where(SFTData.expert_id == expert_id)
    if is_used is not None:
        count_query = count_query.where(SFTData.is_used_in_training == is_used)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    items = result.scalars().all()
    
    # 构建响应
    data = []
    for item in items:
        expert = await session.get(Expert, item.expert_id)
        data.append({
            "id": item.id,
            "expert_id": item.expert_id,
            "expert_name": expert.name if expert else "未知",
            "expert_subject": expert.subject if expert else "",
            "instruction": item.instruction[:200] + "..." if len(item.instruction) > 200 else item.instruction,
            "output_preview": item.output[:200] + "..." if len(item.output) > 200 else item.output,
            "quality_score": item.quality_score,
            "is_used_in_training": item.is_used_in_training,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })
    
    return {
        "items": data,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/sft-data/stats")
async def get_sft_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """获取SFT数据统计"""
    from app.models.database import SFTData
    
    # 统计各专家的待训练数据
    stats = []
    result = await session.execute(select(Expert))
    experts = result.scalars().all()
    
    for expert in experts:
        # 未使用的数据
        unused_result = await session.execute(
            select(func.count(SFTData.id)).where(
                SFTData.expert_id == expert.id,
                SFTData.is_used_in_training == False
            )
        )
        unused_count = unused_result.scalar()
        
        # 已使用的数据
        used_result = await session.execute(
            select(func.count(SFTData.id)).where(
                SFTData.expert_id == expert.id,
                SFTData.is_used_in_training == True
            )
        )
        used_count = used_result.scalar()
        
        if unused_count > 0 or used_count > 0:
            stats.append({
                "expert_id": expert.id,
                "expert_name": expert.name,
                "expert_subject": expert.subject,
                "unused_count": unused_count,
                "used_count": used_count
            })
    
    # 总计
    total_unused_result = await session.execute(
        select(func.count(SFTData.id)).where(SFTData.is_used_in_training == False)
    )
    total_unused = total_unused_result.scalar()
    
    total_used_result = await session.execute(
        select(func.count(SFTData.id)).where(SFTData.is_used_in_training == True)
    )
    total_used = total_used_result.scalar()
    
    return {
        "by_expert": stats,
        "total_unused": total_unused,
        "total_used": total_used
    }



# ============= 辅助函数 =============

async def _import_from_local(session: AsyncSession, base_path: str, specific_subject: Optional[str] = None) -> int:
    """从本地目录导入 GAOKAO-Bench 数据集"""
    imported_count = 0
    data_path = os.path.join(base_path, "Data", "Objective_Questions")
    
    if not os.path.exists(data_path):
        raise Exception(f"数据目录不存在: {data_path}")
    
    for filename in os.listdir(data_path):
        if not filename.endswith('.json'):
            continue
        
        # 解析学科
        subject_en = filename.replace('2010-2022_', '').replace('_MCQs.json', '').replace('_Fill_in_Blanks.json', '').replace('_Reading_Comp.json', '').replace('_Cloze_Test.json', '').replace('_Lang_and_Usage_MCQs.json', '').replace('_Modern_Lit.json', '')
        # 处理 Math_I 和 Math_II 映射到数学
        if subject_en.startswith('Math'):
            subject_en = 'Math'
        subject_cn = SUBJECT_MAPPING.get(subject_en, subject_en)
        
        # 如果指定了学科，只导入该学科
        if specific_subject and subject_cn != specific_subject:
            continue
        
        filepath = os.path.join(data_path, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for item in data.get('example', []):
                # 获取题目内容，确保不为 None
                question = item.get("question") or ""
                if not question.strip():
                    continue
                
                # 检查是否已存在
                existing = await session.execute(
                    select(BenchmarkDataset).where(
                        BenchmarkDataset.question == question
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                # 处理答案格式（去重，避免 "B, C, C" 这种重复）
                answer = item.get("answer", [])
                if isinstance(answer, list):
                    # 去重同时保持顺序
                    seen = set()
                    unique_answers = []
                    for a in answer:
                        if a and a not in seen:
                            seen.add(a)
                            unique_answers.append(a)
                    answer = ", ".join(unique_answers)
                elif answer is None:
                    answer = ""
                else:
                    answer = str(answer)
                
                dataset = BenchmarkDataset(
                    question=question,
                    correct_answer=answer,
                    subject=subject_cn,
                    year=item.get("year") or "",
                    category=item.get("category") or "",
                    score=item.get("score") or 0,
                    analysis=item.get("analysis") or "",
                    question_type="objective",
                    source_url=f"file://{filepath}"
                )
                session.add(dataset)
                imported_count += 1
            
            await session.commit()
            
        except Exception as e:
            print(f"导入文件失败 {filename}: {e}")
            continue
    
    return imported_count


async def _import_from_github(session: AsyncSession, url: str) -> int:
    """从GitHub URL导入单个文件"""
    imported_count = 0
    
    # 转换GitHub URL为raw格式
    raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(raw_url, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    
    # 解析学科
    keywords = data.get('keywords', '')
    subject_en = keywords.replace('2010-2022_', '').replace('_MCQs', '')
    # 处理 Math_I 和 Math_II 映射到数学
    if subject_en.startswith('Math'):
        subject_en = 'Math'
    subject_cn = SUBJECT_MAPPING.get(subject_en, subject_en)
    
    for item in data.get('example', []):
        # 检查是否已存在
        existing = await session.execute(
            select(BenchmarkDataset).where(
                BenchmarkDataset.question == item.get("question", "")
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            continue
        
        answer = item.get("answer", [])
        if isinstance(answer, list):
            # 去重同时保持顺序
            seen = set()
            unique_answers = []
            for a in answer:
                if a not in seen:
                    seen.add(a)
                    unique_answers.append(a)
            answer = ", ".join(unique_answers)
        
        dataset = BenchmarkDataset(
            question=item.get("question", ""),
            correct_answer=answer,
            subject=subject_cn,
            year=item.get("year"),
            category=item.get("category"),
            score=item.get("score"),
            analysis=item.get("analysis"),
            question_type="objective",
            source_url=url
        )
        session.add(dataset)
        imported_count += 1
    
    await session.commit()
    return imported_count


# ============= 报告辅助函数 =============

async def _generate_detailed_report(session: AsyncSession, expert_id: Optional[int] = None, experiment_config: Optional[str] = None, experiment_id: Optional[str] = None) -> Dict:
    """生成详细测试报告（内部函数）

    Args:
        expert_id: 专家ID过滤
        experiment_config: 实验配置标识，如 "routing=True,rag=False"
        experiment_id: 实验ID（优先使用，用于区分同配置的多轮实验）
    """
    # 基础统计
    query = select(BenchmarkResult)
    if expert_id:
        query = query.where(BenchmarkResult.expert_id == expert_id)
    
    # 🔥 关键修复：优先使用 experiment_id 过滤，区分同配置的多轮实验
    if experiment_id:
        query = query.where(BenchmarkResult.experiment_id == experiment_id)
    elif experiment_config:
        query = query.where(BenchmarkResult.experiment_config == experiment_config)

    result = await session.execute(query)
    results = result.scalars().all()
    
    if not results:
        return {"message": "暂无测试数据"}
    
    # 按学科统计
    subject_stats = {}
    year_stats = {}
    score_distribution = {"0-1": 0, "1-2": 0, "2-3": 0, "3-4": 0, "4-5": 0}
    detailed_results = []
    timestamps = [r.created_at for r in results if r.created_at]
    start_time = min(timestamps) if timestamps else None
    end_time = max(timestamps) if timestamps else None
    
    for r in results:
        dataset = await session.get(BenchmarkDataset, r.dataset_id)
        if not dataset:
            continue
        
        # 学科统计
        subject = dataset.subject
        if subject not in subject_stats:
            subject_stats[subject] = {
                "total": 0, "correct": 0, "total_score": 0,
                "accuracy_scores": [], "completeness_scores": [], 
                "educational_scores": []
            }
        subject_stats[subject]["total"] += 1
        if r.is_correct:
            subject_stats[subject]["correct"] += 1
        subject_stats[subject]["total_score"] += r.overall_score
        subject_stats[subject]["accuracy_scores"].append(r.accuracy_score or 0)
        subject_stats[subject]["completeness_scores"].append(r.completeness_score or 0)
        subject_stats[subject]["educational_scores"].append(r.educational_score or 0)
        
        # 年份统计
        year = dataset.year
        if year:
            if year not in year_stats:
                year_stats[year] = {"total": 0, "correct": 0}
            year_stats[year]["total"] += 1
            if r.is_correct:
                year_stats[year]["correct"] += 1
        
        # 分数分布
        score = r.overall_score or 0
        if score < 1:
            score_distribution["0-1"] += 1
        elif score < 2:
            score_distribution["1-2"] += 1
        elif score < 3:
            score_distribution["2-3"] += 1
        elif score < 4:
            score_distribution["3-4"] += 1
        else:
            score_distribution["4-5"] += 1
        
        # 详细记录
        detailed_results.append({
            "id": r.id,
            "question": dataset.question[:100] + "..." if len(dataset.question) > 100 else dataset.question,
            "subject": dataset.subject,
            "year": dataset.year,
            "correct_answer": dataset.correct_answer,
            "model_answer": r.model_answer[:200] + "..." if r.model_answer and len(r.model_answer) > 200 else r.model_answer,
            "is_correct": r.is_correct,
            "overall_score": r.overall_score,
            "accuracy_score": r.accuracy_score,
            "completeness_score": r.completeness_score,
            "educational_score": r.educational_score,
            "suggestions": r.suggestions,
            "timestamp": r.created_at.isoformat() if r.created_at else None
        })
    
    # 计算正确率和平均分
    for subject in subject_stats:
        s = subject_stats[subject]
        s["accuracy"] = round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else 0
        s["avg_score"] = round(s["total_score"] / s["total"], 2) if s["total"] > 0 else 0
        s["avg_accuracy"] = round(sum(s["accuracy_scores"]) / len(s["accuracy_scores"]), 2) if s["accuracy_scores"] else 0
        s["avg_completeness"] = round(sum(s["completeness_scores"]) / len(s["completeness_scores"]), 2) if s["completeness_scores"] else 0
        s["avg_educational"] = round(sum(s["educational_scores"]) / len(s["educational_scores"]), 2) if s["educational_scores"] else 0
        del s["accuracy_scores"]
        del s["completeness_scores"]
        del s["educational_scores"]
    
    for year in year_stats:
        y = year_stats[year]
        y["accuracy"] = round(y["correct"] / y["total"] * 100, 1) if y["total"] > 0 else 0
    
    # 总分统计
    total_correct = sum(1 for r in results if r.is_correct)
    total_score = sum(r.overall_score for r in results)
    
    # 错题列表
    wrong_questions = [r for r in detailed_results if not r["is_correct"]]
    low_score_questions = [r for r in detailed_results if r["overall_score"] < 3]
    
    return {
        "experiment_info": {
            "test_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "duration_seconds": (end_time - start_time).total_seconds() if start_time and end_time else 0,
            "expert_id": expert_id,
            "rag_enabled": settings.ENABLE_RAG,
            "experiment_mode": settings.EXPERIMENT_MODE
        },
        "summary": {
            "total_questions": len(results),
            "correct_count": total_correct,
            "wrong_count": len(results) - total_correct,
            "accuracy_rate": round(total_correct / len(results) * 100, 1),
            "avg_score": round(total_score / len(results), 2),
            "total_score": round(total_score, 2),
            "max_score": max(r.overall_score for r in results),
            "min_score": min(r.overall_score for r in results)
        },
        "by_subject": subject_stats,
        "by_year": year_stats,
        "score_distribution": score_distribution,
        "wrong_questions": wrong_questions[:20],
        "low_score_questions": low_score_questions[:20],
        "all_results": detailed_results
    }


# ============= 报告管理 API =============

@router.get("/reports/list")
async def list_saved_reports():
    """列出所有保存的报告"""
    return {
        "success": True,
        "reports": report_saver.list_reports()
    }


@router.get("/reports/load/{filename}")
async def load_saved_report(filename: str):
    """加载指定报告"""
    report = report_saver.load_report(filename)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {
        "success": True,
        "report": report
    }


@router.delete("/reports/delete/{filename}")
async def delete_saved_report(filename: str):
    """删除指定报告"""
    success = report_saver.delete_report(filename)
    if not success:
        raise HTTPException(status_code=400, detail="删除失败")
    return {
        "success": True,
        "message": "报告已删除"
    }


@router.post("/reports/compare")
async def compare_reports(request: Dict):
    """对比多个报告"""
    filenames = request.get("filenames", [])
    if len(filenames) < 2:
        raise HTTPException(status_code=400, detail="至少需要选择2个报告进行对比")
    
    output_path = report_saver.export_comparison(filenames)
    return {
        "success": True,
        "comparison_file": output_path,
        "message": "对比报告已生成"
    }


# ============= 后台任务 =============

async def run_benchmark_test(
    questions: List[BenchmarkDataset], 
    expert_id: Optional[int] = None,
    experiment_id: Optional[str] = None,
    use_rag: bool = True,
    use_expert_routing: bool = True,
    enable_iteration: bool = False  # 默认禁用，必须显式启用
):
    """后台运行基准测试（简化参数版）"""
    global current_test_task
    
    print(f"\n[🚀 后台任务启动] 共 {len(questions)} 道题目")
    print(f"[配置确认] 路由={use_expert_routing}, RAG={use_rag}, 迭代={enable_iteration}")
    
    # 🔥 生成实验配置标识 - 区分不同实验模式
    experiment_config = f"routing={use_expert_routing},rag={use_rag}"
    print(f"[实验配置标识] {experiment_config}")
    
    print("[DEBUG] About to create AsyncSessionLocal...")
    async with AsyncSessionLocal() as session:
        print(f"[DEBUG] Session created, entering try block...")
        try:
            # 如果指定了专家，使用指定专家；否则根据配置决定是否自动路由
            expert = None
            if expert_id:
                expert = await session.get(Expert, expert_id)
                print(f"[Benchmark] 使用指定专家: {expert.name if expert else 'None'}")
            elif use_expert_routing:
                print("[Benchmark] 使用自动路由（专家路由启用）")
            else:
                print("[Benchmark] 使用通用专家（专家路由禁用）")
            
            if not questions:
                print("[Benchmark] 警告: 题目列表为空!")
                current_test_task["is_running"] = False
                return
            
            for i, question in enumerate(questions):
                # 检查是否被停止（取消标志）
                if current_test_task.get("stopped", False):
                    print(f"[Benchmark] 测试被手动停止，已完成 {i} 道题目")
                    break
                
                # 检查任务是否被取消（使用try-except防止异常）
                try:
                    current = asyncio.current_task()
                    if current and current.cancelled():
                        print(f"[Benchmark] 任务被取消，已完成 {i} 道题目")
                        break
                except Exception:
                    pass  # 如果获取失败，继续执行
                
                # 更新进度
                current_test_task["current"] = i + 1
                current_test_task["current_question"] = question.question[:50] + "..."
                
                # 确定使用的专家
                current_expert = expert
                if not current_expert:
                    if use_expert_routing:
                        # 自动路由: 根据题目学科查找或创建专家
                        current_expert = await expert_pool.get_or_create_expert(
                            session, 
                            subject=question.subject
                        )
                    else:
                        # 禁用专家路由: 使用通用专家
                        current_expert = await expert_pool.get_or_create_expert(
                            session, 
                            subject="通用"
                        )
                
                # 检查是否已测试过（🔥 用 experiment_id 区分，同配置多轮不会互相跳过）
                dedup_query = select(BenchmarkResult).where(
                    BenchmarkResult.dataset_id == question.id,
                    BenchmarkResult.expert_id == current_expert.id,
                )
                if experiment_id:
                    dedup_query = dedup_query.where(BenchmarkResult.experiment_id == experiment_id)
                else:
                    dedup_query = dedup_query.where(BenchmarkResult.experiment_config == experiment_config)
                existing = await session.execute(dedup_query.limit(1))
                if existing.scalar_one_or_none():
                    print(f"[题目 {i+1}] 已测试过（实验: {experiment_id or experiment_config}），跳过")
                    continue
                
                # 调用模型回答（检查停止标志）
                model_answer = ""
                if current_test_task.get("stopped", False):
                    print(f"[Benchmark] 在LLM调用前检测到停止请求")
                    break
                
                # 使用超时包装LLM调用，使取消能更快响应
                try:
                    # 构建当前实验模式描述
                    mode_desc = []
                    if use_expert_routing:
                        mode_desc.append(f"专家={current_expert.subject}")
                    else:
                        # Baseline模式：不使用任何专家prompt
                        mode_desc.append("无专家/Baseline")
                    if use_rag:
                        mode_desc.append("RAG✓")
                    else:
                        mode_desc.append("RAG✗")
                    
                    print(f"\n[题目 {i+1}/{len(questions)}] [{'/'.join(mode_desc)}]")
                    print(f"[问题] {question.question[:60]}...")
                    
                    model_response = await asyncio.wait_for(
                        llm_service.generate(
                            session=session,
                            query=question.question,
                            expert=current_expert,
                            use_rag=use_rag,  # 实验变量：是否使用RAG
                            use_expert_routing=use_expert_routing  # 实验变量：是否使用专家路由（Baseline禁用）
                        ),
                        timeout=120.0  # 120秒超时（LLM生成可能需要较长时间）
                    )
                    model_answer = model_response["answer"]
                    print(f"[回答] {model_answer[:80]}...")
                except asyncio.TimeoutError:
                    model_answer = "[回答生成超时]"
                    print(f"[Benchmark] 问题 {i+1} LLM调用超时")
                except asyncio.CancelledError:
                    print(f"[Benchmark] LLM调用被取消")
                    raise
                except Exception as e:
                    model_answer = f"[回答生成失败] {str(e)}"
                
                # 检查停止标志
                if current_test_task.get("stopped", False):
                    print(f"[Benchmark] 在质量检查前检测到停止请求")
                    break
                
                # 质量检查（也加超时）
                quality_result = None
                try:
                    quality_result = await asyncio.wait_for(
                        quality_checker.check_answer(
                            question=question.question,
                            local_answer=model_answer,
                            expert_subject=current_expert.subject
                        ),
                        timeout=40.0  # 40秒超时
                    )
                except asyncio.TimeoutError:
                    print(f"[Benchmark] 问题 {i+1} 质量检查超时")
                except asyncio.CancelledError:
                    print(f"[Benchmark] 质量检查被取消")
                    raise
                except Exception as e:
                    print(f"质量检查失败: {e}")
                
                # 判断对错 (基于质量评分或简单对比)
                is_correct = False
                if quality_result:
                    is_correct = quality_result["overall_score"] >= 4.0
                else:
                    # 简单字符串匹配作为备选 - 提取答案字母
                    import re
                    model_answers = re.findall(r'[A-D]', model_answer.upper())
                    correct_answers = re.findall(r'[A-D]', question.correct_answer.upper())
                    is_correct = len(set(model_answers) & set(correct_answers)) > 0
                
                # 保存结果（处理 None 值和缺失字段）
                result = BenchmarkResult(
                    dataset_id=question.id,
                    expert_id=current_expert.id,
                    model_answer=model_answer,
                    is_correct=is_correct,
                    accuracy_score=(quality_result.get("accuracy_score") or 0) if quality_result else 0,
                    completeness_score=(quality_result.get("completeness_score") or 0) if quality_result else 0,
                    educational_score=(quality_result.get("educational_score") or 0) if quality_result else 0,
                    overall_score=(quality_result.get("overall_score") or 0) if quality_result else 0,
                    suggestions=quality_result.get("improvement_suggestions", "") if quality_result else "",
                    experiment_config=experiment_config,  # 🔥 保存实验配置标识
                    experiment_id=experiment_id  # 🔥 保存实验ID，用于区分同配置的多轮实验
                )
                session.add(result)
                await session.commit()
                
                # 延迟5秒避免API限流（Kimi API RPM限制：3次/分钟）
                await asyncio.sleep(5)
            
            # 🔥 修复：先生成报告并立即通知实验完成
            # 打印实验完成总结
            print("\n" + "="*60)
            print("[🎉 实验完成] 结果汇总")
            print("="*60)
            print(f"[配置] 路由={use_expert_routing}, RAG={use_rag}, 迭代={enable_iteration}")
            
            # 测试完成，自动生成并保存报告
            try:
                print("[Benchmark] 正在生成详细报告...")
                report = await _generate_detailed_report(session, expert_id, experiment_config, experiment_id)
                saved_path = report_saver.save_report(report)
                
                # 提取关键指标
                summary = report.get("summary", {})
                accuracy = summary.get("accuracy_rate", 0)
                avg_score = summary.get("avg_score", 0)
                
                print(f"[结果] 准确率: {accuracy}%, 平均得分: {avg_score}")
                print(f"[报告] 已保存: {saved_path}")
                print("="*60 + "\n")
            except Exception as report_e:
                print(f"[Benchmark] 保存报告失败: {report_e}")
            
            # 🔥 关键修复：先设置完成状态，确保前端能立即看到
            current_test_task["is_running"] = False
            current_test_task["current_question"] = f"实验完成: {experiment_id or 'N/A'}"
            
            # 🔥 关键修复：先提交会话，确保数据持久化
            await session.commit()
            
            # 如果有实验ID，立即通知实验系统完成（不等待入库）
            if experiment_id:
                try:
                    print(f"[Benchmark] 通知实验系统完成: {experiment_id}")
                    report = await _generate_detailed_report(session, expert_id, experiment_config, experiment_id)
                    
                    # 调用实验系统的完成接口
                    from app.api.experiments import complete_experiment
                    await complete_experiment(experiment_id, report)
                    print(f"[Benchmark] 实验 {experiment_id} 已完成通知")
                except Exception as exp_e:
                    print(f"[Benchmark] 通知实验系统失败: {exp_e}")
            
            # 🔥 关键修复：自动入库改为后台异步执行，不阻塞实验流程
            if enable_iteration:
                async def background_auto_add():
                    # 🔥 使用独立的数据库会话，避免并发冲突
                    async with AsyncSessionLocal() as bg_session:
                        try:
                            print("[Benchmark] 开始后台自动处理错题入知识库...")
                            auto_added = await auto_add_wrong_answers_to_knowledge(bg_session, expert_id)
                            print(f"[Benchmark] 后台自动入库完成: {auto_added} 条")
                        except Exception as auto_e:
                            print(f"[Benchmark] 后台自动入库失败: {auto_e}")
                
                # 启动后台入库任务，不等待完成
                asyncio.create_task(background_auto_add())
            else:
                print("[Benchmark] 迭代/自动入库已禁用（消融实验模式），跳过知识库更新")
            
        except asyncio.CancelledError:
            # 任务被取消（用户点击停止）
            print(f"[Benchmark] 测试任务被取消，已完成 {current_test_task['current']} 道题目")
            current_test_task["is_running"] = False
            
            # 即使被停止也尝试保存已完成部分的报告
            try:
                print("[Benchmark] 正在保存已完成的报告...")
                # 安全获取 experiment_config 和 experiment_id
                local_exp_config = locals().get('experiment_config', 'unknown')
                local_exp_id = locals().get('experiment_id', None)
                report = await _generate_detailed_report(session, expert_id, local_exp_config, local_exp_id)
                report["experiment_info"]["stopped"] = True
                saved_path = report_saver.save_report(report)
                print(f"[Benchmark] 报告已保存: {saved_path}")
            except Exception as report_e:
                print(f"[Benchmark] 保存报告失败: {report_e}")
            
        except Exception as e:
            import traceback
            current_test_task["is_running"] = False
            current_test_task["error"] = str(e)
            print(f"基准测试出错: {e}")
            print(f"[DEBUG] Error type: {type(e)}")
            print(f"[DEBUG] Locals: {list(locals().keys())}")
            traceback.print_exc()
            
            # 即使出错也尝试保存已完成的报告
            try:
                # 安全获取 experiment_config 和 experiment_id
                local_exp_config = locals().get('experiment_config', 'unknown')
                local_exp_id = locals().get('experiment_id', None)
                report = await _generate_detailed_report(session, expert_id, local_exp_config, local_exp_id)
                report["experiment_info"]["error"] = str(e)
                saved_path = report_saver.save_report(report)
            except Exception as report_e:
                print(f"[Benchmark] 保存错误报告失败: {report_e}")


# ============= 自动入库功能 =============

async def auto_add_wrong_answers_to_knowledge(
    session: AsyncSession,
    expert_id: Optional[int] = None,
    low_score_threshold: float = 4.0  # 正确但分数低于此值（<4.0）也入知识库优化
) -> int:
    """
    评测完成后自动将错题和低分正确题加入知识库
    
    根据论文质量评估体系：
    - 总分 >= 4.0：高质量，直接入库
    - 总分 < 4.0：需要优化，云端修正后入库
    
    Args:
        session: 数据库会话
        expert_id: 专家ID（可选）
        low_score_threshold: 低分阈值（默认4.0），低于此值的题云端修正后入库
    
    Returns:
        成功入库的数量
    """
    from sqlalchemy import select, and_, or_
    
    # 查询需要入库的题：
    # 1. 错题 (is_correct = False)
    # 2. 正确但分数低的 (is_correct = True AND overall_score < threshold)
    query = select(BenchmarkResult, BenchmarkDataset).join(
        BenchmarkDataset,
        BenchmarkResult.dataset_id == BenchmarkDataset.id
    ).where(
        or_(
            BenchmarkResult.is_correct == False,
            and_(
                BenchmarkResult.is_correct == True,
                BenchmarkResult.overall_score < low_score_threshold
            )
        )
    ).where(
        BenchmarkResult.is_in_iteration_queue == False  # 未入库的
    )
    
    if expert_id:
        query = query.where(BenchmarkResult.expert_id == expert_id)
    
    result = await session.execute(query)
    rows = result.fetchall()
    
    if not rows:
        print(f"[AutoAdd] 没有需要入库的题目")
        return 0
    
    print(f"[AutoAdd] 找到 {len(rows)} 道需要入库的题目（错题或低分正确题）")
    
    added_count = 0
    for benchmark_result, dataset in rows:
        # 检查是否已存在
        existing = await session.execute(
            select(Knowledge).where(Knowledge.question == dataset.question).limit(1)
        )
        if existing.scalar_one_or_none():
            print(f"[AutoAdd] 跳过已存在: {dataset.question[:40]}...")
            benchmark_result.is_in_iteration_queue = True  # 标记为已处理
            continue
        
        try:
            # 获取专家学科
            expert = await session.get(Expert, benchmark_result.expert_id)
            expert_subject = expert.subject if expert else "通用"
            
            # 判断是否为选择题
            is_choice_question = bool(re.search(r'[A-D][\.\s][\s\S]*?[A-D][\.\s]', dataset.question)) or \
                                bool(re.search(r'\n[\s]*[A-D][\.\s]', dataset.question))
            
            if is_choice_question:
                # 选择题：生成解题模板
                corrected_answer = await generate_choice_template(
                    dataset.question,
                    dataset.correct_answer,
                    benchmark_result.model_answer,
                    expert_subject
                )
                knowledge_type = "template"
                quality_score = max(benchmark_result.overall_score, 4.0)  # 自动生成的给高分
            else:
                # 非选择题：调用云端质检
                from app.services.iteration.quality_checker import QualityChecker
                checker = QualityChecker()
                
                quality_result = await checker.check_answer(
                    question=dataset.question,
                    local_answer=benchmark_result.model_answer,
                    expert_subject=expert_subject
                )
                
                if quality_result and quality_result.get("corrected_answer"):
                    corrected_answer = quality_result["corrected_answer"]
                    knowledge_type = quality_result.get("knowledge_type", "qa")
                    quality_score = quality_result.get("overall_score", benchmark_result.overall_score or 3.0)
                else:
                    # 云端失败，用基础格式
                    corrected_answer = f"【参考答案】\n{dataset.correct_answer}\n\n【解答】\n{benchmark_result.model_answer}"
                    knowledge_type = "qa"
                    quality_score = benchmark_result.overall_score or 3.0
            
            # 生成embedding并入库
            from app.utils.embedding import embedding_service
            content = f"问题：{dataset.question}\n答案：{corrected_answer}"
            embedding = embedding_service.encode(content)
            
            knowledge = Knowledge(
                expert_id=benchmark_result.expert_id,
                question=dataset.question,
                answer=corrected_answer,
                embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                meta_data={
                    "original_answer": benchmark_result.model_answer,
                    "correct_answer": dataset.correct_answer,
                    "source": "benchmark_auto_added",
                    "benchmark_result_id": benchmark_result.id,
                    "quality_score": quality_score,
                    "knowledge_type": knowledge_type,
                    "auto_added": True,
                    "is_wrong": not benchmark_result.is_correct,
                    "original_score": benchmark_result.overall_score
                },
                knowledge_type=knowledge_type,
                source_type="wrong_answer_extracted",
                quality_score=quality_score
            )
            session.add(knowledge)
            
            # 更新结果状态
            benchmark_result.is_in_iteration_queue = True
            benchmark_result.is_processed = True
            added_count += 1
            
            print(f"[AutoAdd] 已入库: {dataset.question[:40]}... (类型:{knowledge_type}, 分数:{quality_score})")
            
            # API限流保护
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"[AutoAdd] 入库失败 (ID={benchmark_result.id}): {e}")
            continue
    
    await session.commit()
    print(f"[AutoAdd] 完成: 成功入库 {added_count}/{len(rows)} 条")
    return added_count
