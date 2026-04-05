"""
错题知识生成器 - 将错题转化为知识库条目

核心流程：
1. 接收错题（题目 + 正确答案 + 解析）
2. 调用云端AI生成结构化知识
3. 存储到知识库（带embedding）
"""
import httpx
import json
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import Knowledge, SFTData
from app.services.iteration.deduplication import deduplication_service
from app.utils.embedding import embedding_service


class KnowledgeGenerator:
    """错题知识生成器"""
    
    async def process_wrong_answer(
        self,
        session: AsyncSession,
        expert_id: int,
        question: str,
        model_answer: str,
        correct_answer: str,
        analysis: str,
        subject: str
    ) -> Dict[str, any]:
        """
        处理错题 - 生成知识库条目
        
        Returns:
            {"knowledge_ids": List[int], "sft_data_id": Optional[int]}
        """
        result = {"knowledge_ids": [], "sft_data_id": None}
        
        # 1. 生成知识点（检索用）
        knowledge_content = await self._generate_knowledge_content(
            question, correct_answer, analysis, subject
        )
        
        # 2. 检查知识库去重
        duplicate = await deduplication_service.check_knowledge_duplicate(
            session, expert_id, knowledge_content
        )
        
        if duplicate is None:  # 不重复才添加
            # 生成embedding
            embedding = embedding_service.encode(knowledge_content)
            
            # 构建meta_data包含完整信息
            meta_data = {
                "question": question,
                "correct_answer": correct_answer,
                "analysis": analysis,
                "model_wrong_answer": model_answer,
                "knowledge_type": "wrong_answer_lesson",
                "full_content": f"问题：{question}\n正确答案：{correct_answer}\n解析：{analysis}"
            }
            
            knowledge = Knowledge(
                expert_id=expert_id,
                content=knowledge_content,
                embedding=embedding,
                meta_data=meta_data,
                source_type="wrong_answer_extracted",
                quality_score=5.0  # 错题知识点质量分设为最高
            )
            session.add(knowledge)
            await session.flush()  # 获取ID
            result["knowledge_ids"].append(knowledge.id)
            
            print(f"[KnowledgeGenerator] 添加知识点: {knowledge_content[:50]}...")
        
        # 3. 同时生成SFT数据（用于后续可能的微调）
        sft_duplicate = await deduplication_service.check_sft_data_duplicate(
            session, expert_id, question, ""
        )
        
        if not sft_duplicate:
            # 生成优质输出（正确答案 + 详细解析）
            output = await self._generate_sft_output(
                question, correct_answer, analysis, subject
            )
            
            sft_data = SFTData(
                expert_id=expert_id,
                instruction=question,
                input="",
                output=output,
                quality_score=5.0,
                is_used_in_training=False,
                source_type="wrong_answer_correction"
            )
            session.add(sft_data)
            await session.flush()
            result["sft_data_id"] = sft_data.id
        
        await session.commit()
        return result
    
    async def _generate_knowledge_content(
        self,
        question: str,
        correct_answer: str,
        analysis: str,
        subject: str
    ) -> str:
        """
        生成知识点内容（用于向量检索）
        
        目标：生成简洁、包含关键词的知识点，确保RAG能召回
        """
        prompt = f"""你是一个{subject}教育专家。请根据以下错题生成一个简洁的知识点条目，用于知识库检索。

【错题信息】
题目：{question}
正确答案：{correct_answer}
解析：{analysis}

【生成要求】
1. 格式：一句话概括核心考点 + 关键概念/公式
2. 必须包含题目中的关键词，确保向量检索时能匹配到
3. 简洁明了（50字以内），便于语义匹配
4. 突出易错点和解题关键

【示例格式】
- 语文：文言文断句规则：虚词"之"在句中停顿的用法及常见句式结构分析
- 数学：三角函数图像变换：y=sin(x)平移、伸缩变换规律及相位计算方法
- 物理：牛顿第二定律应用：斜面上物体受力分析步骤与摩擦力计算要点

请直接输出知识点条目（不要编号，不要解释）："""

        try:
            # 调用云端API（使用LMStudio或配置的云端API）
            base_url = settings.CLOUD_BASE_URL or settings.LMSTUDIO_BASE_URL
            api_key = settings.CLOUD_API_KEY or settings.LMSTUDIO_API_KEY
            model = settings.CLOUD_MODEL or settings.LOCAL_LLM_MODEL
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "你是一个教育知识生成专家，擅长提炼知识点。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 200
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                # 清理输出
                content = content.replace("- ", "").replace("【", "").replace("】", "").strip()
                
                if len(content) > 100:
                    content = content[:100]
                
                return content
                
        except Exception as e:
            print(f"[KnowledgeGenerator] 生成知识点失败: {e}")
            # 失败时返回简化版本
            return f"{subject}错题知识点：{question[:30]}... - 正确答案：{correct_answer}"
    
    async def _generate_sft_output(
        self,
        question: str,
        correct_answer: str,
        analysis: str,
        subject: str
    ) -> str:
        """生成SFT训练用的优质输出"""
        
        prompt = f"""你是一个{subject}教育专家。请针对以下题目，生成一个完整、清晰、教育性强的标准答案。

【题目】
{question}

【参考答案】
{correct_answer}

【解析】
{analysis}

【生成要求】
1. 先给出明确答案
2. 然后提供详细解析（包含关键概念解释）
3. 指出常见错误和易错点
4. 给出解题思路总结
5. 语言简洁专业，适合作为标准答案参考

请生成完整的标准答案："""

        try:
            base_url = settings.CLOUD_BASE_URL or settings.LMSTUDIO_BASE_URL
            api_key = settings.CLOUD_API_KEY or settings.LMSTUDIO_API_KEY
            model = settings.CLOUD_MODEL or settings.LOCAL_LLM_MODEL
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "你是一个教育专家，擅长编写清晰、完整的标准答案。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.5,
                        "max_tokens": 1000
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                output = result["choices"][0]["message"]["content"].strip()
                return output
                
        except Exception as e:
            print(f"[KnowledgeGenerator] 生成SFT输出失败: {e}")
            # 失败时使用基础格式
            return f"【答案】{correct_answer}\n\n【解析】{analysis}\n\n【易错提示】本题容易出错，请注意理解题目要求。"


# 全局实例
knowledge_generator = KnowledgeGenerator()
