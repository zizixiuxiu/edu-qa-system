"""LLM 客户端 - 真实实现"""
from typing import List, Dict, Optional, Any
import aiohttp
from ...core.config import get_settings
from ...core.logging import LoggerMixin

settings = get_settings()


class LLMClient(LoggerMixin):
    """LLM客户端 - 调用本地或云端大模型"""
    
    def __init__(
        self, 
        base_url: str = None, 
        api_key: str = None,
        model: str = None,
        timeout: float = None
    ):
        self.base_url = base_url or settings.LLM_BASE_URL
        self.api_key = api_key or settings.LLM_API_KEY or "not-needed"
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT
        
    async def generate(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        生成文本 - 真实实现
        
        调用OpenAI格式的API（支持LM Studio、Ollama等）
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        聊天补全 - 真实实现
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大生成token数
            
        Returns:
            生成的文本
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key and self.api_key != "not-needed":
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"LLM API错误: {response.status} - {error_text}")
                    
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    self.logger.info(
                        f"LLM生成成功: model={self.model}, "
                        f"prompt_tokens={result.get('usage', {}).get('prompt_tokens', 0)}, "
                        f"completion_tokens={result.get('usage', {}).get('completion_tokens', 0)}"
                    )
                    
                    return content
                    
        except aiohttp.ClientError as e:
            self.logger.error(f"LLM连接错误: {e}")
            raise Exception(f"无法连接到LLM服务: {e}")
        except Exception as e:
            self.logger.error(f"LLM生成错误: {e}")
            raise
    
    async def generate_with_image(
        self, 
        prompt: str, 
        image_data: bytes,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        多模态生成 - 真实实现
        
        Args:
            prompt: 文本提示
            image_data: 图片二进制数据
            
        Returns:
            生成的文本
        """
        import base64
        
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }]
        
        return await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ):
        """
        流式生成 - 真实实现
        
        Yields:
            生成的文本片段
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key and self.api_key != "not-needed":
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"LLM API错误: {response.status} - {error_text}")
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]
                            if data == '[DONE]':
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                delta = chunk["choices"][0]["delta"]
                                if "content" in delta:
                                    yield delta["content"]
                            except:
                                pass
                                
        except Exception as e:
            self.logger.error(f"流式生成错误: {e}")
            raise


# 全局LLM客户端实例
_llm_client = None


def get_llm_client() -> LLMClient:
    """获取全局LLM客户端"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
