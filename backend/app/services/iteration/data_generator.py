"""数据生成服务 - 存储云端优质回答到知识库（支持知识类型分类）"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional, Tuple
import re

from app.core.config import settings
from app.models.database import Knowledge, SFTData
from app.services.iteration.deduplication import deduplication_service
from app.utils.embedding import embedding_service


class DataGenerator:
    """
    数据生成器 - 将云端优质回答存入知识库
    
    核心功能:
    1. 存储云端纠正后的完整高质量回答到知识库
    2. 自动分类知识类型 (qa/concept/formula/template/step)
    3. 生成精简的检索内容，节省token
    4. 生成Alpaca格式的微调数据
    """
    
    # 各学科知识类型权重配置
    SUBJECT_TYPE_WEIGHTS = {
        "数学": {"formula": 0.3, "template": 0.25, "step": 0.25, "concept": 0.15, "qa": 0.05},
        "物理": {"formula": 0.35, "concept": 0.25, "step": 0.2, "template": 0.15, "qa": 0.05},
        "化学": {"formula": 0.3, "concept": 0.3, "step": 0.2, "template": 0.15, "qa": 0.05},
        "语文": {"concept": 0.35, "template": 0.3, "qa": 0.2, "step": 0.1, "formula": 0.05},
        "英语": {"template": 0.35, "concept": 0.25, "qa": 0.25, "step": 0.1, "formula": 0.05},
        "生物": {"concept": 0.4, "step": 0.25, "template": 0.2, "qa": 0.1, "formula": 0.05},
        "历史": {"concept": 0.4, "template": 0.3, "qa": 0.2, "step": 0.1, "formula": 0},
        "地理": {"concept": 0.35, "template": 0.25, "step": 0.2, "qa": 0.15, "formula": 0.05},
        "政治": {"concept": 0.4, "template": 0.3, "qa": 0.2, "step": 0.1, "formula": 0},
        "通用": {"qa": 0.4, "concept": 0.25, "template": 0.2, "step": 0.1, "formula": 0.05}
    }
    
    # 类型识别关键词
    TYPE_KEYWORDS = {
        "formula": ["公式", "定理", "定律", "恒等式", "方程", "=", "+", "-", "×", "÷", "∫", "∑", "π", "√"],
        "concept": ["定义", "概念", "意义", "性质", "特点", "特征", "含义", "是什么", "指"],
        "template": ["模板", "套路", "格式", "范文", "句式", "句型", "写作", "结构", "框架"],
        "step": ["步骤", "流程", "方法", "解法", "算法", "过程", "操作", "程序", "阶段"],
        "qa": ["为什么", "怎么办", "如何", "吗？", "呢？", "？"]  # 默认类型
    }
    
    def classify_knowledge_type(self, question: str, answer: str, subject: str) -> str:
        """
        自动识别知识类型
        
        Returns:
            "qa" | "concept" | "formula" | "template" | "step"
        """
        text = (question + " " + answer).lower()
        scores = {k: 0 for k in ["qa", "concept", "formula", "template", "step"]}
        
        # 关键词匹配
        for type_name, keywords in self.TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[type_name] += 1
        
        # 数学公式特殊检测
        if subject in ["数学", "物理", "化学"]:
            # 检测LaTeX公式或数学符号
            if re.search(r'[\$\\\[\]\{\}^_\d+\-*/=<>]+', answer) or "=" in answer:
                scores["formula"] += 2
            # 检测步骤类描述
            if re.search(r'(第[一二三四五六]步|step\s*\d|①|②|③|1\.|2\.|3\.)', answer):
                scores["step"] += 2
        
        # 获取该学科的权重
        weights = self.SUBJECT_TYPE_WEIGHTS.get(subject, self.SUBJECT_TYPE_WEIGHTS["通用"])
        
        # 加权计算
        for type_name in scores:
            scores[type_name] *= weights.get(type_name, 0.1)
        
        # 返回得分最高的类型
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "qa"
    
    def extract_search_content(self, question: str, answer: str, knowledge_type: str, subject: str) -> str:
        """
        提取精简的检索内容，节省embedding token
        
        策略：
        - 保留核心问题和关键概念
        - 去除冗余解释
        - 根据类型提取关键信息
        """
        # 基础内容：问题核心
        content_parts = [question]
        
        if knowledge_type == "formula":
            # 公式类：提取公式本身和适用条件
            formulas = re.findall(r'[\w\s]+[=＝][\w\s\+\-\*/\(\)\.]+', answer)
            if formulas:
                content_parts.append(f"公式: {formulas[0]}")
            # 提取适用条件（前50字）
            condition_match = re.search(r'适用[于]?|condition|apply', answer)
            if condition_match:
                start = condition_match.start()
                content_parts.append(answer[start:start+50])
                
        elif knowledge_type == "concept":
            # 概念类：提取定义句（通常是前两句）
            sentences = re.split(r'[。！？]', answer)[:2]
            content_parts.extend([s for s in sentences if len(s) > 10])
            
        elif knowledge_type == "step":
            # 步骤类：提取步骤标题
            steps = re.findall(r'(\d+[\.\uff0e\uff09]|第[\d一二三四五六]步|step\s*\d+)[:\uff1a\s]*(.{10,30})', answer)
            for i, (num, desc) in enumerate(steps[:5], 1):  # 最多5步
                content_parts.append(f"步骤{i}: {desc}")
                
        elif knowledge_type == "template":
            # 模板类：提取模板结构和关键词
            content_parts.append("模板结构")
            # 提取列表项
            items = re.findall(r'[\-\*\d+][\.\uff0e\uff09]\s*(.{5,20})', answer)
            content_parts.extend(items[:4])
            
        else:  # qa
            # 问答类：提取核心结论（前100字）
            conclusion = answer[:150] if len(answer) > 150 else answer
            content_parts.append(f"答案: {conclusion}")
        
        # 合并并截断，控制在200字以内（节省embedding成本）
        result = " | ".join(content_parts)
        return result[:200] if len(result) > 200 else result
    
    async def process_quality_answer(
        self,
        session: AsyncSession,
        expert_id: int,
        question: str,
        corrected_answer: str,
        quality_score: float,
        session_id: int,
        subject: str = "",
        knowledge_type: str = None  # 新增：来自质检结果的类型
    ) -> Dict[str, any]:
        """
        处理高质量答案 - 智能分类 + 精简存储 + 生成微调数据
        
        Args:
            knowledge_type: 如果为None则自动分类，否则使用提供的类型（来自质检）
        
        Returns:
            {
                "knowledge_added": bool,
                "sft_data_added": bool,
                "knowledge_type": str,
                "search_content_length": int
            }
        """
        result = {
            "knowledge_added": False, 
            "sft_data_added": False,
            "knowledge_type": knowledge_type or "qa",
            "search_content_length": 0
        }
        
        # 1. 确定知识类型（优先使用质检结果的类型，否则自动分类）
        if not knowledge_type:
            knowledge_type = self.classify_knowledge_type(question, corrected_answer, subject)
            result["knowledge_type"] = knowledge_type
        
        # 2. 准备检索内容（用于去重和embedding）
        # 格式：问题 + 答案前500字
        answer_part = corrected_answer[:500] if len(corrected_answer) > 500 else corrected_answer
        dedup_content = f"问题：{question}\n答案：{answer_part}"
        result["search_content_length"] = len(dedup_content)
        
        # 3. 检查重复（使用与存储完全相同的内容格式）
        duplicate = await deduplication_service.check_knowledge_duplicate(
            session, expert_id, dedup_content
        )
        
        if duplicate is None:  # 不重复
            # 使用相同的内容生成embedding
            retrieval_context = dedup_content
            
            # 生成embedding
            if settings.SIMULATION_MODE:
                import random
                import hashlib
                seed = int(hashlib.md5(retrieval_context.encode()).hexdigest(), 16) % (2**32)
                random.seed(seed)
                embedding = [random.random() for _ in range(384)]
            else:
                embedding = embedding_service.encode(retrieval_context)
            
            # 存储知识 - 使用 question/answer 主字段，content存检索内容
            knowledge = Knowledge(
                expert_id=expert_id,
                question=question,  # 问题字段（必填）
                answer=corrected_answer,  # 答案字段（必填）
                content=retrieval_context,  # 检索内容（用于embedding匹配）
                embedding=embedding,
                knowledge_type=knowledge_type,
                source_type="generated",
                quality_score=quality_score,
                tier=1 if quality_score >= 4.5 else 2,  # 高质量知识设为 tier 1
                meta_data={
                    "question": question,
                    "answer": corrected_answer,
                    "knowledge_type": knowledge_type,
                    "subject": subject,
                    "source_session_id": session_id,
                    "quality_score": quality_score,
                    "retrieval_context": retrieval_context,
                }
            )
            session.add(knowledge)
            result["knowledge_added"] = True
            print(f"[DataGenerator] 新增{knowledge_type}类知识 (质量{quality_score:.2f}, 长度{len(corrected_answer)}): {question[:40]}...")
        else:
            print(f"[DataGenerator] 已存在相似内容: {question[:40]}...")
        
        # 4. 生成微调数据
        is_duplicate = await deduplication_service.check_sft_data_duplicate(
            session, expert_id, question, ""
        )
        
        if not is_duplicate:
            sft_data = SFTData(
                expert_id=expert_id,
                instruction=question,
                input="",
                output=corrected_answer,
                source_session_id=session_id,
                quality_score=quality_score,
                is_used_in_training=False
            )
            session.add(sft_data)
            result["sft_data_added"] = True
        
        # 提交事务
        await session.commit()
        
        # 更新专家统计
        if result["knowledge_added"] or result["sft_data_added"]:
            await self._update_expert_counts(session, expert_id)
        
        return result
    
    async def _update_expert_counts(self, session: AsyncSession, expert_id: int):
        """更新专家的统计计数"""
        from sqlalchemy import func, select
        from app.models.database import Expert
        
        # 统计各类型的知识库数量
        type_counts = {}
        for ktype in ["qa", "concept", "formula", "template", "step"]:
            count = await session.execute(
                select(func.count(Knowledge.id))
                .where(Knowledge.expert_id == expert_id)
                .where(Knowledge.knowledge_type == ktype)
            )
            type_counts[ktype] = count.scalar()
        
        # 统计总数
        total_knowledge = await session.execute(
            select(func.count(Knowledge.id)).where(Knowledge.expert_id == expert_id)
        )
        
        # 统计微调数据数量
        sft_count = await session.execute(
            select(func.count(SFTData.id)).where(SFTData.expert_id == expert_id)
        )
        
        # 更新专家
        expert = await session.get(Expert, expert_id)
        if expert:
            expert.knowledge_count = total_knowledge.scalar()
            expert.sft_data_count = sft_count.scalar()
            # 可以在meta中存储各类型分布
            await session.commit()
            print(f"[DataGenerator] 专家{expert.name} 知识库: {expert.knowledge_count} (各类型: {type_counts})")


data_generator = DataGenerator()
