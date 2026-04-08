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
        
        # 基础提示词
        base_rules = f"""1. 必须从以下列表中选择：{supported_list}
2. 数学问题包含：方程、解方程、求解、几何、代数、函数、计算、数字、公式、等式、未知数x/y/z、加减乘除等
3. 物理问题包含：力、运动、能量、电磁、光学、牛顿定律、速度、加速度等
4. 化学问题包含：元素、化合物、化学反应、分子式、化学方程式等
5. 生物问题包含：细胞、DNA、基因、生物、进化、生态系统等
6. 如果跨学科或无法确定，选"通用"""
        
        # 如果有图片，只看图片内容，完全忽略文字
        if image_base64:
            system_prompt = f"""你是一个学科分类专家。用户上传了一张图片，请**完全根据图片内容判断学科**，忽略所有文字描述。

**强制规则（按优先级）：**
1. **只看图片里的内容**：公式、图形、符号、图表
2. **完全忽略用户文字**：如"解答这题"、"怎么做"等文字与你无关
3. 必须从以下列表选择：{supported_list}

**图片内容判断指南：**
- 图片中有数字、等式、集合符号{{}}、√、∫、∑、π、几何图形 → **数学**
- 图片中有电路图、力学分析图、光学光路图 → **物理**
- 图片中有化学键、分子结构、实验装置 → **化学**
- 图片中有细胞图、生物结构、进化树 → **生物**
- 图片中有地图、地形图、气候图 → **地理**
- 图片中有历史地图、时间线、文物 → **历史**
- 图片中有文言文、诗词、作文 → **语文**

**重要：** 不要考虑用户写了什么文字，只看图片里画了什么！

**输出格式：**
{{
    "subject": "学科名称",
    "confidence": "high/medium/low",
    "reason": "简要说明图片中看到了什么"
}}"""
        else:
            system_prompt = f"""你是一个学科分类专家。请分析用户的问题，判断属于哪个学科领域。

**重要规则：**
{base_rules}

**示例：**
用户: "解方程: 2x + 5 = 13" -> 输出: {{"subject": "数学", "confidence": "high"}}
用户: "牛顿第二定律是什么" -> 输出: {{"subject": "物理", "confidence": "high"}}
用户: "水的化学式" -> 输出: {{"subject": "化学", "confidence": "high"}}

**请以JSON格式输出，不要包含其他内容：**
{{
    "subject": "学科名称",
    "confidence": "high/medium/low"
}}

学科名称必须是列表中的一项。"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # 构建用户消息（处理纯图片情况）
        user_text = query if query.strip() else "请判断图片内容所属学科"
        user_content = user_text
        has_image = image_base64 is not None and len(image_base64) > 100
        if has_image:
            # 检查 base64 是否已经是 data URL 格式
            if image_base64.startswith('data:'):
                image_url = image_base64  # 已经是完整 URL
            else:
                image_url = f"data:image/jpeg;base64,{image_base64}"  # 需要添加前缀
            
            user_content = [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
            print(f"[VL调试] 包含图片，URL长度: {len(image_url)}")
        else:
            print(f"[VL调试] 无图片，纯文本查询: {query[:50]}")
        
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
                print(f"[VL原始输出] {content[:200]}...")  # 调试日志
                parsed = self._parse_subject_response(content)
                
                # 后处理修正：如果VLM返回"通用"或"其他"，尝试用关键词匹配修正
                if parsed["subject"] in ["通用", "其他"]:
                    # 如果有图片但识别为通用，可能是模型不支持多模态
                    if has_image:
                        print(f"[VL警告] 有图片但VLM返回'{parsed['subject']}'，可能模型不支持图片分析")
                        # 尝试从文件名或文字中提取学科线索
                        text_corrected = self._simulate_identify(query)
                        if text_corrected["subject"] != "通用":
                            print(f"[VL降级修正] 从文字提取: '{text_corrected['subject']}'")
                            parsed = text_corrected
                        else:
                            # 文字也识别不出，默认数学（因为数学题最常带图）
                            print(f"[VL默认修正] 图片+通用 -> 数学（默认）")
                            parsed = {"subject": "数学", "confidence": "low"}
                    else:
                        # 无图片，正常关键词匹配
                        corrected = self._simulate_identify(query)
                        if corrected["subject"] != "通用":
                            print(f"[VL后处理修正] '{query[:50]}...' 从'{parsed['subject']}'修正为'{corrected['subject']}'")
                            parsed = corrected
                        else:
                            parsed["subject"] = "通用"
                
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
        """解析模型输出的JSON - 支持Markdown代码块"""
        import json
        import re
        
        # 先尝试提取JSON代码块
        json_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
        if json_block_match:
            content = json_block_match.group(1).strip()
        
        try:
            # 尝试直接解析
            data = json.loads(content)
            subject = data.get("subject", "通用")
            
            # 验证学科是否在支持列表中
            if subject not in self.SUPPORTED_SUBJECTS:
                subject = self._match_subject(subject)
            
            # 打印reason用于调试（如果有）
            if "reason" in data:
                print(f"[VL识别原因] {data['reason']}")
            
            return {
                "subject": subject,
                "confidence": data.get("confidence", "medium")
            }
        except:
            # 尝试从文本中提取 subject 字段
            # 支持多种格式: "subject": "数学" 或 subject: 数学
            patterns = [
                r'["\']?subject["\']?\s*[:：]\s*["\']?([^"\'\n,}]+)["\']?',
                r'学科\s*[:：]\s*["\']?([^"\'\n,}]+)["\']?'
            ]
            
            for pattern in patterns:
                subject_match = re.search(pattern, content, re.IGNORECASE)
                if subject_match:
                    subject = subject_match.group(1).strip()
                    subject = self._match_subject(subject)
                    return {"subject": subject, "confidence": "low"}
            
            # 尝试匹配任何支持的学科名称
            for s in self.SUPPORTED_SUBJECTS:
                if s in content:
                    return {"subject": s, "confidence": "low"}
            
            return {"subject": "通用", "confidence": "low"}
    
    def _match_subject(self, subject: str) -> str:
        """
        匹配标准学科名称
        处理别名和近似名称
        保证返回的学科一定在SUPPORTED_SUBJECTS中
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
            "politics": "政治", "political": "政治", "思政": "政治"
            # 注意：不要映射"通用"到"其他"，"通用"是合法的
        }
        
        subject_lower = subject.lower()
        if subject_lower in aliases:
            return aliases[subject_lower]
        
        # 模糊匹配 - 找包含关系的
        for s in self.SUPPORTED_SUBJECTS:
            if s in subject or subject in s:
                return s
        
        # 如果都不匹配，返回"通用"而不是"其他"（因为"其他"不在支持列表）
        return "通用"
    
    def _simulate_identify(self, query: str) -> Dict[str, str]:
        """模拟学科识别 - 增强版关键词匹配（降级策略）"""
        query_lower = query.lower()
        
        # 优先级排序的关键词（越具体的越优先）
        keywords = {
            "物理": ["牛顿", "定律", "力", "运动", "能量", "电磁", "光学", "热学", "速度", "加速度", 
                    "电路", "电压", "电流", "电阻", "磁场", "重力", "摩擦力", "惯性", "动量", "功", "功率"],
            "数学": ["解方程", "方程", "求解", "计算", "等于", "求", "函数", "几何", "三角形", "圆", "代数", "微积分", 
                    "概率", "积分", "导数", "数列", "矩阵", "向量", "极限", "微分", "加减乘除", "+", "-", "*", "/", "=", "x", "y", "z", 
                    "平方", "根号", "π", "pi", "角度", "弧度", "正弦", "余弦", "正切",
                    "集合", "交集", "并集", "补集", "子集", "属于", "包含", "空集", "全集", "元素", "{}", "∈", "∩", "∪"],
            "化学": ["化学", "元素", "化合物", "反应", "分子", "原子", "化学式", "酸碱", "氧化", 
                    "还原", "离子", "摩尔", "化合价", "催化剂", "沉淀", "溶液", "浓度"],
            "生物": ["光合", "细胞", "基因", "DNA", "进化", "生态", "蛋白质", "酶", "呼吸", 
                    "遗传", "染色体", "生物", "代谢", "激素", "组织", "器官"],
            "历史": ["朝代", "战争", "革命", "历史", "古代", "近代", "现代史", "明清", "唐宋", 
                    "皇帝", "条约", "起义", "战役", "年", "世纪", "公元前"],
            "地理": ["气候", "地形", "地图", "经纬度", "板块", "河流", "山脉", "季风", "降水", 
                    "纬度", "经度", "海拔", "盆地", "高原", "平原", "丘陵", "国家", "省份"],
            "语文": ["诗词", "文言文", "作文", "阅读", "成语", "修辞", "小说", "散文", "古诗", 
                    "作者", "诗人", "文学作品", "段意", "主旨", "赏析"],
            "英语": ["grammar", "vocabulary", "reading", "translation", "tense", "单词", "语法", 
                    "英文", "english", "翻译", "完形填空", "阅读理解", "作文"],
            "政治": ["经济", "政治", "哲学", "马克思", "社会主义", "市场", "唯物", "辩证", 
                    "法治", "民主", "阶级", "制度", "政策", "改革"]
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
