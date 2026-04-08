"""云端质检服务 - 使用Moonshot API进行质量评估"""
import aiohttp
import json
from typing import Dict, Optional, Tuple
from ...core.config import get_settings
from ...core.logging import LoggerMixin

settings = get_settings()


class CloudQualityService(LoggerMixin):
    """云端质量检查服务 - 使用Moonshot Kimi K2.5"""
    
    def __init__(self):
        self.base_url = settings.KIMI_BASE_URL
        self.api_key = settings.KIMI_API_KEY
        self.model = settings.KIMI_MODEL
        self.timeout = 60.0
        self.logger.info(f"云端质检服务初始化: {self.model}")
    
    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        subject: str,
        knowledge_type: str = "qa"
    ) -> Tuple[float, Dict[str, float], str]:
        """
        评估答案质量
        
        Returns:
            (overall_score, detail_scores, feedback)
            overall_score: 0-5分
            detail_scores: {"accuracy": x, "completeness": y, ...}
            feedback: 改进建议
        """
        prompt = self._build_evaluation_prompt(question, answer, subject, knowledge_type)
        
        try:
            result = await self._call_api(prompt)
            return self._parse_evaluation(result)
        except Exception as e:
            self.logger.error(f"云端质检失败: {e}")
            # 返回默认分数，不阻塞流程
            return 3.0, {"accuracy": 3, "completeness": 3, "clarity": 3, "educational": 3}, "评估失败"
    
    def _build_evaluation_prompt(
        self,
        question: str,
        answer: str,
        subject: str,
        knowledge_type: str
    ) -> str:
        """构建评估提示词"""
        type_weights = {
            "formula": {"accuracy": 0.4, "completeness": 0.25, "clarity": 0.2, "educational": 0.15},
            "concept": {"accuracy": 0.3, "completeness": 0.25, "clarity": 0.2, "educational": 0.25},
            "step": {"accuracy": 0.35, "completeness": 0.3, "clarity": 0.25, "educational": 0.1},
            "template": {"accuracy": 0.3, "completeness": 0.25, "clarity": 0.25, "educational": 0.2},
            "qa": {"accuracy": 0.4, "completeness": 0.3, "clarity": 0.2, "educational": 0.1},
        }
        
        weights = type_weights.get(knowledge_type, type_weights["qa"])
        
        return f"""你是一位资深教育专家，请对以下{subject}学科的问答进行质量评估。

【问题】
{question}

【学生回答】
{answer}

请从以下四个维度评估（每项0-5分）：
1. 准确性(accuracy)：内容是否正确，有无事实错误
2. 完整性(completeness)：是否涵盖了问题的关键要点
3. 清晰度(clarity)：表达是否清晰易懂
4. 教育性(educational)：是否有助于学习和理解

权重配置：准确性{weights['accuracy']*100}%，完整性{weights['completeness']*100}%，清晰度{weights['clarity']*100}%，教育性{weights['educational']*100}%

请以JSON格式返回：
{{
    "accuracy": 分数,
    "completeness": 分数,
    "clarity": 分数,
    "educational": 分数,
    "overall": 加权总分,
    "is_correct": 是否正确(true/false),
    "feedback": "改进建议"
}}"""
    
    async def _call_api(self, prompt: str) -> str:
        """调用Moonshot API"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API错误: {response.status} - {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]
    
    def _parse_evaluation(self, content: str) -> Tuple[float, Dict[str, float], str]:
        """解析评估结果"""
        try:
            # 提取JSON
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            overall = float(data.get("overall", 3.0))
            detail_scores = {
                "accuracy": float(data.get("accuracy", 3.0)),
                "completeness": float(data.get("completeness", 3.0)),
                "clarity": float(data.get("clarity", 3.0)),
                "educational": float(data.get("educational", 3.0)),
            }
            feedback = data.get("feedback", "")
            
            return overall, detail_scores, feedback
        except Exception as e:
            self.logger.error(f"解析评估结果失败: {e}")
            return 3.0, {"accuracy": 3, "completeness": 3, "clarity": 3, "educational": 3}, "解析失败"
    
    async def should_add_to_knowledge_base(
        self,
        question: str,
        answer: str,
        threshold: float = 4.0
    ) -> Tuple[bool, float]:
        """判断是否应该加入知识库"""
        overall_score, _, _ = await self.evaluate_answer(question, answer, "general")
        return overall_score >= threshold, overall_score


# 全局云端质检服务实例
cloud_quality_service = CloudQualityService()
