# 🔄 EduQA 开发流程文档

> 规范化的开发流程，确保代码质量、团队协作和项目可持续性

---

## 📋 目录

1. [开发工作流](#开发工作流)
2. [分支策略](#分支策略)
3. [代码规范](#代码规范)
4. [提交流程](#提交流程)
5. [代码审查](#代码审查)
6. [测试策略](#测试策略)
7. [发布流程](#发布流程)
8. [文档维护](#文档维护)

---

## 🌊 开发工作流

### Git Flow 工作流

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  main   │────→│  develop│←────│ feature │     │  hotfix │
│(生产)   │     │(开发)   │     │ 分支    │     │ 分支    │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
       ↑                              │                │
       └──────────────────────────────┘────────────────┘
                    合并路径
```

### 分支定义

| 分支 | 用途 | 命名规范 | 生命周期 |
|------|------|----------|----------|
| `main` | 生产环境代码 | `main` | 永久 |
| `develop` | 开发集成 | `develop` | 永久 |
| `feature/*` | 功能开发 | `feature/功能名称` | 临时 |
| `bugfix/*` | 问题修复 | `bugfix/问题编号-简述` | 临时 |
| `hotfix/*` | 紧急修复 | `hotfix/问题编号-简述` | 临时 |
| `release/*` | 版本发布 | `release/v版本号` | 临时 |

---

## 🌿 分支策略

### 1. 功能开发流程

```bash
# 1. 从 develop 创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/subject-classifier

# 2. 开发过程中频繁提交
git add .
git commit -m "feat(classifier): 添加数学学科识别逻辑"

# 3. 推送到远程
git push origin feature/subject-classifier

# 4. 创建 Pull Request → Code Review → 合并到 develop

# 5. 删除本地和远程功能分支
git branch -d feature/subject-classifier
git push origin --delete feature/subject-classifier
```

### 2. 紧急修复流程

```bash
# 1. 从 main 创建 hotfix 分支
git checkout main
git checkout -b hotfix/123-fix-memory-leak

# 2. 修复问题
# ... coding ...

# 3. 提交并推送
git commit -m "fix(memory): 修复向量缓存内存泄漏 #123"
git push origin hotfix/123-fix-memory-leak

# 4. 创建 PR 合并到 main 和 develop
```

### 3. 版本发布流程

```bash
# 1. 从 develop 创建 release 分支
git checkout develop
git checkout -b release/v1.2.0

# 2. 版本号更新、更新日志编写
# ... bump version ...

# 3. 合并到 main 和 develop
git checkout main
git merge release/v1.2.0
git tag v1.2.0
git push origin main --tags

git checkout develop
git merge release/v1.2.0
```

---

## 📝 代码规范

### 提交信息规范 (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### 类型 (Type)

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(rag): 添加多级检索策略` |
| `fix` | Bug修复 | `fix(api): 修复会话ID重复问题` |
| `docs` | 文档更新 | `docs(readme): 更新部署指南` |
| `style` | 代码格式 | `style: 格式化代码` |
| `refactor` | 重构 | `refactor(expert): 优化专家池初始化` |
| `test` | 测试 | `test(chat): 添加聊天接口测试` |
| `chore` | 构建/工具 | `chore(deps): 更新依赖版本` |
| `perf` | 性能优化 | `perf(embedding): 缓存向量计算结果` |
| `ci` | CI/CD | `ci: 添加自动化测试流水线` |

#### 范围 (Scope)

- `api` - API接口
- `service` - 业务服务
- `model` - 数据模型
- `rag` - RAG检索
- `expert` - 专家系统
- `frontend` - 前端代码
- `config` - 配置相关
- `docs` - 文档

#### 示例

```bash
# 功能提交
git commit -m "feat(rag): 实现多级检索回退策略

- T1学科库优先检索
- T2通用库兜底检索
- 结果融合去重排序

Closes #45"

# Bug修复
git commit -m "fix(expert): 修复专家统计更新并发问题

使用乐观锁防止并发更新导致的统计丢失

Fixes #67"

# 文档更新
git commit -m "docs(api): 更新问答接口文档

- 添加请求/响应示例
- 说明错误码含义"
```

### Python 代码规范

```python
"""
模块级文档字符串，说明模块用途
"""

from typing import Optional, List, Dict
from dataclasses import dataclass

# 常量定义 - 全大写下划线分隔
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30


@dataclass
class RetrievalResult:
    """
    检索结果数据类
    
    Attributes:
        content: 知识内容
        score: 相似度分数 (0-1)
        source: 来源标识
    """
    content: str
    score: float
    source: str


class RetrievalService:
    """
    RAG检索服务
    
    提供多级检索能力，支持学科库优先、通用库兜底策略
    
    Example:
        >>> service = RetrievalService()
        >>> results = await service.retrieve("勾股定理是什么？", expert_id=1)
        >>> print(results[0].score)
        0.95
    """
    
    # 类常量
    DEFAULT_TOP_K = 5
    SIMILARITY_THRESHOLD = 0.6
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """
        初始化检索服务
        
        Args:
            embedding_service: 可选的向量化服务实例
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self._cache: Dict[str, List[RetrievalResult]] = {}
    
    async def retrieve(
        self,
        query: str,
        expert_id: int,
        top_k: int = DEFAULT_TOP_K,
        use_cache: bool = True
    ) -> List[RetrievalResult]:
        """
        检索相关知识
        
        Args:
            query: 查询文本
            expert_id: 专家ID
            top_k: 返回结果数量
            use_cache: 是否使用缓存
            
        Returns:
            按相似度排序的检索结果列表
            
        Raises:
            ValueError: 当 query 为空字符串时
            ExpertNotFoundError: 当 expert_id 不存在时
        """
        if not query.strip():
            raise ValueError("查询文本不能为空")
            
        # 实现逻辑...
        pass
    
    def _calculate_similarity(
        self, 
        vec1: List[float], 
        vec2: List[float]
    ) -> float:
        """
        计算向量相似度 (私有方法)
        
        使用余弦相似度计算两个向量的相似程度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            相似度分数 (0-1)
        """
        # 实现逻辑...
        pass


# 模块级函数
def create_default_service() -> RetrievalService:
    """创建默认配置的检索服务实例"""
    return RetrievalService()
```

### TypeScript/Vue 代码规范

```typescript
// 类型定义 - 使用接口
interface ChatRequest {
  query: string;
  image?: string;
  sessionId?: string;
}

interface ChatResponse {
  answer: string;
  expertName: string;
  usedKnowledges: KnowledgeItem[];
  responseTime: number;
}

// 组合式函数 - 使用 use 前缀
export function useChatService() {
  const loading = ref(false);
  const error = ref<string | null>(null);
  
  const sendMessage = async (request: ChatRequest): Promise<ChatResponse> => {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await fetch('/api/v1/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (e) {
      error.value = e instanceof Error ? e.message : '未知错误';
      throw e;
    } finally {
      loading.value = false;
    }
  };
  
  return {
    loading: readonly(loading),
    error: readonly(error),
    sendMessage
  };
}

// Vue 组件
<template>
  <div class="chat-container">
    <MessageList :messages="messages" />
    <InputBox 
      v-model="inputText"
      :loading="loading"
      @send="handleSend"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useChatService } from '@/composables/useChatService';

// Props 定义
interface Props {
  expertId?: number;
}

const props = withDefaults(defineProps<Props>(), {
  expertId: undefined
});

// Emits 定义
const emit = defineEmits<{
  (e: 'message-sent', message: string): void;
}>();

// 状态
const inputText = ref('');
const messages = ref<Message[]>([]);

// 组合式函数
const { loading, error, sendMessage } = useChatService();

// 计算属性
const canSend = computed(() => 
  inputText.value.trim().length > 0 && !loading.value
);

// 方法
const handleSend = async () => {
  if (!canSend.value) return;
  
  const text = inputText.value;
  messages.value.push({ type: 'user', content: text });
  
  try {
    const response = await sendMessage({
      query: text,
      expertId: props.expertId
    });
    
    messages.value.push({
      type: 'assistant',
      content: response.answer,
      expert: response.expertName
    });
    
    emit('message-sent', text);
    inputText.value = '';
  } catch (e) {
    // 错误已在 composable 中处理
    console.error('发送失败:', e);
  }
};
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>
```

---

## 🔍 代码审查 (Code Review)

### 审查清单

#### 功能性
- [ ] 代码是否实现了需求描述的功能
- [ ] 边界条件是否正确处理
- [ ] 错误处理是否完善
- [ ] 并发安全问题是否考虑

#### 可读性
- [ ] 命名是否清晰、一致
- [ ] 代码结构是否清晰
- [ ] 注释是否充分
- [ ] 是否遵循代码规范

#### 性能
- [ ] 是否有明显的性能问题
- [ ] 数据库查询是否优化
- [ ] 是否有不必要的计算
- [ ] 内存使用是否合理

#### 安全性
- [ ] 输入是否验证和过滤
- [ ] 敏感数据是否正确处理
- [ ] 权限控制是否正确

#### 测试
- [ ] 是否有对应的单元测试
- [ ] 测试覆盖率是否足够
- [ ] 集成测试是否通过

### 审查流程

```
开发者提交 PR
    ↓
CI 自动化检查 (lint/test/build)
    ↓
代码审查者审查 (至少1人)
    ↓
    ├─ 有意见 → 开发者修改 → 重新审查
    ↓
审查通过
    ↓
合并到目标分支
```

### 审查评论规范

```
[nitpick] - 小建议，不阻塞合并
[suggestion] - 建议修改，可以讨论
[question] - 有疑问，需要解释
[blocking] - 阻塞问题，必须修复
[praise] - 表扬好的实践
```

---

## 🧪 测试策略

### 测试金字塔

```
       /\
      /  \     E2E 测试 (少量)
     /----\    
    /      \   集成测试 (中等)
   /--------\  
  /          \ 单元测试 (大量)
 /------------\
```

### 单元测试 (Python)

```python
# tests/services/test_retrieval_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.rag.retrieval_service import RetrievalService


class TestRetrievalService:
    """检索服务单元测试"""
    
    @pytest.fixture
    def service(self):
        mock_embedding = Mock()
        mock_embedding.encode.return_value = [0.1] * 384
        return RetrievalService(embedding_service=mock_embedding)
    
    @pytest.mark.asyncio
    async def test_retrieve_empty_query_should_raise(self, service):
        """空查询应该抛出 ValueError"""
        with pytest.raises(ValueError, match="查询文本不能为空"):
            await service.retrieve("", expert_id=1)
    
    @pytest.mark.asyncio
    async def test_retrieve_with_cache_should_use_cache(self, service):
        """缓存命中时应该返回缓存结果"""
        # 准备缓存数据
        cached_results = [
            RetrievalResult(content="test", score=0.9, source="cache")
        ]
        service._cache["test_query_1"] = cached_results
        
        # 执行
        results = await service.retrieve(
            "test query", 
            expert_id=1, 
            use_cache=True
        )
        
        # 验证
        assert results == cached_results
    
    @pytest.mark.asyncio
    async def test_retrieve_should_return_sorted_results(self, service):
        """结果应该按相似度降序排列"""
        # 准备模拟数据...
        pass
```

### 集成测试

```python
# tests/integration/test_chat_flow.py
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_complete_chat_flow():
    """完整问答流程集成测试"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 发送问题
        response = await client.post("/api/v1/chat/send", json={
            "query": "勾股定理是什么？"
        })
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        # 2. 验证响应结构
        assert "answer" in data
        assert "expert_subject" in data
        assert data["expert_subject"] == "数学"
        
        # 3. 验证知识引用
        assert "used_knowledges" in data
        assert len(data["used_knowledges"]) > 0
```

### E2E 测试 (前端)

```typescript
// cypress/e2e/chat.cy.ts
describe('问答功能', () => {
  beforeEach(() => {
    cy.visit('/chat');
  });

  it('应该能够发送文本问题并获得回答', () => {
    // 输入问题
    cy.get('[data-testid="chat-input"]')
      .type('勾股定理是什么？');
    
    // 发送
    cy.get('[data-testid="send-button"]').click();
    
    // 验证回答出现
    cy.get('[data-testid="assistant-message"]')
      .should('be.visible')
      .and('contain', '勾股定理');
    
    // 验证学科识别
    cy.get('[data-testid="expert-badge"]')
      .should('contain', '数学');
  });

  it('应该能够上传图片', () => {
    cy.get('[data-testid="upload-button"]').click();
    cy.get('input[type="file"]').attachFile('math-problem.jpg');
    
    cy.get('[data-testid="image-preview"]')
      .should('be.visible');
  });
});
```

---

## 🚀 发布流程

### 发布检查清单

- [ ] 所有测试通过
- [ ] 代码审查完成
- [ ] 文档已更新
- [ ] 更新日志已编写
- [ ] 版本号已更新
- [ ] 配置已检查
- [ ] 数据库迁移已准备

### 自动化发布流水线

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: |
          pytest tests/ --cov=app --cov-report=xml
      - name: Upload Coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker Image
        run: |
          docker build -t eduqa:${{ github.ref_name }} .
      - name: Push to Registry
        run: |
          docker push registry.eduqa.io/backend:${{ github.ref_name }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Staging
        run: |
          kubectl set image deployment/eduqa-backend \
            backend=registry.eduqa.io/backend:${{ github.ref_name }}
      - name: Run Smoke Tests
        run: |
          ./scripts/smoke-tests.sh
      - name: Deploy to Production
        if: success()
        run: |
          kubectl set image deployment/eduqa-backend \
            backend=registry.eduqa.io/backend:${{ github.ref_name }}
```

---

## 📚 文档维护

### 文档类型

| 文档 | 位置 | 维护责任 | 更新时机 |
|------|------|----------|----------|
| API 文档 | `/docs/api` | 后端开发 | 接口变更时 |
| 架构文档 | `/docs/architecture` | 架构师 | 架构变更时 |
| 部署文档 | `/docs/deployment` | 运维 | 部署流程变更时 |
| 开发指南 | `/docs/development` | Tech Lead | 流程变更时 |
| 用户手册 | `/docs/user` | 产品经理 | 功能发布时 |

### 文档更新流程

1. **代码变更时同步更新文档**
2. **PR 中包含文档变更说明**
3. **定期审查文档准确性 (每季度)**

---

## 🎯 最佳实践总结

### Do's ✅
- 小步快跑，频繁提交
- 写自解释的代码 + 必要的注释
- 先写测试再写实现 (TDD)
- 保持函数小而单一职责
- 及时重构，保持代码健康

### Don'ts ❌
- 一次性提交大量代码
- 复制粘贴代码
- 忽略警告和类型错误
- 跳过测试直接提交
- 硬编码魔法数字/字符串

---

**文档版本**: v1.0  
**最后更新**: 2026-03-13  
**维护者**: Development Team
