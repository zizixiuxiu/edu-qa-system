"""
训练任务执行器 - 模拟执行训练任务
"""
import asyncio
import random
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.database import TrainingJob, SFTData


class TrainingExecutor:
    """训练任务执行器"""
    
    def __init__(self):
        self.is_running = False
        self.current_job = None
        self._task = None
    
    async def start(self):
        """启动执行器"""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._worker())
        print("[TrainingExecutor] 训练执行器已启动")
    
    async def stop(self):
        """停止执行器"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[TrainingExecutor] 训练执行器已停止")
    
    async def _worker(self):
        """后台工作线程"""
        while self.is_running:
            try:
                await self._process_pending_jobs()
                await asyncio.sleep(5)  # 每5秒检查一次
            except Exception as e:
                print(f"[TrainingExecutor] 错误: {e}")
                await asyncio.sleep(10)
    
    async def _process_pending_jobs(self):
        """处理等待中的任务"""
        async with AsyncSessionLocal() as session:
            # 获取一个等待中的任务
            result = await session.execute(
                select(TrainingJob)
                .where(TrainingJob.status == "pending")
                .order_by(TrainingJob.created_at.asc())
                .limit(1)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return
            
            # 开始执行
            self.current_job = job
            job.status = "running"
            job.started_at = datetime.utcnow()
            await session.commit()
            
            print(f"[TrainingExecutor] 开始训练任务 #{job.id} (专家: {job.expert_id})")
            
            # 模拟训练过程
            try:
                await self._execute_training(session, job)
            except Exception as e:
                print(f"[TrainingExecutor] 任务 #{job.id} 失败: {e}")
                job.status = "failed"
                await session.commit()
            finally:
                self.current_job = None
    
    async def _execute_training(self, session: AsyncSession, job: TrainingJob):
        """执行训练"""
        loss_history = []
        
        # 获取SFT数据
        result = await session.execute(
            select(SFTData)
            .where(
                SFTData.expert_id == job.expert_id,
                SFTData.is_used_in_training == False
            )
            .limit(job.data_count)
        )
        sft_data_list = result.scalars().all()
        
        if not sft_data_list:
            raise Exception("没有可用的训练数据")
        
        # 模拟每个epoch的训练
        for epoch in range(job.epochs):
            if not self.is_running:
                break
            
            # 模拟训练时间 (1-3秒)
            await asyncio.sleep(random.uniform(1, 3))
            
            # 模拟损失值（从高到低递减）
            base_loss = 2.5
            decay = 0.3 * (epoch / job.epochs)
            noise = random.uniform(-0.1, 0.1)
            loss = max(0.1, base_loss - decay + noise)
            loss_history.append(round(loss, 4))
            
            # 更新进度
            job.loss_history = loss_history
            await session.commit()
            
            print(f"[TrainingExecutor] 任务 #{job.id} Epoch {epoch + 1}/{job.epochs}, Loss: {loss:.4f}")
        
        # 标记完成
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.output_path = f"/models/expert_{job.expert_id}_v{datetime.utcnow().timestamp()}.pt"
        
        # 标记SFT数据为已使用
        for sft_data in sft_data_list:
            sft_data.is_used_in_training = True
        
        await session.commit()
        print(f"[TrainingExecutor] 任务 #{job.id} 完成!")


# 全局执行器实例
training_executor = TrainingExecutor()
