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
from sqlalchemy import select, func, update
from typing import List, Optional, Dict
from pydantic import BaseModel
import httpx
import json
import asyncio
import os
from datetime import datetime

from app.core.database import get_session as get_async_session, AsyncSessionLocal
from app.core.config import settings
from app.services.experts.llm_service import llm_service
from app.services.experts.expert_pool import expert_pool
from app.services.iteration.quality_checker import quality_checker
from app.services.iteration.data_generator import data_generator
from app.services.iteration.knowledge_generator import knowledge_generator
from app.services.benchmark.report_saver import report_saver
from app.models.database import BenchmarkDataset, BenchmarkResult, Expert

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


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
    "task": None  # 保存后台任务引用，用于强制取消
}

# GAOKAO-Bench 数据集本地路径
GAOKAO_BENCH_PATH = os.environ.get("GAOKAO_BENCH_PATH", "D:\\kimi_code\\GAOKAO-Bench-main")

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
    
    # 验证专家（如果指定了）
    expert = None
    if request.expert_id:
        expert = await session.get(Expert, request.expert_id)
        if not expert:
            raise HTTPException(status_code=404, detail="专家不存在")
    
    # 构建查询
    query = select(BenchmarkDataset)
    
    if request.subject:
        query = query.where(BenchmarkDataset.subject == request.subject)
    if request.year:
        query = query.where(BenchmarkDataset.year == request.year)
    
    if request.mode == "random":
        query = query.order_by(func.random()).limit(100)
    
    result = await session.execute(query)
    questions = result.scalars().all()
    
    if not questions:
        raise HTTPException(status_code=400, detail="没有可用的测试题目")
    
    # 初始化任务状态
    current_test_task = {
        "is_running": True,
        "expert_id": request.expert_id,
        "mode": request.mode,
        "total": len(questions),
        "current": 0,
        "current_question": "",
        "start_time": datetime.now(),
        "error": None,
        "stopped": False
    }
    
    # 后台运行测试
    task = asyncio.create_task(run_benchmark_test(questions, request.expert_id))
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
    
    return {
        "success": True,
        "message": "测试已停止，正在结算...",
        "stopped_at": current_test_task["current"]
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
        "task": None
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
        "recent_results": recent_results
    }


@router.get("/results")
async def get_results(
    page: int = 1,
    page_size: int = 20,
    filter: str = "all",  # 参数名改为 filter，与前端的参数名一致
    subject: Optional[str] = None,
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
    
    # 统计总数
    count_query = select(func.count(BenchmarkResult.id))
    if filter == "correct":
        count_query = count_query.where(BenchmarkResult.is_correct == True)
    elif filter == "wrong":
        count_query = count_query.where(BenchmarkResult.is_correct == False)
    elif filter == "low_score":
        count_query = count_query.where(BenchmarkResult.overall_score < 3)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(BenchmarkResult.created_at.desc())
    
    result = await session.execute(query)
    results = result.scalars().all()
    
    # 格式化结果
    items = []
    
    # 先查询所有SFT数据的问题列表（用于判断是否已加入知识库）
    from app.models.database import SFTData
    sft_result = await session.execute(
        select(SFTData.instruction).distinct()
    )
    sft_questions = set(sft_result.scalars().all())
    
    for r in results:
        dataset = await session.get(BenchmarkDataset, r.dataset_id)
        question = dataset.question if dataset else ""
        
        # 检查是否已在知识库中（通过问题匹配）
        is_in_knowledge_base = question in sft_questions
        
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
    session: AsyncSession = Depends(get_async_session)
):
    """生成详细的评测报告 - 支持实验对比"""
    # 基础统计
    query = select(BenchmarkResult)
    if expert_id:
        query = query.where(BenchmarkResult.expert_id == expert_id)
    
    result = await session.execute(query)
    results = result.scalars().all()
    
    if not results:
        return {"message": "暂无测试数据"}
    
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
    report = await get_benchmark_report(expert_id, session)
    
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
                r["id"], r["subject"], r["year"], 
                "是" if r["is_correct"] else "否",
                r["overall_score"], r["accuracy_score"],
                r["completeness_score"], r["educational_score"],
                r["correct_answer"], r["model_answer"]
            ])
        
        return {"csv_content": output.getvalue()}
    else:
        raise HTTPException(status_code=400, detail="不支持的格式")


@router.post("/add-to-iteration")
async def add_to_iteration(
    request: AddToIterationRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """将错题加入迭代队列（仅标记，不立即生成）"""
    added_count = 0
    already_in_queue = 0
    
    for result_id in request.result_ids:
        result = await session.get(BenchmarkResult, result_id)
        if not result:
            continue
        
        # 检查是否已在队列中
        if result.is_in_iteration_queue:
            already_in_queue += 1
            continue
        
        # 仅标记为待处理，不立即生成
        result.is_in_iteration_queue = True
        result.is_processed = False
        added_count += 1
    
    await session.commit()
    
    msg = f"成功将 {added_count} 道错题加入迭代队列"
    if already_in_queue > 0:
        msg += f"（{already_in_queue} 道已在队列中）"
    
    return {
        "success": True,
        "added_count": added_count,
        "already_in_queue": already_in_queue,
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
                # 检查是否已存在
                existing = await session.execute(
                    select(BenchmarkDataset).where(
                        BenchmarkDataset.question == item.get("question", "")
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

async def _generate_detailed_report(session: AsyncSession, expert_id: Optional[int] = None) -> Dict:
    """生成详细测试报告（内部函数）"""
    # 基础统计
    query = select(BenchmarkResult)
    if expert_id:
        query = query.where(BenchmarkResult.expert_id == expert_id)
    
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

async def run_benchmark_test(questions: List[BenchmarkDataset], expert_id: Optional[int] = None):
    """后台运行基准测试"""
    global current_test_task
    
    async with AsyncSessionLocal() as session:
        try:
            # 如果指定了专家，使用指定专家；否则自动路由
            expert = None
            if expert_id:
                expert = await session.get(Expert, expert_id)
            
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
                
                # 自动路由: 如果没有指定专家，根据题目学科匹配
                current_expert = expert
                if not current_expert:
                    # 根据题目学科查找或创建专家
                    current_expert = await expert_pool.get_or_create_expert(
                        session, 
                        subject=question.subject
                    )
                
                # 检查是否已测试过
                existing = await session.execute(
                    select(BenchmarkResult).where(
                        BenchmarkResult.dataset_id == question.id,
                        BenchmarkResult.expert_id == current_expert.id
                    ).limit(1)
                )
                if existing.scalar_one_or_none():
                    continue
                
                # 调用模型回答（检查停止标志）
                model_answer = ""
                if current_test_task.get("stopped", False):
                    print(f"[Benchmark] 在LLM调用前检测到停止请求")
                    break
                
                # 使用超时包装LLM调用，使取消能更快响应
                try:
                    model_response = await asyncio.wait_for(
                        llm_service.generate(
                            session=session,
                            query=question.question,
                            expert=current_expert,
                            use_rag=True
                        ),
                        timeout=60.0  # 60秒超时（LLM生成可能需要较长时间）
                    )
                    model_answer = model_response["answer"]
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
                
                # 保存结果
                result = BenchmarkResult(
                    dataset_id=question.id,
                    expert_id=current_expert.id,
                    model_answer=model_answer,
                    is_correct=is_correct,
                    accuracy_score=quality_result["accuracy_score"] if quality_result else 0,
                    completeness_score=quality_result["completeness_score"] if quality_result else 0,
                    educational_score=quality_result["educational_score"] if quality_result else 0,
                    overall_score=quality_result["overall_score"] if quality_result else 0,
                    suggestions=quality_result.get("improvement_suggestions", "") if quality_result else ""
                )
                session.add(result)
                await session.commit()
                
                # 延迟5秒避免API限流（Kimi API RPM限制：3次/分钟）
                await asyncio.sleep(5)
            
            current_test_task["is_running"] = False
            
            # 测试完成，自动生成并保存报告
            try:
                print("[Benchmark] 测试完成，正在生成报告...")
                report = await _generate_detailed_report(session, expert_id)
                saved_path = report_saver.save_report(report)
                print(f"[Benchmark] 报告已自动保存: {saved_path}")
            except Exception as report_e:
                print(f"[Benchmark] 保存报告失败: {report_e}")
            
        except asyncio.CancelledError:
            # 任务被取消（用户点击停止）
            print(f"[Benchmark] 测试任务被取消，已完成 {current_test_task['current']} 道题目")
            current_test_task["is_running"] = False
            
            # 即使被停止也尝试保存已完成部分的报告
            try:
                print("[Benchmark] 正在保存已完成的报告...")
                report = await _generate_detailed_report(session, expert_id)
                report["experiment_info"]["stopped"] = True
                saved_path = report_saver.save_report(report)
                print(f"[Benchmark] 报告已保存: {saved_path}")
            except Exception as report_e:
                print(f"[Benchmark] 保存报告失败: {report_e}")
            
        except Exception as e:
            current_test_task["is_running"] = False
            current_test_task["error"] = str(e)
            print(f"基准测试出错: {e}")
            
            # 即使出错也尝试保存已完成的报告
            try:
                report = await _generate_detailed_report(session, expert_id)
                report["experiment_info"]["error"] = str(e)
                saved_path = report_saver.save_report(report)
                print(f"[Benchmark] 错误报告已保存: {saved_path}")
            except Exception as report_e:
                print(f"[Benchmark] 保存错误报告失败: {report_e}")
