"""基准测试报告持久化保存服务"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class BenchmarkReportSaver:
    """保存基准测试报告到本地文件系统"""
    
    def __init__(self, base_dir: str = None):
        """
        初始化报告保存器
        
        Args:
            base_dir: 报告保存根目录，默认为项目目录下的 benchmark_reports
        """
        if base_dir is None:
            # 默认保存到项目根目录的 benchmark_reports 文件夹
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "benchmark_reports"
            )
        
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        self.reports_dir = self.base_dir / "reports"
        self.comparisons_dir = self.base_dir / "comparisons"
        self.reports_dir.mkdir(exist_ok=True)
        self.comparisons_dir.mkdir(exist_ok=True)
    
    def save_report(
        self, 
        report_data: Dict[str, Any],
        experiment_config: Dict[str, Any] = None
    ) -> str:
        """
        保存测试报告
        
        Args:
            report_data: 测试报告数据
            experiment_config: 实验配置参数
            
        Returns:
            保存的文件路径
        """
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_id = report_data.get("experiment_info", {}).get("test_id", timestamp)
        
        # 构建完整报告
        full_report = {
            "metadata": {
                "version": "1.0",
                "saved_at": datetime.now().isoformat(),
                "file_format": "benchmark_report_v1"
            },
            "experiment_config": experiment_config or self._get_default_config(),
            "results": report_data
        }
        
        # 保存为JSON文件
        filename = f"benchmark_{test_id}.json"
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)
        
        print(f"[BenchmarkReportSaver] 报告已保存: {filepath}")
        return str(filepath)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认实验配置"""
        from app.core.config import settings
        
        return {
            "system_config": {
                "experiment_mode": settings.EXPERIMENT_MODE,
                "rag_enabled": settings.ENABLE_RAG,
                "expert_routing_enabled": settings.ENABLE_EXPERT_ROUTING,
                "self_iteration_enabled": settings.ENABLE_SELF_ITERATION,
                "rag_top_k": settings.RAG_TOP_K,
                "embedding_model": settings.EMBEDDING_MODEL,
                "quality_threshold": settings.QUALITY_THRESHOLD,
                "dedup_threshold": settings.DEDUP_THRESHOLD
            },
            "model_config": {
                "vl_model": settings.VL_MODEL_NAME,
                "local_llm": settings.LOCAL_LLM_MODEL,
                "lmstudio_url": settings.LMSTUDIO_BASE_URL
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def list_reports(self) -> list:
        """列出所有保存的报告"""
        reports = []
        for filepath in sorted(self.reports_dir.glob("benchmark_*.json"), reverse=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取关键信息
                meta = {
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "saved_at": data.get("metadata", {}).get("saved_at"),
                    "test_id": data.get("results", {}).get("experiment_info", {}).get("test_id"),
                    "experiment_mode": data.get("experiment_config", {}).get("system_config", {}).get("experiment_mode"),
                    "rag_enabled": data.get("experiment_config", {}).get("system_config", {}).get("rag_enabled"),
                    "total_questions": data.get("results", {}).get("summary", {}).get("total_questions"),
                    "accuracy_rate": data.get("results", {}).get("summary", {}).get("accuracy_rate"),
                    "avg_score": data.get("results", {}).get("summary", {}).get("avg_score")
                }
                reports.append(meta)
            except Exception as e:
                print(f"[BenchmarkReportSaver] 读取报告失败 {filepath}: {e}")
                continue
        
        return reports
    
    def load_report(self, filename: str) -> Optional[Dict]:
        """加载指定报告"""
        filepath = self.reports_dir / filename
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[BenchmarkReportSaver] 加载报告失败 {filepath}: {e}")
            return None
    
    def delete_report(self, filename: str) -> bool:
        """删除报告"""
        filepath = self.reports_dir / filename
        try:
            if filepath.exists():
                filepath.unlink()
                return True
        except Exception as e:
            print(f"[BenchmarkReportSaver] 删除报告失败 {filepath}: {e}")
        return False
    
    def export_comparison(
        self, 
        report_files: list, 
        output_name: str = None
    ) -> str:
        """
        导出多报告对比数据
        
        Args:
            report_files: 要对比的报告文件名列表
            output_name: 输出文件名（可选）
            
        Returns:
            对比报告文件路径
        """
        if output_name is None:
            output_name = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        comparison_data = {
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "report_count": len(report_files)
            },
            "reports": []
        }
        
        for filename in report_files:
            report = self.load_report(filename)
            if report:
                # 提取关键对比数据
                summary = {
                    "filename": filename,
                    "test_id": report.get("results", {}).get("experiment_info", {}).get("test_id"),
                    "experiment_mode": report.get("experiment_config", {}).get("system_config", {}).get("experiment_mode"),
                    "rag_enabled": report.get("experiment_config", {}).get("system_config", {}).get("rag_enabled"),
                    "summary": report.get("results", {}).get("summary"),
                    "by_subject": report.get("results", {}).get("by_subject")
                }
                comparison_data["reports"].append(summary)
        
        # 保存对比报告
        filepath = self.comparisons_dir / output_name
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, ensure_ascii=False, indent=2)
        
        print(f"[BenchmarkReportSaver] 对比报告已保存: {filepath}")
        return str(filepath)


# 全局单例
report_saver = BenchmarkReportSaver()
