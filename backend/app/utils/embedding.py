"""Embedding工具 - 单例模式，模型只加载一次"""
from functools import lru_cache
from typing import List
from app.core.config import settings


class EmbeddingService:
    """Embedding服务 - 单例模式"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _load_model(self):
        """懒加载模型"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            import os
            import glob
            
            model_path = settings.EMBEDDING_MODEL
            
            # 检查是否是本地路径
            if os.path.exists(model_path):
                print(f"[EmbeddingService] 正在加载本地模型: {model_path}")
                
                # 如果是 HuggingFace cache 格式，找到实际的模型文件
                snapshots_dir = os.path.join(model_path, "snapshots")
                if os.path.exists(snapshots_dir):
                    # 找到最新的 snapshot
                    snapshots = glob.glob(os.path.join(snapshots_dir, "*"))
                    if snapshots:
                        model_path = snapshots[0]
                        print(f"[EmbeddingService] 使用 snapshot: {model_path}")
            else:
                print(f"[EmbeddingService] 正在加载HuggingFace模型: {model_path}")
            
            try:
                self._model = SentenceTransformer(model_path, device=settings.EMBEDDING_DEVICE)
                print(f"[EmbeddingService] 模型加载完成")
            except Exception as e:
                print(f"[EmbeddingService] 模型加载失败: {e}")
                # 如果失败，使用简单的哈希模拟embedding（降级方案）
                print(f"[EmbeddingService] 使用模拟embedding作为降级方案")
                self._model = None
        
        return self._model
    
    def encode(self, text: str, target_dim: int = 384) -> List[float]:
        """编码单个文本，强制转换为指定维度"""
        model = self._load_model()
        if model is None:
            # 降级方案：使用哈希生成伪向量
            return self._hash_embedding(text, dim=target_dim)
        
        vec = model.encode(text).tolist()
        result = self._ensure_dimension(vec, target_dim)
        
        # 调试日志（首次使用时打印）
        if not hasattr(self, '_dim_checked'):
            self._dim_checked = True
            print(f"[EmbeddingService] 输入维度: {len(vec)}, 输出维度: {len(result)}, 目标: {target_dim}")
        
        return result
    
    def encode_batch(self, texts: List[str], target_dim: int = 384) -> List[List[float]]:
        """批量编码文本，强制转换为指定维度"""
        model = self._load_model()
        if model is None:
            # 降级方案
            return [self._hash_embedding(t, dim=target_dim) for t in texts]
        
        vectors = model.encode(texts).tolist()
        return [self._ensure_dimension(v, target_dim) for v in vectors]
    
    def _ensure_dimension(self, vec: List[float], target_dim: int = 384) -> List[float]:
        """确保向量维度正确，通过截断或填充"""
        current_dim = len(vec)
        
        if current_dim == target_dim:
            return vec
        elif current_dim > target_dim:
            # 维度过多，截断
            return vec[:target_dim]
        else:
            # 维度不足，用零填充
            return vec + [0.0] * (target_dim - current_dim)
    
    def _hash_embedding(self, text: str, dim: int = 384) -> List[float]:
        """使用哈希生成伪embedding（降级方案）"""
        import hashlib
        import random
        # 使用文本哈希作为随机种子，确保相同文本产生相同向量
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        random.seed(seed)
        # 生成归一化的随机向量
        import math
        vec = [random.random() for _ in range(dim)]
        # 归一化
        norm = math.sqrt(sum(x*x for x in vec))
        return [x/norm for x in vec]


# 全局单例实例
embedding_service = EmbeddingService()

# 启动时预加载模型（避免首次请求时加载慢）
def preload_embedding_model():
    """预加载embedding模型"""
    print("[EmbeddingService] 启动预加载模型...")
    embedding_service._load_model()
    print("[EmbeddingService] 预加载完成")


def get_embedding(text: str) -> List[float]:
    """获取文本的embedding向量（便捷函数）"""
    return embedding_service.encode(text)


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """批量获取embedding向量（便捷函数）"""
    return embedding_service.encode_batch(texts)
