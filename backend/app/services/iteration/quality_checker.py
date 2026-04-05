"""
质量检查服务 - 云端API纠正和评分（支持知识类型差异化评估）
"""
import httpx
from typing import Optional, Dict, Tuple
from app.core.config import settings


class QualityChecker:
    """
    质量检查器 - 使用云端大模型进行答案质检
    
    核心功能:
    1. 自动识别知识类型
    2. 根据类型差异化评估（不同权重、不同标准）
    3. 给出质量评分和纠正后的答案
    
    评估维度：
    - 准确性 (accuracy): 内容是否正确
    - 完整性 (completeness): 是否覆盖所有要点
    - 教育性 (educational): 是否易于理解
    - 规范性 (standardization): 格式是否规范（公式/步骤类）
    - 实用性 (practicality): 是否实用（模板类）
    - 逻辑性 (logic): 逻辑是否清晰（步骤类）
    """
    
    # 知识类型权重配置
    TYPE_WEIGHTS = {
        "formula": {
            "accuracy": 0.40,        # 公式准确性最重要
            "completeness": 0.25,    # 公式完整
            "standardization": 0.20, # 格式规范
            "educational": 0.15      # 易于理解
        },
        "concept": {
            "accuracy": 0.35,        # 概念准确
            "educational": 0.35,     # 教育性重要
            "completeness": 0.30     # 定义完整
        },
        "template": {
            "completeness": 0.40,    # 模板完整
            "practicality": 0.30,    # 实用性
            "accuracy": 0.30         # 内容准确
        },
        "step": {
            "completeness": 0.40,    # 步骤完整
            "logic": 0.30,           # 逻辑清晰
            "accuracy": 0.30         # 操作准确
        },
        "qa": {
            "accuracy": 0.35,        # 回答准确
            "completeness": 0.35,    # 回答完整
            "educational": 0.30      # 易于理解
        }
    }
    
    # 类型评估标准（用于prompt）
    TYPE_CRITERIA = {
        "formula": """
【公式/定律类评估标准】
1. 准确性(40%): 公式是否正确，符号是否准确
2. 完整性(25%): 是否包含适用条件、参数说明
3. 规范性(20%): 格式是否标准（如 LaTeX 规范）
4. 教育性(15%): 是否有推导或说明，易于理解
评分标准：满分5分，≥4.0为高质量，3.0-4.0为中等，<3.0为低质量""",
        
        "concept": """
【核心概念类评估标准】
1. 准确性(35%): 定义是否准确，无错误
2. 教育性(35%): 是否通俗易懂，有例子说明
3. 完整性(30%): 是否涵盖概念的核心要素
评分标准：满分5分，≥4.0为高质量，3.0-4.0为中等，<3.0为低质量""",
        
        "template": """
【解题模板类评估标准】
1. 完整性(40%): 模板结构是否完整，步骤是否齐全
2. 实用性(30%): 是否可直接套用，变式是否通用
3. 准确性(30%): 模板逻辑是否正确
评分标准：满分5分，≥4.0为高质量，3.0-4.0为中等，<3.0为低质量""",
        
        "step": """
【步骤/方法类评估标准】
1. 完整性(40%): 步骤是否完整，无遗漏
2. 逻辑性(30%): 步骤顺序是否合理，因果清晰
3. 准确性(30%): 每一步操作是否正确
评分标准：满分5分，≥4.0为高质量，3.0-4.0为中等，<3.0为低质量""",
        
        "qa": """
【问答对类评估标准】
1. 准确性(35%): 回答内容是否正确
2. 完整性(35%): 是否回答了问题的所有部分
3. 教育性(30%): 解释是否清晰，有条理
评分标准：满分5分，≥4.0为高质量，3.0-4.0为中等，<3.0为低质量"""
    }
    
    def __init__(self):
        self.api_key = settings.CLOUD_API_KEY
        self.base_url = settings.CLOUD_BASE_URL
        self.model = settings.CLOUD_MODEL
    
    def classify_content_type(self, question: str, answer: str, subject: str) -> str:
        """
        自动识别内容类型
        
        Returns: "formula" | "concept" | "template" | "step" | "qa"
        """
        import re
        
        text = (question + " " + answer).lower()
        
        # 公式类检测
        if subject in ["数学", "物理", "化学"]:
            if re.search(r'[=\+\-\*/\^∫∑π√∂ΔΣ]{2,}', answer):
                return "formula"
        
        # 概念类检测
        if any(kw in text for kw in ["定义", "概念", "含义", "是什么", "什么是", "意思"]):
            return "concept"
        
        # 模板类检测
        if any(kw in text for kw in ["模板", "格式", "范文", "句式", "套路", "写作"]):
            return "template"
        
        # 步骤类检测
        if re.search(r'(第[一二三四五六]步|step\s*\d|①|②|③|1\.|2\.|步骤)', answer):
            return "step"
        
        # 默认问答类
        return "qa"
    
    async def check_answer(
        self,
        question: str,
        local_answer: str,
        expert_subject: str
    ) -> Optional[Dict]:
        """
        检查答案质量 - 类型感知的差异化评估
        
        Returns:
            {
                "corrected_answer": str,
                "knowledge_type": str,        # 识别的类型
                "accuracy_score": float,      # 0-5
                "completeness_score": float,  # 0-5
                "educational_score": float,   # 0-5
                "additional_score": float,    # 0-5 (根据类型的额外维度)
                "overall_score": float,       # 0-5 (加权综合)
                "improvement_suggestions": str
            }
        """
        if not settings.ENABLE_CLOUD_QUALITY_CHECK or not self.api_key:
            return None
        
        # 1. 本地预分类（用于选择合适的评估标准）
        knowledge_type = self.classify_content_type(question, local_answer, expert_subject)
        
        if settings.SIMULATION_MODE:
            return self._simulate_check(question, local_answer, knowledge_type)
        
        # 2. 根据类型构建评估标准
        criteria = self.TYPE_CRITERIA.get(knowledge_type, self.TYPE_CRITERIA["qa"])
        weights = self.TYPE_WEIGHTS.get(knowledge_type, self.TYPE_WEIGHTS["qa"])
        
        # 确定额外评估维度名称
        additional_dim = {
            "formula": "规范性",
            "concept": "教育性",  # concept用educational作为主要维度之一
            "template": "实用性",
            "step": "逻辑性",
            "qa": "清晰度"
        }
        dim_name = additional_dim.get(knowledge_type, "规范性")
        
        system_prompt = f"""你是一位严格的教育内容质检专家，专注于{expert_subject}学科。

{criteria}

你的任务:
1. 首先判断内容类型（公式/概念/模板/步骤/问答）
2. 根据上述评估标准进行评分
3. 给出纠正后的标准答案
4. 按以下维度评分(每项0-5分，精确到小数点后1位):
   - accuracy_score: 准确性
   - completeness_score: 完整性  
   - educational_score: 教育性/易懂性
   - additional_score: {dim_name}

请严格按照以下JSON格式输出:
{{
    "knowledge_type": "识别的类型(formula/concept/template/step/qa)",
    "corrected_answer": "纠正后的完整答案",
    "accuracy_score": 4.5,
    "completeness_score": 4.0,
    "educational_score": 4.5,
    "additional_score": 4.2,
    "improvement_suggestions": "具体的改进建议"
}}"""
        
        user_prompt = f"""【问题】
{question}

【学生/系统提供的答案】
{local_answer}

请根据{knowledge_type}类型的评估标准进行评估，并给出纠正后的答案。"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions" if self.base_url else "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.2,  # 更低温度，更稳定评分
                        "max_tokens": 2048
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                return self._parse_quality_response(content, weights, knowledge_type)
                
        except Exception as e:
            print(f"云端质检失败: {e}")
            return None
    
    def _parse_quality_response(
        self, 
        content: str, 
        weights: Dict[str, float],
        default_type: str = "qa"
    ) -> Dict:
        """解析质检响应并计算加权综合分"""
        import json
        import re
        
        try:
            # 清理非法字符
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
            cleaned = re.sub(r'[\u200b-\u200f\ufeff]', '', cleaned)
            
            # 尝试提取JSON
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # 备用清理
                    json_str = json_match.group()
                    json_str = ''.join(char for char in json_str if ord(char) >= 32 or char in '\n\r\t')
                    data = json.loads(json_str)
                
                # 获取各维度分数
                accuracy = float(data.get("accuracy_score", 3))
                completeness = float(data.get("completeness_score", 3))
                educational = float(data.get("educational_score", 3))
                additional = float(data.get("additional_score", 3))
                
                # 根据类型计算加权综合分
                knowledge_type = data.get("knowledge_type", default_type).lower()
                type_weights = self.TYPE_WEIGHTS.get(knowledge_type, weights)
                
                # 映射额外维度到标准维度
                if knowledge_type == "formula":
                    overall = (
                        accuracy * type_weights["accuracy"] +
                        completeness * type_weights["completeness"] +
                        additional * type_weights["standardization"] +  # additional = 规范性
                        educational * type_weights["educational"]
                    )
                elif knowledge_type == "template":
                    overall = (
                        accuracy * type_weights["accuracy"] +
                        completeness * type_weights["completeness"] +
                        additional * type_weights["practicality"] +     # additional = 实用性
                        educational * 0  # 模板类教育性权重低
                    )
                elif knowledge_type == "step":
                    overall = (
                        accuracy * type_weights["accuracy"] +
                        completeness * type_weights["completeness"] +
                        additional * type_weights["logic"] +            # additional = 逻辑性
                        educational * 0
                    )
                else:  # concept, qa
                    overall = (
                        accuracy * type_weights.get("accuracy", 0.35) +
                        completeness * type_weights.get("completeness", 0.35) +
                        educational * type_weights.get("educational", 0.30)
                    )
                
                return {
                    "knowledge_type": knowledge_type,
                    "corrected_answer": data.get("corrected_answer", ""),
                    "accuracy_score": accuracy,
                    "completeness_score": completeness,
                    "educational_score": educational,
                    "additional_score": additional,
                    "overall_score": round(overall, 2),
                    "improvement_suggestions": data.get("improvement_suggestions", ""),
                    "weight_config": type_weights  # 返回使用的权重配置（用于调试）
                }
        except Exception as e:
            print(f"解析质检响应失败: {e}")
            print(f"原始内容前200字符: {content[:200]}")
        
        # 降级返回
        return {
            "knowledge_type": default_type,
            "corrected_answer": content,
            "accuracy_score": 3.0,
            "completeness_score": 3.0,
            "educational_score": 3.0,
            "additional_score": 3.0,
            "overall_score": 3.0,
            "improvement_suggestions": "解析失败",
            "weight_config": weights
        }
    
    def _simulate_check(self, question: str, local_answer: str, knowledge_type: str = "qa") -> Dict:
        """模拟质检 - 按类型生成不同分数分布"""
        import random
        
        weights = self.TYPE_WEIGHTS.get(knowledge_type, self.TYPE_WEIGHTS["qa"])
        
        # 根据类型特点模拟评分
        if knowledge_type == "formula":
            accuracy = round(random.uniform(3.5, 5.0), 1)
            completeness = round(random.uniform(3.0, 4.5), 1)
            educational = round(random.uniform(2.5, 4.0), 1)  # 公式类教育性偏低
            additional = round(random.uniform(3.5, 5.0), 1)   # 规范性
        elif knowledge_type == "concept":
            accuracy = round(random.uniform(3.5, 5.0), 1)
            completeness = round(random.uniform(3.0, 4.5), 1)
            educational = round(random.uniform(3.5, 5.0), 1)  # 概念类教育性重要
            additional = educational
        elif knowledge_type in ["template", "step"]:
            accuracy = round(random.uniform(3.5, 5.0), 1)
            completeness = round(random.uniform(3.5, 5.0), 1)  # 步骤/模板完整性重要
            educational = round(random.uniform(3.0, 4.5), 1)
            additional = round(random.uniform(3.5, 5.0), 1)   # 实用性/逻辑性
        else:  # qa
            accuracy = round(random.uniform(3.5, 5.0), 1)
            completeness = round(random.uniform(3.0, 4.5), 1)
            educational = round(random.uniform(3.5, 4.8), 1)
            additional = educational
        
        # 计算加权综合分
        if knowledge_type == "formula":
            overall = (
                accuracy * weights["accuracy"] +
                completeness * weights["completeness"] +
                additional * weights["standardization"] +
                educational * weights["educational"]
            )
        else:
            overall = (
                accuracy * weights.get("accuracy", 0.35) +
                completeness * weights.get("completeness", 0.35) +
                educational * weights.get("educational", 0.30)
            )
        
        return {
            "knowledge_type": knowledge_type,
            "corrected_answer": f"[{knowledge_type}类型纠正]{local_answer}\n\n(模拟云端纠正)",
            "accuracy_score": accuracy,
            "completeness_score": completeness,
            "educational_score": educational,
            "additional_score": additional,
            "overall_score": round(overall, 2),
            "improvement_suggestions": f"模拟建议：作为{knowledge_type}类型内容，建议关注{list(weights.keys())[0]}",
            "weight_config": weights
        }


quality_checker = QualityChecker()
