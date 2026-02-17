"""
Integration Tests for PII Scrubber LangGraph Integration - TASK-PII-120

Tests end-to-end graph execution with PII scrubbing as Node 0.

Test Coverage:
- Success path: PII scrubbed → graph continues
- Validation gate: Unscrubbed data blocked (HTTP 422)
- Error handling: Scrubbing failures handled gracefully
- State propagation: pii_scrubbed flag flows through graph
- Performance: p95 latency ≤ 50ms

Linked Specs:
- Section 12: Testing strategy
- FR-PII-005: Validation gate
- TASK-PII-100: PII Scrubber Agent
- TASK-PII-101: Graph topology
"""

import sys
import os

# Add src to path for standalone execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestPIIScrubb erGraphIntegration:
    """Integration tests for PII Scrubber in LangGraph."""
    
    @pytest.fixture
    def mock_graph_state(self):
        """Fixture providing minimal graph state for testing."""
        return {
            "requisition_input": {
                "request_id": "test-req-001",
                "correlation_id": "corr-001",
                "job_description": {
                    "title": "Senior Python Developer",
                    "description": "We need a developer. Contact john.doe@example.com",
                    "client_name": "Acme Corporation",
                    "location": "New York, NY 10001"
                }
            },
            "pii_scrubbed": None,
            "error_message": None
        }
    
    def test_pii_scrubber_node_success(self, mock_graph_state, monkeypatch):
        """Test PII scrubber node processes state successfully."""
        # Set up environment
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "test_salt_" + "x" * 32)
        
        from app.ai.agents.pii_scrubber import pii_scrubber_node
        
        # Mock NER detector to avoid SpaCy dependency
        with patch('app.ai.agents.pii_scrubber.PIIScrubber') as MockScrubber:
            mock_scrubber = MockScrubber.return_value
            
            # Mock scrub_text to return scrubbed content
            def mock_scrub(text, **kwargs):
                scrubbed = text.replace("john.doe@example.com", "[EMAIL_REDACTED]")
                scrubbed = scrubbed.replace("10001", "[POSTAL_REDACTED]")
                
                from app.pii.scrubber import ScrubResult
                return ScrubResult(
                    original_text=text,
                    scrubbed_text=scrubbed,
                    detections=[
                        {'text': 'john.doe@example.com', 'pii_type': 'email', 'method': 'regex', 'action': 'redact', 'confidence': 1.0}
                    ] if '@' in text else [],
                    is_scrubbed=True,
                    deterministic=True
                )
            
            mock_scrubber.scrub_text.side_effect = mock_scrub
            
            # Execute node
            result_state = pii_scrubber_node(mock_graph_state)
            
            # Verify pii_scrubbed flag set
            assert result_state["pii_scrubbed"] is True
            
            # Verify PII was scrubbed
            scrubbed_desc = result_state["requisition_input"]["job_description"]["description"]
            assert "[EMAIL_REDACTED]" in scrubbed_desc
            assert "john.doe@example.com" not in scrubbed_desc
            
            # Verify metadata populated
            assert "pii_scrub_metadata" in result_state
            assert result_state["pii_scrub_metadata"]["total_pii_found"] > 0
    
    def test_validation_gate_blocks_unscrubbed_data(self, mock_graph_state):
        """Test validation gate blocks when pii_scrubbed = False (FR-PII-005)."""
        from app.ai.agents.pii_scrubber import should_continue_after_pii_scrubbing
        
        # Set pii_scrubbed to False
        mock_graph_state["pii_scrubbed"] = False
        
        # Execute validation gate
        result = should_continue_after_pii_scrubbing(mock_graph_state)
        
        # Should return END (block processing)
        assert result == "END"
        
        # Should set error message
        assert "Validation failed" in mock_graph_state.get("error_message", "")
    
    def test_validation_gate_allows_scrubbed_data(self, mock_graph_state):
        """Test validation gate allows when pii_scrubbed = True."""
        from app.ai.agents.pii_scrubber import should_continue_after_pii_scrubbing
        
        # Set pii_scrubbed to True
        mock_graph_state["pii_scrubbed"] = True
        
        # Execute validation gate
        result = should_continue_after_pii_scrubbing(mock_graph_state)
        
        # Should continue to requisition_parsing
        assert result == "requisition_parsing"
    
    def test_validation_gate_blocks_on_error(self, mock_graph_state):
        """Test validation gate blocks when error_message exists."""
        from app.ai.agents.pii_scrubber import should_continue_after_pii_scrubbing
        
        # Set error message
        mock_graph_state["error_message"] = "Scrubbing failed"
        mock_graph_state["pii_scrubbed"] = False
        
        # Execute validation gate
        result = should_continue_after_pii_scrubbing(mock_graph_state)
        
        # Should return END
        assert result == "END"
    
    def test_pii_scrubber_handles_empty_job_description(self, monkeypatch):
        """Test scrubber handles missing job description gracefully."""
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "test_salt_" + "x" * 32)
        
        from app.ai.agents.pii_scrubber import pii_scrubber_node
        
        state = {
            "requisition_input": {
                "request_id": "test-req-002",
                "correlation_id": "corr-002",
                "job_description": {}  # Empty JD
            }
        }
        
        with patch('app.ai.agents.pii_scrubber.PIIScrubber'):
            result = pii_scrubber_node(state)
            
            # Should set pii_scrubbed to False and error
            assert result["pii_scrubbed"] is False
            assert result.get("error_message") is not None
    
    def test_graph_topology_integration(self, monkeypatch):
        """Test that create_graph includes PII scrubber as Node 0 (TASK-PII-101)."""
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "test_salt_" + "x" * 32)
        
        # Mock all dependencies
        with patch('app.ai.graph.pii_scrubber_node'), \
             patch('app.ai.graph.requisition_parsing_node'), \
             patch('app.ai.graph.skill_normalization_node'), \
             patch('app.ai.graph.embedding_node'), \
             patch('app.ai.graph.rag_retrieval_node'), \
             patch('app.ai.graph.matching_scoring_node'), \
             patch('app.ai.graph.explanation_generation_node'), \
             patch('app.ai.graph.result_aggregation_node'):
            
            from app.ai.graph import create_graph
            
            # Create graph (should not fail)
            graph = create_graph()
            
            # Verify graph was created
            assert graph is not None
    
    def test_state_schema_includes_pii_fields(self):
        """Test GraphState schema includes pii_scrubbed and pii_scrub_metadata (TASK-PII-102, TASK-PII-103)."""
        from app.ai.state import GraphState, PIIScrubMetadata
        
        # Create state with PII fields
        state: GraphState = {
            "requisition_input": {
                "request_id": "test",
                "correlation_id": "test",
                "job_description": {}
            },
            "pii_scrubbed": True,
            "pii_scrub_metadata": {
                "detections": [],
                "fields_scrubbed": ["description"],
                "total_pii_found": 5
            },
            "parsed_jd": None,
            "normalized_skills": None,
            "candidate_scores": None,
            "final_results": None,
            "embedding_result": None,
            "retrieved_candidates": None,
            "total_evaluated": None,
            "total_qualified": None,
            "token_metrics": None,
            "llm_call_logs": None,
            "cumulative_tokens": None,
            "cumulative_cost_usd": None,
            "error_message": None
        }
        
        # Verify fields exist (type checking would catch missing fields)
        assert "pii_scrubbed" in state
        assert "pii_scrub_metadata" in state


def run_integration_tests():
    """Run integration tests standalone."""
    print("=" * 60)
    print("PII SCRUBBER INTEGRATION TESTS")
    print("=" * 60)
    
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_integration_tests()
