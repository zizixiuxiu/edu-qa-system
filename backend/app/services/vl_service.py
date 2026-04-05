"""VL服务 - Qwen3-VL学科识别（仅识别学科）"""
import base64
import httpx
from typing import Optional, Dict
from app.core.config import settings


class VLService:
    """视觉语言模型服务 - 用于学科识别"""
    
    # 固定学科列表（不可扩展，大模型只能从这个列表中选择）
    SUPPORTED_SUBJECTS = [
        "数学", "物理", "化学",
        "语文", "英语",
        "生物", "历史", "地理", "政治",
        "通用"  # 用于跨学科或无法分类的问题
    ]
    
    def __init__(self):
        self.base_url = settings.LMSTUDIO_BASE_URL
        self.api_key = settings.LMSTUDIO_API_KEY
        self.model = settings.VL_MODEL_NAME
    
    async def identify_subject(
        self, 
        query: str, 
        image_base64: Optional[str] = None
    ) -> Dict[str, str]:
        """
        识别问题所属学科
        
        Returns:
            {
                "subject": "数学",
                "confidence": "high"
            }
        """
        if settings.SIMULATION_MODE:
            # 模拟模式 - 根据关键词简单判断
            return self._simulate_identify(query)
        
        # 构建prompt（严格限制只能从固定列表选择）
        supported_list = "、".join(self.SUPPORTED_SUBJECTS)
        system_prompt = f"""你是一个学科分类专家。请分析用户的问题，判断属于哪个学科领域。

**重要：必须从以下固定列表中选择，不能创建新的学科：**
{supported_list}

如果问题跨学科或无法确定，请选择"通用"。

请以JSON格式输出：
{{
    "subject": "学科名称",
    "confidence": "high/medium/low"
}}

只输出学科名称，不需要细分领域。"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 构建用户消息
        user_content = query
        if image_base64:
            user_content = [
                {"type": "text", "text": query},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        
        messages.append({"role": "user", "content": user_content})
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 100
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # 解析模型输出
                content = result["choices"][0]["message"]["content"]
                parsed = self._parse_subject_response(content)
                print(f"[VL识别成功] 模型: {self.model}, 结果: {parsed}")
                return parsed
                
        except httpx.ConnectError as e:
            print(f"[VL识别失败] 无法连接LMStudio ({self.base_url}): {e}")
            fallback_result = self._fallback_identify(query)
            print(f"[VL降级识别] '{query[:50]}...' -> {fallback_result['subject']}")
            return fallback_result
        except Exception as e:
            print(f"[VL识别失败] 其他错误: {e}")
            fallback_result = self._fallback_identify(query)
            print(f"[VL降级识别] '{query[:50]}...' -> {fallback_result['subject']}")
            return fallback_result
    
    def _parse_subject_response(self, content: str) -> Dict[str, str]:
        """解析模型输出的JSON"""
        import json
        import re
        
        try:
            # 尝试直接解析
            data = json.loads(content)
            subject = data.get("subject", "其他")
            
            # 验证学科是否在支持列表中
            if subject not in self.SUPPORTED_SUBJECTS:
                subject = self._match_subject(subject)
            
            return {
                "subject": subject,
                "confidence": data.get("confidence", "medium")
            }
        except:
            # 尝试从文本中提取
            subject_match = re.search(r'学科[:：]?\s*(\w+)', content)
            
            if subject_match:
                subject = subject_match.group(1)
                subject = self._match_subject(subject)
                return {"subject": subject, "confidence": "low"}
            
            return {"subject": "其他", "confidence": "low"}
    
    def _match_subject(self, subject: str) -> str:
        """
        匹配标准学科名称
        处理别名和近似名称
        """
        subject = subject.strip()
        
        # 直接匹配
        if subject in self.SUPPORTED_SUBJECTS:
            return subject
        
        # 别名映射
        aliases = {
            "math": "数学", "maths": "数学", "mathematics": "数学",
            "physics": "物理",
            "chemistry": "化学", "chem": "化学",
            "chinese": "语文",
            "english": "英语", "eng": "英语",
            "biology": "生物", "bio": "生物",
            "history": "历史", "hist": "历史",
            "geography": "地理", "geo": "地理",
            "politics": "政治", "political": "政治", "思政": "政治",
            "通用": "其他"
        }
        
        subject_lower = subject.lower()
        if subject_lower in aliases:
            return aliases[subject_lower]
        
        # 模糊匹配 - 找包含关系的
        for s in self.SUPPORTED_SUBJECTS:
            if s in subject or subject in s:
                return s
        
        return "其他"
    
    def _simulate_identify(self, query: str) -> Dict[str, str]:
        """模拟学科识别 - 增强版关键词匹配"""
        query_lower = query.lower()
        
        # 优先级排序的关键词（越具体的越优先）
        keywords = {
            "物理": ["牛顿", "定律", "力", "运动", "能量", "电磁", "光学", "热学", "速度", "加速度", 
                    "电路", "电压", "电流", "电阻", "磁场", "重力", "摩擦力", "惯性", "动量"],
            "数学": ["解方程", "求解", "函数", "方程", "几何", "三角形", "圆", "代数", "微积分", 
                    "概率", "积分", "导数", "数列", "矩阵", "向量", "极限", "微分"],
            "化学": ["化学", "元素", "化合物", "反应", "分子", "原子", "化学式", "酸碱", "氧化", 
                    "还原", "离子", "摩尔", "化合价", "催化剂"],
            "生物": ["光合", "细胞", "基因", "DNA", "进化", "生态", "蛋白质", "酶", "呼吸", 
                    "遗传", "染色体", "生物", "代谢", "激素"],
            "历史": ["朝代", "战争", "革命", "历史", "古代", "近代", "现代史", "明清", "唐宋", 
                    "皇帝", "条约", "起义", "战役"],
            "地理": ["气候", "地形", "地图", "经纬度", "板块", "河流", "山脉", "季风", "降水", 
                    "纬度", "经度", "海拔", "盆地", "高原"],
            "语文": ["诗词", "文言文", "作文", "阅读", "成语", "修辞", "小说", "散文", "古诗", 
                    "作者", "诗人", "文学作品"],
            "英语": ["grammar", "vocabulary", "reading", "translation", "tense", "单词", "语法", 
                    "英文", "english", "翻译", "完形填空"],
            "政治": ["经济", "政治", "哲学", "马克思", "社会主义", "市场", "唯物", "辩证", 
                    "法治", "民主", "阶级"]
        }
        
        # 统计每个学科的匹配词数量
        subject_scores = {}
        for subject, words in keywords.items():
            score = sum(2 if w in query_lower else 0 for w in words)
            # 额外加分：如果查询包含学科名本身
            if subject in query:
                score += 5
            if score > 0:
                subject_scores[subject] = score
        
        if subject_scores:
            # 按分数排序，取最高分的
            best_subject = max(subject_scores, key=subject_scores.get)
            return {"subject": best_subject, "confidence": "high"}
        
        return {"subject": "其他", "confidence": "medium"}
    
    def _fallback_identify(self, query: str) -> Dict[str, str]:
        """降级识别"""
        return self._simulate_identify(query)
    
    def get_supported_subjects(self) -> list:
        """获取支持的学科列表"""
        return self.SUPPORTED_SUBJECTS.copy()


vl_service = VLService()
