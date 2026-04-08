"""专家路由服务"""
from abc import ABC, abstractmethod
from typing import List, Optional

from ..models.expert import Expert, RoutingResult
from ...core.logging import LoggerMixin
from ...core.exceptions import RoutingFailedError


class VLClassifier(ABC):
    """VL分类器接口"""
    
    @abstractmethod
    async def classify(self, question: str, image_url: Optional[str] = None) -> tuple:
        """
        返回: (subject, confidence)
        """
        pass


class DefaultVLClassifier(VLClassifier, LoggerMixin):
    """默认VLM分类器实现 - 使用VLM服务"""
    
    def __init__(self):
        self.vlm_service = None
    
    async def classify(self, question: str, image_url: Optional[str] = None) -> tuple:
        """使用VLM服务进行学科分类"""
        # 延迟导入避免循环依赖
        if self.vlm_service is None:
            from ...infrastructure.llm.vlm_service import vlm_service
            self.vlm_service = vlm_service
        
        # 如果有图片，使用图片分类
        if image_url:
            # 从URL或base64加载图片数据
            image_data = await self._load_image(image_url)
            subject_en, confidence = await self.vlm_service.classify_image(
                image_data=image_data,
                text=question
            )
        else:
            # 纯文本使用关键词分类
            subject_en, confidence = self.vlm_service._keyword_classify(question)
        
        # 转换为中文学科名
        subject_zh = self.vlm_service.to_chinese(subject_en)
        return subject_zh, confidence
    
    async def _load_image(self, image_url: str) -> bytes:
        """从URL加载图片数据"""
        if image_url.startswith("data:image"):
            # Base64编码的图片
            import base64
            base64_data = image_url.split(",")[1]
            return base64.b64decode(base64_data)
        elif image_url.startswith("http"):
            # HTTP URL
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    return await response.read()
        else:
            # 本地文件路径
            with open(image_url, "rb") as f:
                return f.read()


class RoutingService(LoggerMixin):
    """专家路由服务"""
    
    # 默认学科列表
    DEFAULT_SUBJECTS = [
        "数学", "物理", "化学", "生物",
        "语文", "英语", "历史", "地理", "政治",
        "通用"
    ]
    
    def __init__(self, vl_classifier: VLClassifier):
        self.vl_classifier = vl_classifier
    
    async def route(
        self,
        question: str,
        image_url: Optional[str] = None,
        force_subject: Optional[str] = None
    ) -> RoutingResult:
        """
        路由问题到专家
        
        Args:
            question: 问题文本
            image_url: 图片URL（可选）
            force_subject: 强制指定学科（可选）
        
        Returns:
            RoutingResult: 路由结果
        
        Raises:
            RoutingFailedError: 路由失败
        """
        try:
            # 如果强制指定学科
            if force_subject:
                return RoutingResult(
                    expert_id=0,  # 由调用方根据subject查找
                    expert_subject=force_subject,
                    confidence=1.0,
                    method="manual"
                )
            
            # 使用VL模型识别学科
            subject, confidence = await self.vl_classifier.classify(question, image_url)
            
            self.logger.info(
                "Question routed",
                question_preview=question[:50],
                subject=subject,
                confidence=confidence,
                has_image=bool(image_url)
            )
            
            return RoutingResult(
                expert_id=0,  # 由调用方根据subject查找
                expert_subject=subject,
                confidence=confidence,
                method="vl"
            )
            
        except Exception as e:
            self.logger.error("Routing failed", error=str(e), question=question[:50])
            # 降级到通用专家
            return RoutingResult(
                expert_id=0,
                expert_subject="通用",
                confidence=0.5,
                method="fallback"
            )
    
    def get_prompt_template(self, expert_subject: str) -> str:
        """获取专家的prompt模板 - 覆盖全部9个学科+通用"""
        templates = {
            "数学": """你是一位资深数学专家。请用清晰的步骤解答问题，必要时使用LaTeX格式（$...$行内，$$...$$块级）表示公式。注意解题过程的逻辑严谨性。

问题：{question}

相关知识：
{context}

请给出详细解答：""",

            "物理": """你是一位资深物理专家。请结合物理原理和定律分析问题，使用恰当的公式和国际单位制。注意物理量的因果关系和受力分析。

问题：{question}

相关知识：
{context}

请给出详细解答：""",

            "化学": """你是一位资深化学专家。请分析化学原理，必要时写出配平的化学方程式。注意反应条件、物质状态标注和计量关系。

问题：{question}

相关知识：
{context}

请给出详细解答：""",

            "生物": """你是一位资深生物专家。请结合生物学原理解答问题，涉及细胞、遗传、生态等知识时注意概念的准确性和逻辑链条的完整性。

问题：{question}

相关知识：
{context}

请给出详细解答：""",

            "语文": """你是一位资深语文专家。请从文学鉴赏、语言运用、阅读理解等角度解答问题。涉及古文时注意字词释义和句式分析，涉及写作时注意结构和修辞。

问题：{question}

相关知识：
{context}

请给出详细解答：""",

            "英语": """你是一位资深英语专家。请从语法、词汇、语境等角度分析问题，给出准确解答。涉及翻译时注意信达雅，涉及写作时注意地道表达。

问题：{question}

相关知识：
{context}

请给出详细解答：""",

            "历史": """你是一位资深历史专家。请结合历史背景、时间线和因果关系分析问题。注意史实的准确性，区分史实与评价，善用史料论证。

问题：{question}

相关知识：
{context}

请给出详细解答：""",

            "地理": """你是一位资深地理专家。请结合自然地理和人文地理知识分析问题。注意区位因素分析、气候成因、地形地貌等要素的综合运用。

问题：{question}

相关知识：
{context}

请给出详细解答：""",

            "政治": """你是一位资深政治专家。请结合政治学、经济学、哲学原理分析问题。注意理论联系实际，观点明确，论证有力。

问题：{question}

相关知识：
{context}

请给出详细解答：""",

            "通用": """你是一个智能教育助手。请基于以下知识回答问题，给出准确、完整、有教育价值的解答。

问题：{question}

相关知识：
{context}

请给出详细解答："""
        }

        return templates.get(expert_subject, templates["通用"])
