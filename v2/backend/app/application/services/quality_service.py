"""云端质检服务 - 知识质量评估与入库"""
import asyncio
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime

from ...core.config import get_settings
from ...core.logging import LoggerMixin
from ...domain.models.knowledge import (
    KnowledgeItem, KnowledgeMetadata, KnowledgeTier, 
    KnowledgeType, QualityScores
)
from ...domain.models.session import QAInteraction

settings = get_settings()


@dataclass
class QualityCheckResult:
    """质检结果"""
    overall_score: float  # 总分 0-5
    accuracy_score: float  # 准确度
    completeness_score: float  # 完整性
    clarity_score: float  # 清晰性
    educational_score: float  # 教育价值
    format_score: float  # 格式规范
    knowledge_type: str  # 识别出的知识类型
    is_qualified: bool  # 是否合格（≥4.0）
    feedback: str  # 改进建议


class CloudQualityChecker(LoggerMixin):
    """
    云端质检服务
    
    使用Kimi/Moonshot API进行质量评估
    支持差异化权重：不同知识类型有不同的评分维度权重
    """
    
    # 知识类型识别模式 + 差异化权重（论文表4）
    TYPE_PATTERNS = {
        KnowledgeType.FORMULA: {
            "patterns": ["=", "+", "-", "*", "/", "^", "√", "π", "∫", "∑", "lim", "dx", "dy"],
            "keywords": ["公式", "定律", "定理", "恒等式", "方程"],
            "weights": {"accuracy": 0.40, "completeness": 0.25, "educational": 0.15, "format": 0.20}
        },
        KnowledgeType.CONCEPT: {
            "patterns": [],
            "keywords": ["定义", "概念", "是什么", "指", "称为", "意思"],
            "weights": {"accuracy": 0.35, "completeness": 0.30, "educational": 0.35}
        },
        KnowledgeType.TEMPLATE: {
            "patterns": [],
            "keywords": ["模板", "格式", "范文", "示例", "样例", "参考"],
            "weights": {"accuracy": 0.30, "completeness": 0.40, "practicality": 0.30}
        },
        KnowledgeType.STEP: {
            "patterns": ["①", "②", "③", "④", "⑤", "(1)", "(2)", "(3)"],
            "keywords": ["第一步", "首先", "接着", "然后", "最后", "步骤"],
            "weights": {"accuracy": 0.30, "completeness": 0.40, "logic": 0.30}
        },
        KnowledgeType.QA: {
            "patterns": [],
            "keywords": ["问题", "答案", "问", "答", "为什么", "怎么"],
            "weights": {"accuracy": 0.35, "completeness": 0.35, "educational": 0.30}
        }
    }
    
    def __init__(self):
        self.base_url = settings.KIMI_BASE_URL
        self.api_key = settings.KIMI_API_KEY
        self.model = settings.KIMI_MODEL
        self.quality_threshold = settings.KNOWLEDGE_QUALITY_THRESHOLD  # 4.0
        
    def identify_knowledge_type(self, question: str, answer: str) -> KnowledgeType:
        """
        自动识别知识类型
        
        基于关键词和模式匹配
        """
        content = f"{question} {answer}".lower()
        
        scores = {}
        for k_type, config in self.TYPE_PATTERNS.items():
            score = 0
            # 关键词匹配
            for keyword in config["keywords"]:
                if keyword in content:
                    score += 2
            # 模式匹配
            for pattern in config["patterns"]:
                if pattern in content:
                    score += 1
            scores[k_type] = score
        
        if not scores or max(scores.values()) == 0:
            return KnowledgeType.QA
        
        return max(scores, key=scores.get)
    
    async def check_quality(
        self,
        question: str,
        answer: str,
        subject: str,
        knowledge_type: Optional[KnowledgeType] = None
    ) -> QualityCheckResult:
        """
        执行云端质量检查
        
        Args:
            question: 问题
            answer: 答案
            subject: 学科
            knowledge_type: 知识类型（可选，自动识别）
            
        Returns:
            质检结果
        """
        # 自动识别知识类型
        if knowledge_type is None:
            knowledge_type = self.identify_knowledge_type(question, answer)
        
        # 调用Kimi API进行评分
        scores = await self._call_quality_api(
            question, answer, subject, knowledge_type
        )
        
        # 计算加权总分
        overall_score = self._calculate_weighted_score(scores, knowledge_type)
        
        return QualityCheckResult(
            overall_score=overall_score,
            accuracy_score=scores.get("accuracy", 0),
            completeness_score=scores.get("completeness", 0),
            clarity_score=scores.get("clarity", 0),
            educational_score=scores.get("educational", 0),
            format_score=scores.get("format", 0),
            knowledge_type=knowledge_type.value,
            is_qualified=overall_score >= self.quality_threshold,
            feedback=scores.get("feedback", "")
        )
    
    async def _call_quality_api(
        self,
        question: str,
        answer: str,
        subject: str,
        knowledge_type: KnowledgeType
    ) -> Dict[str, float]:
        """
        调用Kimi API进行质量评分
        
        如果API不可用，使用本地规则评分作为fallback
        """
        try:
            prompt = self._build_quality_prompt(question, answer, subject, knowledge_type)
            
            import aiohttp
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个教育内容质量评估专家。请对给定的问答对进行评分。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        return self._parse_quality_response(content)
                    else:
                        raise Exception(f"API错误: {response.status}")
                        
        except Exception as e:
            self.logger.warning(f"云端质检失败: {e}，使用本地规则评分")
            return self._local_quality_score(question, answer, knowledge_type)
    
    def _build_quality_prompt(
        self,
        question: str,
        answer: str,
        subject: str,
        knowledge_type: KnowledgeType
    ) -> str:
        """构建质量评估提示词"""
        type_weights = self.TYPE_PATTERNS.get(knowledge_type, self.TYPE_PATTERNS[KnowledgeType.QA])
        weights_desc = "\n".join([f"- {k}: {v*100:.0f}%" for k, v in type_weights["weights"].items()])
        
        return f"""请对以下{subject}学科的{knowledge_type.value}类型问答对进行质量评估：

【问题】
{question}

【答案】
{answer}

请从以下维度评分（0-5分）：
{weights_desc}

请以JSON格式返回：
{{
    "accuracy": float,      // 准确度/正确性
    "completeness": float,  // 完整性
    "clarity": float,       // 清晰性
    "educational": float,   // 教育价值
    "format": float,        // 格式规范（如适用）
    "feedback": string      // 改进建议（50字以内）
}}"""
    
    def _parse_quality_response(self, content: str) -> Dict[str, float]:
        """解析API返回的评分"""
        import json
        import re
        
        # 提取JSON
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return {
                    "accuracy": float(data.get("accuracy", 3.0)),
                    "completeness": float(data.get("completeness", 3.0)),
                    "clarity": float(data.get("clarity", 3.0)),
                    "educational": float(data.get("educational", 3.0)),
                    "format": float(data.get("format", 3.0)),
                    "feedback": data.get("feedback", "")
                }
            except (json.JSONDecodeError, ValueError):
                pass
        
        # 解析失败返回默认值
        return {"accuracy": 3.0, "completeness": 3.0, "clarity": 3.0, 
                "educational": 3.0, "format": 3.0, "feedback": "解析失败"}
    
    def _local_quality_score(
        self,
        question: str,
        answer: str,
        knowledge_type: KnowledgeType
    ) -> Dict[str, float]:
        """本地规则评分（fallback）"""
        # 基于答案长度、结构等简单规则
        answer_len = len(answer)
        
        # 完整性：基于长度
        completeness = min(5.0, 2.0 + answer_len / 200)
        
        # 清晰性：检查是否有列表、步骤标记
        clarity = 3.0
        if any(m in answer for m in ["①", "②", "1.", "2.", "首先", "然后"]):
            clarity = 4.5
        
        # 教育价值：检查是否有解释说明
        educational = 3.5 if ("因为" in answer or "所以" in answer or "解释" in answer) else 3.0
        
        return {
            "accuracy": 3.5,
            "completeness": completeness,
            "clarity": clarity,
            "educational": educational,
            "format": 4.0 if "\n" in answer else 3.0,
            "feedback": "本地规则评分"
        }
    
    def _calculate_weighted_score(
        self,
        scores: Dict[str, float],
        knowledge_type: KnowledgeType
    ) -> float:
        """计算加权总分"""
        type_config = self.TYPE_PATTERNS.get(knowledge_type, self.TYPE_PATTERNS[KnowledgeType.QA])
        weights = type_config["weights"]
        
        total_score = 0.0
        total_weight = 0.0
        
        for dim, weight in weights.items():
            if dim in scores:
                total_score += scores[dim] * weight
                total_weight += weight
        
        return round(total_score / total_weight, 2) if total_weight > 0 else 3.0
    
    async def process_interaction(
        self,
        interaction: QAInteraction,
        expert_id: int,
        session_id: str
    ) -> Optional[KnowledgeItem]:
        """
        处理QA交互，进行质检并决定是否入库
        
        这是自我进化闭环的核心方法
        """
        question = interaction.question.content
        answer = interaction.answer.content
        
        # 1. 执行质检
        result = await self.check_quality(
            question=question,
            answer=answer,
            subject="unknown",  # 可以从expert获取
        )
        
        # 2. 创建质量评估对象
        quality = QualityScores(
            overall=result.overall_score,
            accuracy=result.accuracy_score,
            completeness=result.completeness_score,
            educational=result.educational_score,
            clarity=result.clarity_score
        )
        
        # 3. 更新交互记录
        from ...domain.models.session import QualityAssessment
        interaction.set_assessment(QualityAssessment(
            correctness_score=result.accuracy_score,
            completeness_score=result.completeness_score,
            clarity_score=result.clarity_score,
            educational_value_score=result.educational_score,
            overall_score=result.overall_score,
            is_correct=result.is_qualified,
            feedback=result.feedback
        ))
        
        # 4. 检查是否合格入库
        if not result.is_qualified:
            self.logger.info(f"质量不合格({result.overall_score:.1f})，不入库")
            return None
        
        # 5. 检查去重
        from ...domain.services.rag_service import get_retriever
        retriever = get_retriever()
        duplicate = await retriever.check_duplicate(answer)
        
        if duplicate:
            self.logger.info(f"发现重复知识(相似度{duplicate[1]:.2f})，不入库")
            return None
        
        # 6. 生成向量
        from ...infrastructure.embedding.bge_encoder import encode_text
        embeddings = await encode_text(answer)
        
        # 7. 创建知识项
        metadata = KnowledgeMetadata(
            question=question,
            answer=answer,
            knowledge_type=KnowledgeType(result.knowledge_type),
            source_session_id=session_id
        )
        
        knowledge = KnowledgeItem(
            expert_id=expert_id,
            content=answer,
            embedding=embeddings[0],
            metadata=metadata,
            tier=KnowledgeTier.TIER0,  # 质检合格的知识进入Tier 0
            quality=quality
        )
        
        self.logger.info(f"知识质检合格，准备入库: score={result.overall_score:.1f}, type={result.knowledge_type}")
        return knowledge


# 全局质检服务实例
_quality_checker = None


def get_quality_checker() -> CloudQualityChecker:
    """获取全局质检服务实例"""
    global _quality_checker
    if _quality_checker is None:
        _quality_checker = CloudQualityChecker()
    return _quality_checker
