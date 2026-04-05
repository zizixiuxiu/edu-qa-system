"""
紧急停止脚本 - 强制终止所有基准测试相关的Python进程
"""
import psutil
import sys

def stop_benchmark():
    print("正在查找并停止基准测试进程...")
    
    stopped = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'connections']):
        try:
            # 查找监听8000端口的进程（FastAPI后端）
            if proc.info['name'] == 'python.exe':
                for conn in proc.info.get('connections', []):
                    if hasattr(conn, 'laddr') and conn.laddr.port == 8000:
                        print(f"找到后端服务进程 PID: {proc.info['pid']}")
                        proc.terminate()
                        stopped = True
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if stopped:
        print("✅ 已发送停止信号")
    else:
        print("⚠️ 未找到运行中的后端服务")
        print("\n请手动停止：")
        print("1. 按 Ctrl+Shift+Esc 打开任务管理器")
        print("2. 找到 'Python' 进程（内存使用较大的那个）")
        print("3. 右键点击 -> 结束任务")

if __name__ == "__main__":
    stop_benchmark()
