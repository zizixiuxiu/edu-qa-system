"""专家池管理器 - 按学科划分，支持动态扩展"""
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
import os

from app.models.database import Expert
from app.core.config import settings


class ExpertPoolManager:
    """
    专家池管理器 - 按学科划分
    
    支持的学科（可扩展）:
    - 数学、物理、化学
    - 语文、英语
    - 生物、历史、地理、政治
    """
    
    # 预定义的学科列表（包含通用专家作为跨学科知识库）
    DEFAULT_SUBJECTS = ["数学", "物理", "化学", "语文", "英语", "生物", "历史", "地理", "政治", "通用"]
    
    def __init__(self):
        self._cache: Dict[str, Expert] = {}  # 按学科缓存
    
    async def get_or_create_expert(
        self,
        session: AsyncSession,
        subject: str
    ) -> Expert:
        """
        获取或创建学科专家
        
        Args:
            subject: 学科名称，如"数学"
        
        Returns:
            Expert: 学科专家对象
        """
        # 标准化学科名称
        subject = subject.strip()
        
        # 先查缓存
        if subject in self._cache:
            return self._cache[subject]
        
        # 查询数据库
        statement = select(Expert).where(Expert.subject == subject)
        result = await session.execute(statement)
        expert = result.scalar_one_or_none()
        
        if expert:
            self._cache[subject] = expert
            return expert
        
        # 创建新专家
        expert_name = f"{subject}专家"
        expert = Expert(
            subject=subject,
            name=expert_name,
            model_type="base",
            lora_path=None,
            is_active=True
        )
        session.add(expert)
        await session.commit()
        await session.refresh(expert)
        
        # 创建专家权重目录
        expert_weight_dir = f"experts/{expert.id}"
        os.makedirs(expert_weight_dir, exist_ok=True)
        
        self._cache[subject] = expert
        print(f"[ExpertPool] 创建新学科专家: {expert_name} (ID: {expert.id})")
        return expert
    
    async def get_expert_by_subject(
        self,
        session: AsyncSession,
        subject: str
    ) -> Optional[Expert]:
        """通过学科名称获取专家"""
        # 先查缓存
        if subject in self._cache:
            return self._cache[subject]
        
        statement = select(Expert).where(Expert.subject == subject)
        result = await session.execute(statement)
        expert = result.scalar_one_or_none()
        
        if expert:
            self._cache[subject] = expert
        
        return expert
    
    async def get_expert(self, session: AsyncSession, expert_id: int) -> Optional[Expert]:
        """通过ID获取专家"""
        # 在缓存中查找
        for expert in self._cache.values():
            if expert.id == expert_id:
                return expert
        
        # 查询数据库
        statement = select(Expert).where(Expert.id == expert_id)
        result = await session.execute(statement)
        expert = result.scalar_one_or_none()
        
        if expert:
            self._cache[expert.subject] = expert
        
        return expert
    
    async def list_experts(
        self,
        session: AsyncSession,
        subject: Optional[str] = None,
        only_active: bool = True
    ) -> List[Expert]:
        """
        列出所有专家
        
        Args:
            subject: 筛选特定学科
            only_active: 只显示启用的专家
        """
        statement = select(Expert)
        
        if subject:
            statement = statement.where(Expert.subject == subject)
        
        if only_active:
            statement = statement.where(Expert.is_active == True)
        
        statement = statement.order_by(Expert.total_qa_count.desc())
        
        result = await session.execute(statement)
        return result.scalars().all()
    
    async def list_all_subjects(self, session: AsyncSession) -> List[Dict]:
        """
        获取所有学科列表（包括未创建专家的）
        
        Returns:
            [{"subject": "数学", "has_expert": true, "expert_id": 1}, ...]
        """
        # 获取已创建的专家学科
        statement = select(Expert).where(Expert.is_active == True)
        result = await session.execute(statement)
        experts = result.scalars().all()
        
        expert_map = {e.subject: e for e in experts}
        
        # 合并默认学科和已创建学科
        all_subjects = set(self.DEFAULT_SUBJECTS) | set(expert_map.keys())
        
        return [
            {
                "subject": subject,
                "has_expert": subject in expert_map,
                "expert_id": expert_map[subject].id if subject in expert_map else None,
                "is_default": subject in self.DEFAULT_SUBJECTS
            }
            for subject in sorted(all_subjects)
        ]
    
    async def update_expert_stats(
        self,
        session: AsyncSession,
        expert_id: int,
        response_time: float,
        is_accurate: bool
    ):
        """更新专家统计数据"""
        expert = await self.get_expert(session, expert_id)
        if not expert:
            return
        
        # 更新平均响应时间 (滑动平均)
        n = expert.total_qa_count
        expert.avg_response_time = (expert.avg_response_time * n + response_time) / (n + 1)
        
        # 更新准确率
        current_correct = expert.accuracy_rate * n
        if is_accurate:
            current_correct += 1
        expert.accuracy_rate = current_correct / (n + 1)
        
        expert.total_qa_count += 1
        
        await session.commit()
        
        # 更新缓存
        self._cache[expert.subject] = expert
    
    async def toggle_expert_status(
        self,
        session: AsyncSession,
        expert_id: int,
        is_active: bool
    ) -> bool:
        """启用/禁用专家"""
        expert = await self.get_expert(session, expert_id)
        if expert:
            expert.is_active = is_active
            await session.commit()
            self._cache[expert.subject] = expert
            return True
        return False
    
    async def delete_expert(self, session: AsyncSession, expert_id: int) -> bool:
        """删除专家"""
        expert = await self.get_expert(session, expert_id)
        if expert:
            await session.delete(expert)
            await session.commit()
            # 从缓存中移除
            if expert.subject in self._cache:
                del self._cache[expert.subject]
            return True
        return False
    
    def get_expert_prompt(self, expert: Expert) -> str:
        """获取专家的角色Prompt - 使用 Markdown 格式"""
        
        format_instructions = """
请使用 Markdown 格式回答，遵循以下规则：

1. 标题层级：使用 ## 作为主标题，### 作为子标题
2. 重点内容：使用 **粗体** 标记关键概念
3. 列表：使用 - 或 1. 2. 3. 组织要点
4. 公式：行内公式用 $...$，块级公式用 $$...$$
5. 分隔：不同部分之间用 --- 分隔
6. 引用：重要结论使用 > 引用格式

示例格式：
## 核心概念

**关键术语**的解释内容...

### 详细说明

- 要点一：说明内容
- 要点二：说明内容

---

## 公式推导

$$E = mc^2$$

其中 $E$ 表示能量，$m$ 表示质量，$c$ 表示光速。
"""
        
        prompts = {
            "数学": f"""你是一位资深的数学教育专家。

{format_instructions}

解答数学问题时：
- 用 ## 标注"解题步骤"
- 用 ### 标注每一步的具体操作
- 公式用 $...$ 包裹
- 关键数字和结果用 **粗体** 标出
- 多步骤之间用 --- 分隔""",
            
            "物理": f"""你是一位物理学科专家。

{format_instructions}

解答物理问题时：
- 用 ## 标注"物理原理"
- 用 ## 标注"公式推导"
- 用 ## 标注"应用实例"
- 物理量用 **粗体** 标记，如 **F**、**m**、**a**
- 单位用行内代码标注，如 `N`、`kg`、`m/s²`
- 不同板块之间用 --- 分隔""",
            
            "化学": f"""你是一位化学教育专家。

{format_instructions}

解答化学问题时：
- 用 ## 标注"化学原理"
- 用 ## 标注"反应方程式"
- 化学式用行内代码，如 `H₂O`、`CO₂`
- 关键概念用 **粗体** 标记
- 实验步骤用编号列表 1. 2. 3.""",
            
            "语文": f"""你是一位语文教育专家。

{format_instructions}

解答语文问题时：
- 用 ## 标注"文本分析"
- 用 ## 标注"写作技巧"
- 引用原文使用 > 引用格式
- 修辞手法用 **粗体** 标出
- 分点论述使用 - 列表""",
            
            "英语": f"""你是一位英语教学专家。

{format_instructions}

解答英语问题时：
- 用 ## 标注"语法解析"
- 用 ## 标注"词汇讲解"
- 例句用 > 引用格式
- 重点短语用 **粗体** 标出
- 语法规则用 ### 子标题分层""",
            
            "生物": f"""你是一位生物学科专家。

{format_instructions}

解答生物问题时：
- 用 ## 标注"生物学概念"
- 用 ## 标注"生理机制"
- 生物术语用 **粗体** 标记
- 过程描述用编号列表 1. 2. 3.
- 结构层次用 ### 子标题""",
            
            "历史": f"""你是一位历史教育专家。

{format_instructions}

解答历史问题时：
- 用 ## 标注"历史背景"
- 用 ## 标注"事件经过"
- 用 ## 标注"历史影响"
- 时间、人物用 **粗体** 标出
- 史料引用用 > 引用格式
- 多角度分析用 --- 分隔""",
            
            "地理": f"""你是一位地理学科专家。

{format_instructions}

解答地理问题时：
- 用 ## 标注"地理概念"
- 用 ## 标注"空间分布"
- 用 ## 标注"形成原因"
- 地理数据用 **粗体** 标出
- 分点论述使用 - 列表""",
            
            "政治": f"""你是一位思想政治教育专家。

{format_instructions}

解答政治问题时：
- 用 ## 标注"理论要点"
- 用 ## 标注"现实意义"
- 核心概念用 **粗体** 标出
- 理论联系实际用 > 引用格式
- 分层次论述用 ### 子标题""",
            
            "通用": f"""你是一位跨学科知识助手，擅长处理涉及多个学科领域的问题。

{format_instructions}

解答跨学科问题时：
- 用 ## 标注涉及的学科领域
- 用 ### 标注各学科的核心概念
- 用 **粗体** 标记关键术语和结论
- 用 --- 分隔不同学科的内容
- 最后总结各学科之间的关联""",
            
            "default": f"""你是一位专业的教育助手。

{format_instructions}

解答问题时：
- 用 ## 组织主要板块
- 用 **粗体** 标记关键信息
- 用 - 或编号组织要点
- 用 --- 分隔不同部分"""
        }
        
        return prompts.get(expert.subject, prompts["default"])
    
    async def ensure_default_experts(self, session: AsyncSession):
        """
        确保默认学科专家已创建
        用于系统初始化
        """
        created = []
        for subject in self.DEFAULT_SUBJECTS:
            expert = await self.get_or_create_expert(session, subject)
            created.append(expert.subject)
        
        print(f"[ExpertPool] 已确保 {len(created)} 个默认学科专家: {', '.join(created)}")
        return created


# 全局单例
expert_pool = ExpertPoolManager()
