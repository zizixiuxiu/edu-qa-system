"""实验监控脚本 - 定期检查实验进度并记录"""
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import time
import sys

# 配置
CHECK_INTERVAL = 10 * 60  # 10分钟（秒）
MAX_DURATION = 10 * 60 * 60  # 10小时（秒）
BASE_URL = "http://localhost:8000"

class ExperimentMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.log_file = f"experiment_monitor_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
        self.check_count = 0
        
    def log(self, message):
        """记录日志到文件和控制台"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    
    async def get_experiment_status(self, session):
        """获取实验状态"""
        try:
            async with session.get(f"{BASE_URL}/api/v1/experiments/queue", timeout=10) as resp:
                if resp.status != 200:
                    return None, f"HTTP {resp.status}"
                queue_data = await resp.json()
            
            async with session.get(f"{BASE_URL}/api/v1/benchmark/progress", timeout=10) as resp:
                if resp.status != 200:
                    return None, f"HTTP {resp.status}"
                progress_data = await resp.json()
            
            running_exp = None
            completed_count = 0
            pending_count = 0
            
            for exp in queue_data.get('queue', []):
                if exp['status'] == 'running':
                    running_exp = exp
                elif exp['status'] == 'completed':
                    completed_count += 1
                elif exp['status'] == 'pending':
                    pending_count += 1
            
            return {
                'success': True,
                'running_exp': running_exp,
                'progress': progress_data,
                'completed': completed_count,
                'pending': pending_count,
                'total': queue_data.get('total', 0)
            }, None
            
        except Exception as e:
            return None, str(e)
    
    async def check_once(self, session):
        """执行一次检查"""
        self.check_count += 1
        elapsed = datetime.now() - self.start_time
        
        self.log(f"--- 检查 #{self.check_count} (运行时长: {elapsed}) ---")
        
        status, error = await self.get_experiment_status(session)
        
        if error:
            self.log(f"❌ 获取状态失败: {error}")
            return False
        
        if status['running_exp']:
            exp = status['running_exp']
            prog = status['progress']
            pct = round(prog.get('current', 0) / prog.get('total', 1) * 100, 1) if prog.get('total') else 0
            
            self.log(f"🔄 正在运行: {exp['name']}")
            self.log(f"   进度: {prog.get('current', 0)}/{prog.get('total', 0)} ({pct}%)")
            self.log(f"   当前题目: {prog.get('current_question', 'N/A')[:50]}...")
            self.log(f"   状态: {prog.get('status', 'unknown')}")
        else:
            self.log("⏸️  没有正在运行的实验")
        
        self.log(f"📊 队列统计: 完成={status['completed']}, 等待={status['pending']}, 总计={status['total']}")
        
        # 检查是否全部完成
        if status['completed'] == status['total'] and status['total'] > 0:
            self.log("")
            self.log("🎉 所有实验已完成！")
            self.log("=" * 60)
            return True
        
        return False
    
    async def run(self):
        """主监控循环"""
        self.log("=" * 60)
        self.log("🚀 实验监控任务启动")
        self.log("=" * 60)
        self.log(f"检查间隔: {CHECK_INTERVAL // 60} 分钟")
        self.log(f"最大监控时长: {MAX_DURATION // 3600} 小时")
        self.log(f"日志文件: {self.log_file}")
        self.log("")
        
        async with aiohttp.ClientSession() as session:
            while True:
                elapsed = (datetime.now() - self.start_time).total_seconds()
                
                # 检查是否超过最大监控时间
                if elapsed > MAX_DURATION:
                    self.log(f"⏰ 已达到最大监控时长 ({MAX_DURATION // 3600} 小时)，监控结束")
                    break
                
                # 执行检查
                all_completed = await self.check_once(session)
                if all_completed:
                    break
                
                self.log("")
                
                # 等待下一次检查
                await asyncio.sleep(CHECK_INTERVAL)
        
        total_time = datetime.now() - self.start_time
        self.log(f"监控任务结束")
        self.log(f"总运行时长: {total_time}")
        self.log(f"日志保存在: {self.log_file}")

if __name__ == "__main__":
    try:
        monitor = ExperimentMonitor()
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        print("\n监控被用户中断")
        sys.exit(0)
