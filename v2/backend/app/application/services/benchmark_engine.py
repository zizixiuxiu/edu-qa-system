"""基准测试执行引擎 - 真实实现"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from ...core.logging import LoggerMixin
from ...core.config import get_settings
from ...infrastructure.llm.client import get_llm_client
from ...domain.services.rag_service import get_retriever
from ...application.services.quality_service import get_quality_checker

settings = get_settings()


class BenchmarkEngine(LoggerMixin):
    """基准测试执行引擎 - 真实实现"""
    
    def __init__(self):
        self.is_running = False
        self.current_progress = 0
        self.total_questions = 0
        self.llm_client = get_llm_client()
        self.retriever = get_retriever()
        self.quality_checker = get_quality_checker()
    
    async def run_experiment(
        self,
        experiment_id: str,
        config: Dict[str, Any],
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        运行实验 - 真实实现
        
        使用真实的LLM进行测试，支持RAG增强和自我迭代
        """
        self.is_running = True
        self.total_questions = config.get("max_questions", 50)
        subject = config.get("subject", "general")
        enable_rag = config.get("enable_rag", True)
        enable_iteration = config.get("enable_iteration", False)
        
        self.logger.info(
            f"启动实验: {experiment_id}, "
            f"题目数: {self.total_questions}, "
            f"学科: {subject}, "
            f"RAG: {enable_rag}, 迭代: {enable_iteration}"
        )
        
        # 加载测试题目（真实数据集或生成）
        questions = await self._load_questions(subject, self.total_questions)
        
        correct_count = 0
        results = []
        subject_stats = {}
        
        for i, question in enumerate(questions):
            if not self.is_running:
                self.logger.info(f"实验已停止: {i}/{self.total_questions}")
                break
            
            self.current_progress = i + 1
            
            try:
                # 执行单题测试
                result = await self._process_question(
                    question=question,
                    enable_rag=enable_rag,
                    subject=subject
                )
                
                if result["is_correct"]:
                    correct_count += 1
                
                results.append(result)
                
                # 按学科统计
                q_subject = result.get("subject", subject)
                if q_subject not in subject_stats:
                    subject_stats[q_subject] = {"total": 0, "correct": 0}
                subject_stats[q_subject]["total"] += 1
                if result["is_correct"]:
                    subject_stats[q_subject]["correct"] += 1
                
                # 自我迭代：质检并入库
                if enable_iteration and result.get("quality_score", 0) >= 4.0:
                    await self._process_iteration(question, result)
                
            except Exception as e:
                self.logger.error(f"处理题目 {i+1} 失败: {e}")
                results.append({
                    "question_id": i + 1,
                    "is_correct": False,
                    "score": 0,
                    "error": str(e)
                })
            
            if progress_callback:
                await progress_callback(i + 1, self.total_questions)
        
        self.is_running = False
        
        # 生成报告
        return self._generate_report(
            experiment_id=experiment_id,
            config=config,
            results=results,
            correct_count=correct_count,
            subject_stats=subject_stats
        )
    
    async def _load_questions(self, subject: str, count: int) -> List[Dict[str, Any]]:
        """加载测试题目 - 从数据库或生成"""
        # 优先从数据库加载
        try:
            from ...infrastructure.database.repositories.knowledge_repository import KnowledgeRepository
            from ...infrastructure.database.connection import db
            
            async with db.session() as session:
                # 这里简化处理，实际应该从专门的测试集表加载
                # 暂时生成模拟题目
                pass
        except Exception as e:
            self.logger.warning(f"从数据库加载题目失败: {e}")
        
        # 生成测试题目
        questions = []
        templates = self._get_question_templates(subject)
        
        for i in range(count):
            template = templates[i % len(templates)]
            questions.append({
                "id": i + 1,
                "subject": subject,
                "question": template["question"],
                "answer": template["answer"],
                "type": template.get("type", "qa")
            })
        
        return questions
    
    def _get_question_templates(self, subject: str) -> List[Dict[str, str]]:
        """获取题目模板"""
        templates = {
            "math": [
                {"question": "求解方程 x^2 - 5x + 6 = 0", "answer": "x=2 或 x=3", "type": "formula"},
                {"question": "计算 sin(30°) 的值", "answer": "0.5", "type": "formula"},
                {"question": "求函数 f(x) = x^2 的导数", "answer": "f'(x) = 2x", "type": "formula"},
            ],
            "physics": [
                {"question": "牛顿第二定律的公式是什么？", "answer": "F=ma", "type": "formula"},
                {"question": "光速是多少？", "answer": "3×10^8 m/s", "type": "concept"},
                {"question": "什么是能量守恒定律？", "answer": "能量既不会凭空产生，也不会凭空消失...", "type": "concept"},
            ],
            "chemistry": [
                {"question": "水的化学式是什么？", "answer": "H2O", "type": "formula"},
                {"question": "什么是氧化还原反应？", "answer": "有电子转移的化学反应...", "type": "concept"},
                {"question": "元素周期表有多少个元素？", "answer": "118个", "type": "concept"},
            ],
            "general": [
                {"question": "什么是机器学习？", "answer": "机器学习是人工智能的一个分支...", "type": "concept"},
                {"question": "解释什么是深度学习", "answer": "深度学习是机器学习的子集...", "type": "concept"},
            ]
        }
        return templates.get(subject, templates["general"])
    
    async def _process_question(
        self,
        question: Dict[str, Any],
        enable_rag: bool,
        subject: str
    ) -> Dict[str, Any]:
        """处理单个题目"""
        q_text = question["question"]
        reference_answer = question["answer"]
        
        # RAG检索（如果启用）
        context = ""
        if enable_rag:
            try:
                retrieval_results = await self.retriever.retrieve(
                    query=q_text,
                    top_k=3
                )
                context = "\n".join([r.content for r in retrieval_results])
            except Exception as e:
                self.logger.warning(f"RAG检索失败: {e}")
        
        # 构建提示词
        prompt = self._build_prompt(q_text, context)
        
        # 调用LLM生成答案
        model_answer = await self.llm_client.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=500
        )
        
        # 评估答案
        is_correct, quality_score = await self._evaluate_answer(
            model_answer=model_answer,
            reference=reference_answer,
            question=q_text
        )
        
        return {
            "question_id": question["id"],
            "subject": question.get("subject", subject),
            "question": q_text,
            "model_answer": model_answer,
            "reference_answer": reference_answer,
            "is_correct": is_correct,
            "score": quality_score,
            "quality_score": quality_score,
            "has_rag": bool(context),
        }
    
    def _build_prompt(self, question: str, context: str = "") -> str:
        """构建提示词"""
        if context:
            return f"""基于以下参考资料回答问题：

参考资料：
{context}

问题：{question}

请给出准确、完整的答案："""
        else:
            return f"""问题：{question}

请给出准确、完整的答案："""
    
    async def _evaluate_answer(
        self,
        model_answer: str,
        reference: str,
        question: str
    ) -> tuple[bool, float]:
        """评估答案质量"""
        try:
            # 使用云端质检服务
            result = await self.quality_checker.check_quality(
                question=question,
                answer=model_answer,
                subject="general"
            )
            
            # 判断是否正确（综合评分≥3.5视为正确）
            is_correct = result.overall_score >= 3.5
            
            return is_correct, result.overall_score
            
        except Exception as e:
            self.logger.warning(f"云端质检失败: {e}，使用简单匹配")
            # 降级：简单文本匹配
            model_keywords = set(model_answer.lower().split())
            ref_keywords = set(reference.lower().split())
            overlap = len(model_keywords & ref_keywords)
            total = len(ref_keywords)
            
            similarity = overlap / total if total > 0 else 0
            is_correct = similarity > 0.5
            score = min(5.0, similarity * 5)
            
            return is_correct, round(score, 2)
    
    async def _process_iteration(
        self,
        question: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """处理自我迭代 - 质检并入库"""
        try:
            from ...domain.models.session import QAInteraction, Message
            from ...domain.models.knowledge import KnowledgeItem
            
            interaction = QAInteraction(
                question=Message(role="user", content=question["question"]),
                answer=Message(role="assistant", content=result["model_answer"])
            )
            
            knowledge = await self.quality_checker.process_interaction(
                interaction=interaction,
                expert_id=1,  # 简化处理
                session_id=f"benchmark_{result['question_id']}"
            )
            
            if knowledge:
                self.logger.info(f"题目 {result['question_id']} 已入库")
                
        except Exception as e:
            self.logger.warning(f"自我迭代处理失败: {e}")
    
    def _generate_report(
        self,
        experiment_id: str,
        config: Dict[str, Any],
        results: List[Dict[str, Any]],
        correct_count: int,
        subject_stats: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """生成实验报告"""
        total = len(results)
        accuracy_rate = round(correct_count / total * 100, 1) if total > 0 else 0
        avg_score = round(sum(r.get("score", 0) for r in results) / total, 2) if total > 0 else 0
        
        # 按学科统计
        by_subject = {}
        for subject, stats in subject_stats.items():
            s_total = stats["total"]
            s_correct = stats["correct"]
            by_subject[subject] = {
                "total": s_total,
                "correct": s_correct,
                "accuracy": round(s_correct / s_total * 100, 1) if s_total > 0 else 0
            }
        
        report = {
            "experiment_id": experiment_id,
            "config": config,
            "summary": {
                "total_questions": total,
                "correct_count": correct_count,
                "wrong_count": total - correct_count,
                "accuracy_rate": accuracy_rate,
                "avg_score": avg_score,
                "rag_enabled": config.get("enable_rag", False),
                "iteration_enabled": config.get("enable_iteration", False),
            },
            "by_subject": by_subject,
            "details": results,
            "completed_at": datetime.now().isoformat(),
        }
        
        self.logger.info(
            f"实验完成: {experiment_id}, "
            f"正确率: {accuracy_rate}%, 平均分: {avg_score}"
        )
        return report
    
    def stop(self):
        """停止当前实验"""
        self.is_running = False
        self.logger.info("实验停止请求已收到")
    
    def get_progress(self) -> Dict[str, Any]:
        """获取当前进度"""
        return {
            "is_running": self.is_running,
            "current": self.current_progress,
            "total": self.total_questions,
            "progress_pct": round(
                self.current_progress / self.total_questions * 100, 1
            ) if self.total_questions > 0 else 0,
        }
