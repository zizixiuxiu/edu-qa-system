"""Tier 0 自动入库服务单元测试"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock

from app.services.tier0.tier0_ingest_service import Tier0IngestService


@pytest.fixture
def service():
    return Tier0IngestService()


@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def sample_quality_result():
    """样本质检结果"""
    return {
        "overall_score": 4.5,
        "accuracy_score": 4.5,
        "completeness_score": 4.0,
        "educational_score": 4.5,
        "additional_score": 4.2,
        "knowledge_type": "formula",
        "corrected_answer": "纠正后的答案",
        "improvement_suggestions": "改进建议"
    }


class TestQualityThreshold:
    """测试质量阈值过滤"""
    
    @pytest.mark.asyncio
    async def test_low_quality_rejected(self, service, mock_session):
        """低质量应该被拒绝入库"""
        result = await service.auto_ingest(
            session=mock_session,
            session_id=1,
            question="测试问题",
            local_answer="本地答案",
            cloud_corrected="纠正答案",
            quality_result={"overall_score": 3.5},
            expert_id=1
        )
        
        assert result["status"] == "rejected"
        assert "quality_too_low" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_high_quality_accepted(self, service, mock_session, sample_quality_result):
        """高质量应该被接受"""
        with patch('app.utils.embedding.embedding_service') as mock_emb:
            mock_emb.encode.return_value = np.random.randn(384)
            
            with patch.object(service, '_check_duplicate', new=AsyncMock(return_value={
                "is_duplicate": False, "similarity": 0.0, "existing_id": None
            })):
                with patch.object(service, '_update_expert_tier0_count', new=AsyncMock()):
                    # Mock Tier0Knowledge 避免 SQLAlchemy mapper 初始化问题
                    mock_knowledge = Mock()
                    mock_knowledge.id = 123
                    with patch('app.services.tier0.tier0_ingest_service.Tier0Knowledge', return_value=mock_knowledge):
                        result = await service.auto_ingest(
                            session=mock_session,
                            session_id=1,
                            question="测试问题",
                            local_answer="本地答案",
                            cloud_corrected="纠正答案",
                            quality_result=sample_quality_result,
                            expert_id=1
                        )
                        
                        assert result["status"] == "success"


class TestDuplicateDetection:
    """测试去重逻辑"""
    
    @pytest.mark.asyncio
    async def test_exact_duplicate_by_hash(self, service, mock_session):
        """SimHash完全匹配应该被视为重复"""
        mock_knowledge = Mock()
        mock_knowledge.id = 123
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_knowledge]
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await service._check_duplicate(
            session=mock_session,
            new_embedding=np.random.randn(384),
            question="相同的问题内容",
            new_score=4.5
        )
        
        assert result["is_duplicate"] is True
        assert result["similarity"] == 1.0
    
    @pytest.mark.asyncio
    async def test_vector_duplicate_replace(self, service, mock_session):
        """向量相似度高且新质量更高，应该替换旧记录"""
        # Mock SimHash不匹配
        mock_result1 = Mock()
        mock_result1.scalars.return_value.all.return_value = []
        
        # Mock 向量搜索返回高相似度结果
        mock_knowledge = Mock()
        mock_knowledge.id = 456
        mock_knowledge.quality_score = 4.0  # 旧记录质量较低
        
        mock_result2 = Mock()
        mock_result2.first.return_value = (mock_knowledge, 0.05)  # 距离0.05 = 相似度0.95
        
        mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # 新记录质量更高(4.5 > 4.0)，应该替换
        result = await service._check_duplicate(
            session=mock_session,
            new_embedding=np.random.randn(384),
            question="不同的问题",
            new_score=4.5
        )
        
        # 新记录质量更高，应该允许入库（旧记录被删除）
        assert result["is_duplicate"] is False


class TestIngestSuccess:
    """测试成功入库场景"""
    
    @pytest.mark.asyncio
    async def test_successful_ingest(self, service, mock_session, sample_quality_result):
        """完整成功入库流程"""
        with patch('app.utils.embedding.embedding_service') as mock_emb:
            mock_emb.encode.return_value = np.random.randn(384)
            
            with patch.object(service, '_check_duplicate', new=AsyncMock(return_value={
                "is_duplicate": False
            })):
                with patch.object(service, '_update_expert_tier0_count', new=AsyncMock()):
                    mock_knowledge = Mock()
                    mock_knowledge.id = 999
                    mock_session.add = Mock()
                    mock_session.refresh = AsyncMock()
                    
                    with patch('app.services.tier0.tier0_ingest_service.Tier0Knowledge', return_value=mock_knowledge):
                        result = await service.auto_ingest(
                            session=mock_session,
                            session_id=42,
                            question="测试数学题：2+2=?",
                            local_answer="4",
                            cloud_corrected="答案是4",
                            quality_result=sample_quality_result,
                            expert_id=1
                        )
                        
                        assert result["status"] == "success"
                        assert result["knowledge_id"] is not None
                        mock_session.add.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
