"""BGE 向量编码器 - 384维中文Embedding - 真实实现"""
from typing import List, Union
import numpy as np
from ...core.config import get_settings
from ...core.logging import LoggerMixin

settings = get_settings()


class BGEEncoder(LoggerMixin):
    """BGE-small-zh-v1.5 编码器 - 生成384维向量 - 真实实现"""
    
    DIMENSION = 384  # BGE-small-zh-v1.5 输出维度
    
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or settings.EMBEDDING_DEVICE
        self._model = None
        self._tokenizer = None
        self._model_loaded = False
        
    def _load_model(self):
        """懒加载模型 - 真实实现"""
        if self._model_loaded:
            return
            
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            self.logger.info(f"加载BGE模型: {self.model_name}")
            
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            self._model.to(self.device)
            self._model.eval()
            
            self._model_loaded = True
            self.logger.info(f"✅ BGE模型加载完成，设备: {self.device}")
            
        except ImportError as e:
            self.logger.error(f"❌ 缺少依赖: {e}")
            raise ImportError(
                "使用Embedding功能需要安装: pip install transformers torch"
            ) from e
        except Exception as e:
            self.logger.error(f"❌ 加载BGE模型失败: {e}")
            raise RuntimeError(
                f"无法加载Embedding模型 '{self.model_name}'，请检查模型是否存在"
            ) from e
    
    def encode(
        self, 
        texts: Union[str, List[str]], 
        normalize: bool = True
    ) -> np.ndarray:
        """
        将文本编码为向量 - 真实实现
        
        Args:
            texts: 单个文本或文本列表
            normalize: 是否归一化向量
            
        Returns:
            向量数组，形状: (batch_size, 384)
        """
        self._load_model()
        
        if isinstance(texts, str):
            texts = [texts]
        
        import torch
        
        # 添加指令前缀（BGE推荐）
        instruction = "Represent this sentence for searching relevant passages: "
        texts_with_instruction = [instruction + t for t in texts]
        
        # Tokenize
        encoded = self._tokenizer(
            texts_with_instruction,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        
        # 移动到设备
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        
        # 生成向量
        with torch.no_grad():
            model_output = self._model(**encoded)
            # 使用[CLS] token的表示
            embeddings = model_output.last_hidden_state[:, 0]
            
        # 转换为numpy
        embeddings = embeddings.cpu().numpy()
        
        # 归一化
        if normalize:
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        return embeddings
    
    def compute_similarity(
        self, 
        query_vec: np.ndarray, 
        doc_vecs: np.ndarray
    ) -> np.ndarray:
        """
        计算余弦相似度
        
        Args:
            query_vec: 查询向量 (384,) 或 (1, 384)
            doc_vecs: 文档向量 (n, 384)
            
        Returns:
            相似度数组 (n,)
        """
        if query_vec.ndim == 1:
            query_vec = query_vec.reshape(1, -1)
        
        # 余弦相似度 = 归一化向量的点积
        similarities = np.dot(query_vec, doc_vecs.T).flatten()
        return similarities


# 全局编码器实例
_encoder = None


def get_encoder() -> BGEEncoder:
    """获取全局编码器实例（单例）"""
    global _encoder
    if _encoder is None:
        _encoder = BGEEncoder()
    return _encoder


async def encode_text(text: Union[str, List[str]]) -> List[List[float]]:
    """
    异步编码文本
    
    注意：实际编码是CPU密集型操作，在线程池中执行避免阻塞事件循环
    """
    import asyncio
    
    encoder = get_encoder()
    loop = asyncio.get_event_loop()
    
    # 在线程池中执行编码
    vectors = await loop.run_in_executor(None, encoder.encode, text)
    return vectors.tolist()


async def compute_query_embedding(query: str) -> List[float]:
    """计算查询文本的向量"""
    vectors = await encode_text(query)
    return vectors[0]
