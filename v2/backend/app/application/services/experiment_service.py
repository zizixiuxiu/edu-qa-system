"""实验应用服务"""
import asyncio
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from uuid import uuid4

from ...core.config import get_settings
from ...core.logging import LoggerMixin
from ...core.exceptions import ValidationError
from ..dto.experiment_dto import (
    ExperimentConfigDTO,
    ExperimentQueueItemDTO,
    BenchmarkProgressDTO,
)

settings = get_settings()


class ExperimentQueueItem:
    """实验队列项（内存存储）"""
    def __init__(self, exp_id: str, config: ExperimentConfigDTO):
        self.id = exp_id
        self.config = config
        self.status = "pending"
        self.progress = 0
        self.current_question = 0
        self.total_questions = config.max_questions or 50
        self.created_at = datetime.now().isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.result: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.config.name,
            "status": self.status,
            "config": self.config.model_dump(),
            "progress": self.progress,
            "current_question": self.current_question,
            "total_questions": self.total_questions,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class ExperimentApplicationService(LoggerMixin):
    """实验应用服务"""
    
    def __init__(self):
        self.queue: List[ExperimentQueueItem] = []
        self.current_experiment_id: Optional[str] = None
        self._lock = asyncio.Lock()
        self._running_tasks: set = set()  # 保存后台任务引用，防止GC
    
    async def create_experiments(
        self,
        configs: List[ExperimentConfigDTO]
    ) -> List[str]:
        """创建实验"""
        experiment_ids = []
        
        for config in configs:
            exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
            item = ExperimentQueueItem(exp_id, config)
            self.queue.append(item)
            experiment_ids.append(exp_id)
        
        self.logger.info(f"Created {len(experiment_ids)} experiments")
        return experiment_ids
    
    async def get_queue(self) -> Dict[str, Any]:
        """获取实验队列"""
        async with self._lock:
            pending = sum(1 for e in self.queue if e.status == "pending")
            running = sum(1 for e in self.queue if e.status == "running")
            completed = sum(1 for e in self.queue if e.status == "completed")
            
            return {
                "current_id": self.current_experiment_id,
                "queue": [e.to_dict() for e in self.queue],
                "total": len(self.queue),
                "pending": pending,
                "running": running,
                "completed": completed,
            }
    
    async def start_next(self) -> Optional[ExperimentQueueItem]:
        """启动下一个实验"""
        async with self._lock:
            # 检查是否有正在运行的实验
            if self.current_experiment_id:
                return None
            
            # 找到下一个pending的实验
            for item in self.queue:
                if item.status == "pending":
                    item.status = "running"
                    item.started_at = datetime.now().isoformat()
                    self.current_experiment_id = item.id
                    
                    self.logger.info(f"Started experiment: {item.config.name}")
                    return item
            
            return None
    
    async def complete_experiment(
        self,
        exp_id: str,
        result: Dict[str, Any]
    ) -> None:
        """完成实验"""
        async with self._lock:
            for item in self.queue:
                if item.id == exp_id:
                    item.status = "completed"
                    item.completed_at = datetime.now().isoformat()
                    item.progress = 100
                    item.result = result
                    
                    # 保存结果到文件
                    await self._save_result(item, result)
                    
                    if self.current_experiment_id == exp_id:
                        self.current_experiment_id = None
                    
                    self.logger.info(f"Completed experiment: {item.config.name}")
                    break
    
    async def _save_result(
        self,
        item: ExperimentQueueItem,
        result: Dict[str, Any]
    ) -> None:
        """保存实验结果"""
        exp_dir = os.path.join(settings.DATA_DIR, "experiments", item.id)
        os.makedirs(exp_dir, exist_ok=True)
        
        data = {
            "experiment_info": {
                "id": item.id,
                "name": item.config.name,
                "created_at": item.created_at,
                "started_at": item.started_at,
                "completed_at": item.completed_at,
            },
            "config": item.config.model_dump(),
            "results": result
        }
        
        filepath = os.path.join(exp_dir, "experiment_data.json")
        # 使用异步文件操作避免阻塞事件循环
        try:
            import aiofiles
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except ImportError:
            # 降级到同步操作（仅在开发环境）
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def _execute_single_experiment(self, exp_id: str, config: ExperimentConfigDTO) -> None:
        """执行单个实验（内部方法）"""
        async def progress_callback(current: int, total: int):
            """进度回调"""
            async with self._lock:
                for item in self.queue:
                    if item.id == exp_id:
                        item.current_question = current
                        item.progress = int(current / total * 100)
                        break
        
        try:
            # 创建独立的引擎实例（避免单例状态污染）
            from .benchmark_engine import BenchmarkEngine
            engine = BenchmarkEngine()
            
            # 使用引擎执行实验
            result = await engine.run_experiment(
                experiment_id=exp_id,
                config=config.model_dump(),
                progress_callback=progress_callback
            )
            
            # 完成实验
            await self.complete_experiment(exp_id, result)
            
        except Exception as e:
            self.logger.error(f"Experiment execution failed: {e}")
            # 标记为错误状态
            async with self._lock:
                for item in self.queue:
                    if item.id == exp_id:
                        item.status = "error"
                        break
                self.current_experiment_id = None
    
    async def execute_current_experiment(self) -> None:
        """执行当前实验（后台任务）- 使用循环而非递归"""
        while True:
            config = self.get_current_config()
            exp_id = self.current_experiment_id
            
            if not config or not exp_id:
                self.logger.info("No more experiments to execute")
                break
            
            # 执行当前实验
            await self._execute_single_experiment(exp_id, config)
            
            # 尝试启动下一个
            next_exp = await self.start_next()
            if not next_exp:
                self.logger.info("All experiments completed")
                break
            # 继续循环执行下一个，避免递归
    
    async def clear_queue(self) -> None:
        """清空队列"""
        self.queue.clear()
        self.current_experiment_id = None
        self.logger.info("Queue cleared")
    
    def get_current_config(self) -> Optional[ExperimentConfigDTO]:
        """获取当前实验配置"""
        if not self.current_experiment_id:
            return None
        
        for item in self.queue:
            if item.id == self.current_experiment_id:
                return item.config
        
        return None
