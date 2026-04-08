"""VLM 视觉语言模型服务 - 多模态学科分类"""
import base64
from typing import Dict, Optional, Tuple
import aiohttp
from ...core.config import get_settings
from ...core.logging import LoggerMixin

settings = get_settings()


class VLMService(LoggerMixin):
    """VLM服务 - 使用 Qwen3-VL-4B 进行多模态学科分类"""
    
    # 九大学科分类标签
    SUBJECTS = [
        "math", "physics", "chemistry", "biology",
        "chinese", "english", "history", "geography", "politics"
    ]
    
    # 学科中英文映射
    SUBJECT_MAP = {
        "math": "数学",
        "physics": "物理", 
        "chemistry": "化学",
        "biology": "生物",
        "chinese": "语文",
        "english": "英语",
        "history": "历史",
        "geography": "地理",
        "politics": "政治",
        "general": "通用"
    }
    
    # 反向映射
    SUBJECT_REVERSE_MAP = {v: k for k, v in SUBJECT_MAP.items()}
    
    # 学科关键词库（用于降级策略）
    KEYWORD_PATTERNS = {
        "math": [r"=", r"\+", r"\-", r"\*", r"\/", r"\^", r"√", r"π", r"∫", r"∑", r"lim", r"dx", r"dy", r"方程", r"函数"],
        "physics": [r"N", r"kg", r"m/s", r"J", r"W", r"A", r"V", r"Ω", r"Pa", r"Hz", r"F", r"T", r"力", r"速度", r"加速度"],
        "chemistry": [r"H2O", r"CO2", r"NaCl", r"mol", r"→", r"⇌", r"△", r"↑", r"↓", r"化学", r"反应", r"元素"],
        "biology": [r"细胞", r"DNA", r"RNA", r"蛋白质", r"基因", r"染色体", r"细胞核", r"线粒体", r"生物"],
        "chinese": [r"文言文", r"诗词", r"成语", r"阅读理解", r"作文", r"修辞", r"标点", r"语文", r"文学"],
        "english": [r"grammar", r"vocabulary", r"reading", r"writing", r"listening", r"speaking", r"英语", r"英文"],
        "history": [r"朝代", r"年号", r"历史", r"战役", r"条约", r"改革", r"革命", r"古代", r"近代"],
        "geography": [r"纬度", r"经度", r"气候", r"地形", r"河流", r"山脉", r"国家", r"首都", r"地理"],
        "politics": [r"政治", r"经济", r"哲学", r"马克思主义", r"社会主义", r"法律", r"道德", r"思想"],
    }
    
    def __init__(self):
        self.base_url = settings.VL_BASE_URL  # 本地LM Studio
        self.api_key = settings.LLM_API_KEY or "not-needed"
        self.model = settings.VL_MODEL  # qwen/qwen3-vl-4b
        self.timeout = settings.VL_TIMEOUT
        self.logger.info(f"VLM服务初始化: {self.model} @ {self.base_url}")
        
    def _encode_image(self, image_data: bytes) -> str:
        """将图片编码为base64"""
        return base64.b64encode(image_data).decode('utf-8')
    
    def _build_classification_prompt(self, text: Optional[str] = None) -> str:
        """构建学科分类提示词"""
        base_prompt = """你是一个学科分类专家。请分析图片中的题目，判断属于哪个学科。
可选学科：数学(math)、物理(physics)、化学(chemistry)、生物(biology)、
语文(chinese)、英语(english)、历史(history)、地理(geography)、政治(politics)

请只返回学科名称（英文小写），例如：math
如果无法确定，返回：general"""
        
        if text:
            base_prompt += f"\n\n用户问题：{text}"
        
        return base_prompt
    
    async def classify_image(
        self, 
        image_data: bytes, 
        text: Optional[str] = None,
        use_vlm: bool = True
    ) -> Tuple[str, float]:
        """
        对图片进行学科分类
        
        Args:
            image_data: 图片二进制数据
            text: 可选的文本描述
            use_vlm: 是否使用VLM，False则使用关键词降级
            
        Returns:
            (学科, 置信度)
        """
        # Level 1: VLM分类
        if use_vlm:
            try:
                subject, confidence = await self._vlm_classify(image_data, text)
                if confidence > 0.6:
                    return subject, confidence
                self.logger.warning(f"VLM置信度低({confidence:.2f})，降级到关键词匹配")
            except Exception as e:
                self.logger.error(f"VLM分类失败: {e}，降级到关键词匹配")
        
        # Level 2: 关键词匹配
        if text:
            subject, confidence = self._keyword_classify(text)
            if confidence > 0.5:
                return subject, confidence
        
        # Level 3: 通用专家兜底
        return "general", 0.3
    
    def to_chinese(self, subject_en: str) -> str:
        """将英文学科名转换为中文"""
        return self.SUBJECT_MAP.get(subject_en, "通用")
    
    def to_english(self, subject_zh: str) -> str:
        """将中文学科名转换为英文"""
        return self.SUBJECT_REVERSE_MAP.get(subject_zh, "general")
    
    async def _vlm_classify(
        self, 
        image_data: bytes, 
        text: Optional[str] = None
    ) -> Tuple[str, float]:
        """使用VLM进行端到端分类"""
        import json
        
        base64_image = self._encode_image(image_data)
        prompt = self._build_classification_prompt(text)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 50
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"VLM API错误: {response.status} - {error_text}")
                
                result = await response.json()
                content = result["choices"][0]["message"]["content"].strip().lower()
                
                # 解析响应
                for subject in self.SUBJECTS:
                    if subject in content:
                        # 简单置信度：如果直接匹配则0.9，否则0.7
                        return subject, 0.9 if content == subject else 0.7
                
                return "general", 0.5
    
    def _keyword_classify(self, text: str) -> Tuple[str, float]:
        """关键词匹配分类"""
        import re
        
        text_lower = text.lower()
        scores = {}
        
        for subject, patterns in self.KEYWORD_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            if score > 0:
                scores[subject] = score
        
        if not scores:
            return "general", 0.0
        
        # 归一化分数
        max_score = max(scores.values())
        best_subject = max(scores, key=scores.get)
        confidence = min(0.5 + (max_score / 10) * 0.3, 0.8)  # 0.5-0.8范围
        
        return best_subject, confidence
    
    async def extract_text_from_image(self, image_data: bytes) -> str:
        """从图片中提取文字 (OCR)"""
        base64_image = self._encode_image(image_data)
        
        prompt = """请识别图片中的文字内容，直接返回识别到的文本，不要添加任何解释。"""
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                result = await response.json()
                return result["choices"][0]["message"]["content"].strip()


# 全局VLM服务实例
vlm_service = VLMService()
