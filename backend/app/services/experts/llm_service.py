"""LLM推理服务 - 本地模型 + 级联RAG检索"""
import httpx
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import Expert
from app.services.experts.expert_pool import expert_pool
from app.services.rag.retrieval_service import retrieval_service


class LLMService:
    """大语言模型推理服务 - 支持专家库+通用库级联检索"""
    
    def __init__(self):
        self.base_url = settings.LMSTUDIO_BASE_URL
        self.api_key = settings.LMSTUDIO_API_KEY
        self.model = settings.LOCAL_LLM_MODEL
    
    async def generate(
        self,
        session: AsyncSession,
        expert: Expert,
        query: str,
        image: Optional[str] = None,
        use_rag: bool = True
    ) -> Dict:
        """
        生成回答 - 支持级联RAG检索
        
        Returns:
            {
                "answer": str,
                "used_knowledges": List[Dict],
                "inference_time": float,
                "rag_time": float,
                "rag_stats": Dict  # 检索统计信息
            }
        """
        import time
        start_time = time.time()
        
        # 构建系统Prompt
        system_prompt = expert_pool.get_expert_prompt(expert)
        
        # RAG检索相关知识（级联检索：专家库 + 条件触发通用库）
        used_knowledges = []
        rag_time = 0
        rag_stats = {}
        
        if use_rag and settings.ENABLE_RAG:
            rag_start = time.time()
            
            # 使用知识类型感知的检索服务
            retrieval_results, rag_stats = await retrieval_service.retrieve(
                session=session,
                expert_id=expert.id,
                query=query,
                top_k=settings.RAG_TOP_K,
                max_general=2
            )
            
            rag_time = time.time() - rag_start
            
            if retrieval_results:
                # 按类型分组组织上下文，节省token
                type_groups = {}
                type_labels = {
                    "formula": "公式/定律",
                    "concept": "核心概念",
                    "template": "解题模板",
                    "step": "步骤/方法",
                    "qa": "典型问答"
                }
                
                for result in retrieval_results:
                    ktype = result.knowledge.knowledge_type
                    if ktype not in type_groups:
                        type_groups[ktype] = []
                    type_groups[ktype].append(result)
                
                # 构建结构化上下文
                context_parts = []
                for ktype in ["formula", "concept", "template", "step", "qa"]:
                    if ktype in type_groups:
                        type_name = type_labels.get(ktype, ktype)
                        group_contexts = []
                        for result in type_groups[ktype]:
                            # 优先使用meta_data中的答案（更完整）
                            if result.knowledge.meta_data and "answer" in result.knowledge.meta_data:
                                answer = result.knowledge.meta_data["answer"]
                                # 截取答案前部分保存精华（节省token）
                                answer_summary = answer[:200] + "..." if len(answer) > 200 else answer
                                group_contexts.append(answer_summary)
                            else:
                                group_contexts.append(result.knowledge.content)
                            
                            used_knowledges.append({
                                "id": result.knowledge.id,
                                "type": ktype,
                                "content": result.knowledge.content[:100] + "...",
                                "source": result.source,
                                "similarity": round(result.similarity, 3)
                            })
                        
                        # 合并同类型的内容
                        type_content = "\n".join([f"- {c}" for c in group_contexts])
                        context_parts.append(f"[{type_name}]\n{type_content}")
                
                context = "\n\n".join(context_parts)
                
                # 精简的上下文提示
                system_prompt += f"""\n\n【知识库参考】\n{context}\n\n基于上述知识回答。如缺少关键信息，请说明。"""
        
        # 构建消息
        messages = [{"role": "system", "content": system_prompt}]
        
        if image:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": query},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": query})
        
        # 调用模型
        if settings.SIMULATION_MODE:
            answer = self._simulate_generate(expert, query, used_knowledges)
            inference_time = 0.5
        else:
            answer, inference_time = await self._call_model(messages)
        
        return {
            "answer": answer,
            "used_knowledges": used_knowledges,
            "inference_time": inference_time,
            "rag_time": rag_time,
            "rag_stats": rag_stats
        }
    
    async def _call_model(self, messages: List[Dict]) -> tuple:
        """调用本地模型"""
        import time
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2048,
                        "stream": False
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                
                answer = result["choices"][0]["message"]["content"]
                inference_time = time.time() - start
                
                return answer, inference_time
                
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return f"抱歉，模型调用出现问题: {str(e)}", time.time() - start
    
    def _simulate_generate(
        self,
        expert: Expert,
        query: str,
        knowledges: List[Dict]
    ) -> str:
        """模拟生成回答 - 使用 Markdown 格式"""
        subject = expert.subject
        
        # 构建知识来源说明
        expert_knowledge_count = sum(1 for k in knowledges if k.get("source") == "expert")
        general_knowledge_count = sum(1 for k in knowledges if k.get("source") == "general")
        
        source_info = f"（参考{expert_knowledge_count}条专家知识"
        if general_knowledge_count > 0:
            source_info += f"，{general_knowledge_count}条通用知识"
        source_info += "）"
        
        # 根据问题类型生成不同的模拟回答
        if "牛顿" in query or "定律" in query:
            return f"""{expert.name}为你解答{source_info}：

## 核心概念

这是经典力学中的重要定律，描述了力、质量和加速度之间的关系。

## 数学表达式

**F = m·a**

其中：
- **F** 表示合外力（单位：牛顿 N）
- **m** 表示质量（单位：千克 kg）
- **a** 表示加速度（单位：米/秒² m/s²）

## 物理意义

物体的加速度与所受合外力成正比，与物体质量成反比。

---

*回答基于知识库检索生成*"""
        
        elif "方程" in query or "解" in query:
            return f"""{expert.name}为你解答{source_info}：

## 解题步骤

### 第一步：理解题意
分析问题中的已知条件和所求目标。

### 第二步：建立方程
根据题意列出数学关系式。

### 第三步：求解
运用适当的数学方法求解。

### 第四步：验证
检查结果是否符合实际意义。

---

*回答基于知识库检索生成*"""
        
        else:
            return f"""{expert.name}为你解答{source_info}：

## 问题分析

针对你的{subject}问题，我从以下几个方面进行解答：

### 1. 基本概念
这是{subject}领域的基础知识点。

### 2. 详细解释
- 要点一：核心概念说明
- 要点二：具体应用场景
- 要点三：注意事项

### 3. 总结
希望以上解答对你有帮助！如有疑问可以继续提问。

---

*回答基于知识库检索生成*"""


llm_service = LLMService()
