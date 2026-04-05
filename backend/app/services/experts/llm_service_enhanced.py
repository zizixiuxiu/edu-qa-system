"""
增强版LLM推理服务 - 本地模型 + 多级RAG
整合18万条数据集，学科库优先，通用库兜底
"""
import httpx
import time
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.database import Expert, Knowledge
from app.services.experts.expert_pool import expert_pool
from app.services.rag.multi_tier_retrieval import multi_tier_retriever
from app.utils.embedding import embedding_service


class EnhancedLLMService:
    """
    增强版LLM服务
    
    特性：
    1. 多级RAG检索（学科库 -> 通用库）
    2. 融合本地知识库 + 外部数据集
    3. 自动 fallback 机制
    """
    
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
        生成回答 - 增强版
        
        Returns:
            {
                "answer": str,
                "used_knowledges": List[Dict],
                "inference_time": float,
                "rag_time": float,
                "retrieval_details": Dict  # 检索详情
            }
        """
        start_time = time.time()
        
        # 1. 构建系统Prompt
        system_prompt = expert_pool.get_expert_prompt(expert)
        
        # 2. 多级RAG检索
        used_knowledges = []
        rag_time = 0
        retrieval_details = {
            "tier1_count": 0,
            "tier2_count": 0,
            "total_found": 0
        }
        
        if use_rag:
            rag_start = time.time()
            
            # 2.1 从外部数据集检索（18万条）
            external_results = multi_tier_retriever.retrieve(
                query=query,
                subject=expert.subject,
                top_k=settings.RAG_TOP_K,
                tier_weights=(1.0, 0.8),
                score_threshold=0.6
            )
            
            # 2.2 从本地知识库检索（迭代积累的数据）
            local_results = await self._retrieve_local_knowledge(
                session, expert.id, query, top_k=3
            )
            
            rag_time = time.time() - rag_start
            
            # 2.3 融合结果
            all_knowledges = self._merge_retrieval_results(
                external_results, local_results
            )
            
            # 2.4 构建上下文
            if all_knowledges:
                context = self._build_context(all_knowledges)
                system_prompt += f"\n\n参考以下知识点回答:\n{context}"
                
                used_knowledges = [
                    {
                        "id": k.id if hasattr(k, 'id') else k.get('id', ''),
                        "content": (k.question if hasattr(k, 'question') else k.get('question', k.content if hasattr(k, 'content') else k.get('content', '')))[:100] + "...",
                        "source": k.dataset if hasattr(k, 'dataset') else k.get('dataset', 'local'),
                        "tier": k.tier if hasattr(k, 'tier') else 1,
                        "score": round(k.score if hasattr(k, 'score') else 0.8, 3)
                    }
                    for k in all_knowledges[:settings.RAG_TOP_K]
                ]
                
                # 统计
                tier1_count = sum(1 for k in all_knowledges if hasattr(k, 'tier') and k.tier == 1)
                tier2_count = sum(1 for k in all_knowledges if hasattr(k, 'tier') and k.tier == 2)
                local_count = len(local_results)
                
                retrieval_details = {
                    "tier1_count": tier1_count,
                    "tier2_count": tier2_count,
                    "local_count": local_count,
                    "total_found": len(all_knowledges)
                }
        
        # 3. 调用模型
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
        
        # 生成
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
            "total_time": time.time() - start_time,
            "retrieval_details": retrieval_details
        }
    
    async def _retrieve_local_knowledge(
        self,
        session: AsyncSession,
        expert_id: int,
        query: str,
        top_k: int = 3
    ) -> List[Knowledge]:
        """检索本地知识库（迭代积累的数据）"""
        # 编码查询
        query_embedding = embedding_service.encode(query)
        
        # 相似度搜索
        statement = select(Knowledge).where(
            Knowledge.expert_id == expert_id
        ).order_by(
            Knowledge.embedding.cosine_distance(query_embedding)
        ).limit(top_k)
        
        result = await session.execute(statement)
        return result.scalars().all()
    
    def _merge_retrieval_results(
        self,
        external_results: List,
        local_results: List[Knowledge]
    ) -> List:
        """
        融合外部数据集和本地知识库的结果
        
        策略：
        1. 本地知识库结果优先（质量更高，已人工校验）
        2. 外部数据集补充
        3. 按分数排序
        """
        merged = []
        
        # 添加本地结果（赋予较高权重）
        for k in local_results:
            # 包装为类似RetrievalResult的对象
            k.score = 0.95  # 本地知识默认高分
            k.tier = 0  # 特殊标记为本地
            merged.append(k)
        
        # 添加外部结果（去重）
        local_questions = {k.content[:50] for k in local_results}
        for r in external_results:
            # 简单去重：问题前50字符不重复
            if r.question[:50] not in local_questions:
                merged.append(r)
        
        # 按分数排序
        merged.sort(key=lambda x: x.score if hasattr(x, 'score') else 0, reverse=True)
        
        return merged
    
    def _build_context(self, knowledges: List) -> str:
        """构建上下文 - 只包含问题，不含答案（保证基准测试有效性）"""
        contexts = []
        
        for i, k in enumerate(knowledges[:settings.RAG_TOP_K], 1):
            if hasattr(k, 'question'):  # 外部数据集
                # 只包含问题和选项，绝不包含答案！
                ctx = f"[{i}] {k.question}"
                if k.type == 'choice' and hasattr(k, 'metadata') and k.metadata.get('choices'):
                    choices = k.metadata['choices'][:4]
                    ctx += f"\n选项: {', '.join(str(c) for c in choices)}"
            else:  # 本地知识库 - content只包含问题
                ctx = f"[{i}] {k.content}"
            
            contexts.append(ctx)
        
        return "\n\n".join(contexts)
    
    async def _call_model(self, messages: List[Dict]) -> tuple:
        """调用本地模型"""
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
        """模拟生成"""
        subject = expert.subject
        
        # 统计来源
        local_count = sum(1 for k in knowledges if k.get('source') == 'local')
        external_count = len(knowledges) - local_count
        
        templates = {
            "数学": f"""【{expert.name}专家解答 - 增强版】

基于检索到的 {len(knowledges)} 个知识点（本地: {local_count}, 外部: {external_count}），我为你解答：

这是一个{subject}问题...

（实际部署后将连接真实模型生成详细解答）""",
            
            "default": f"""【{expert.name}专家解答 - 增强版】

检索结果统计:
- 本地知识库: {local_count} 条
- 外部数据集: {external_count} 条
- 总计引用: {len(knowledges)} 条知识点

（实际部署后将连接真实模型）"""
        }
        
        return templates.get(subject, templates["default"])


# 全局单例 - 替换原有 llm_service
enhanced_llm_service = EnhancedLLMService()
