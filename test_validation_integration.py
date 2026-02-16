"""Integration test for requisition validation in the LangGraph pipeline."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.ai.agents.requisition_parsing import requisition_parsing_node
from app.ai.state import GraphState


def test_invalid_requisition_stops_pipeline():
    """Test that invalid requisition stops the pipeline at parsing stage."""
    print("\n" + "="*70)
    print("INTEGRATION TEST: Invalid Requisition Should Stop Pipeline")
    print("="*70)
    
    # Create an invalid requisition (empty JD text, no skills)
    invalid_state = {
        "requisition_input": {
            "request_id": "REQ-TEST-1771149515921",
            "correlation_id": "CORR-TEST-INVALID",
            "job_description": {
                "client_name": "Test Corp",
                "title": "Developer",
                "role": "Developer",
                "jd_text": "",  # Invalid: empty
                "mandatory_skills": [],  # Invalid: no skills
                "preferred_skills": [],
                "location": [],  # Invalid: empty
                "work_mode": ["Remote"],
                "priority": "MEDIUM"
            }
        },
        "parsed_jd": None,
        "normalized_skills": None,
        "candidate_scores": None,
        "final_results": None,
        "error_message": None,
        "llm_call_logs": [],
        "cumulative_tokens": 0,
        "cumulative_cost_usd": 0.0,
    }
    
    print("\n📝 Input State:")
    print(f"  Request ID: {invalid_state['requisition_input']['request_id']}")
    print(f"  JD Text: '{invalid_state['requisition_input']['job_description']['jd_text']}'")
    print(f"  Mandatory Skills: {invalid_state['requisition_input']['job_description']['mandatory_skills']}")
    print(f"  Location: {invalid_state['requisition_input']['job_description']['location']}")
    
    # Run the parsing node
    print("\n🔄 Running requisition_parsing_node...")
    result_state = requisition_parsing_node(invalid_state)
    
    print("\n📊 Output State:")
    print(f"  Error Message: {result_state.get('error_message')}")
    print(f"  Parsed JD: {result_state.get('parsed_jd')}")
    print(f"  LLM Calls: {len(result_state.get('llm_call_logs', []))}")
    
    # Assertions
    assert result_state.get("error_message") is not None, "Expected error_message to be set"
    assert "VALIDATION_FAILED" in result_state["error_message"], "Expected VALIDATION_FAILED in error"
    assert result_state.get("parsed_jd") is None, "Expected parsed_jd to remain None"
    assert len(result_state.get("llm_call_logs", [])) == 0, "Expected no LLM calls for invalid requisition"
    
    print("\n✅ ASSERTIONS PASSED:")
    print("  ✓ Error message set with VALIDATION_FAILED")
    print("  ✓ Parsed JD remains None (no processing)")
    print("  ✓ No LLM calls made (saved cost)")
    
    # Extract validation reasons
    error_msg = result_state["error_message"]
    validation_reasons = error_msg.replace("VALIDATION_FAILED: ", "")
    print(f"\n📋 Validation Reasons:")
    for reason in validation_reasons.split("; "):
        print(f"  • {reason}")
    
    print("\n" + "="*70)
    print("✅ INTEGRATION TEST PASSED!")
    print("="*70)


def test_valid_requisition_proceeds():
    """Test that valid requisition proceeds through parsing."""
    print("\n" + "="*70)
    print("INTEGRATION TEST: Valid Requisition Should Proceed")
    print("="*70)
    
    # Create a valid requisition
    valid_state = {
        "requisition_input": {
            "request_id": "REQ-TEST-VALID-001",
            "correlation_id": "CORR-TEST-VALID",
            "job_description": {
                "client_name": "Acme Corp",
                "title": "Senior Python Developer",
                "role": "Backend Developer",
                "jd_text": "We are looking for an experienced Python developer with strong FastAPI skills. The ideal candidate will have 3-5 years of experience building scalable REST APIs.",
                "mandatory_skills": ["Python", "FastAPI", "PostgreSQL"],
                "preferred_skills": ["Docker", "Kubernetes"],
                "experience": {"min_months": 36, "max_months": 60},
                "location": ["Bangalore", "Remote"],
                "work_mode": ["Hybrid"],
                "priority": "HIGH"
            }
        },
        "parsed_jd": None,
        "normalized_skills": None,
        "candidate_scores": None,
        "final_results": None,
        "error_message": None,
        "llm_call_logs": [],
        "cumulative_tokens": 0,
        "cumulative_cost_usd": 0.0,
    }
    
    print("\n📝 Input State:")
    print(f"  Request ID: {valid_state['requisition_input']['request_id']}")
    print(f"  Title: {valid_state['requisition_input']['job_description']['title']}")
    print(f"  Mandatory Skills: {valid_state['requisition_input']['job_description']['mandatory_skills']}")
    
    # Run the parsing node
    print("\n🔄 Running requisition_parsing_node...")
    result_state = requisition_parsing_node(valid_state)
    
    print("\n📊 Output State:")
    print(f"  Error Message: {result_state.get('error_message')}")
    print(f"  Parsed JD: {'✓ Present' if result_state.get('parsed_jd') else '✗ None'}")
    
    # Assertions
    # Note: If LLM is not configured, it will use fallback parsing
    # Either way, validation should pass and parsing should occur
    if result_state.get("error_message"):
        # Check it's not a validation error
        assert "VALIDATION_FAILED" not in result_state["error_message"], \
            f"Unexpected validation failure: {result_state['error_message']}"
    
    # Should have parsed_jd (either from LLM or fallback)
    assert result_state.get("parsed_jd") is not None, "Expected parsed_jd to be populated"
    
    print("\n✅ ASSERTIONS PASSED:")
    print("  ✓ No validation errors")
    print("  ✓ Parsed JD populated (processing occurred)")
    
    if result_state.get("parsed_jd"):
        print(f"\n📋 Parsed JD:")
        print(f"  Normalized Title: {result_state['parsed_jd'].get('normalized_title')}")
        print(f"  Normalized Role: {result_state['parsed_jd'].get('normalized_role')}")
    
    print("\n" + "="*70)
    print("✅ INTEGRATION TEST PASSED!")
    print("="*70)


if __name__ == "__main__":
    print("\n" + "🧪 RUNNING INTEGRATION TESTS ".center(70, "="))
    
    try:
        test_invalid_requisition_stops_pipeline()
        test_valid_requisition_proceeds()
        
        print("\n" + "="*70)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("="*70)
        print("\n💡 Summary:")
        print("  • Invalid requisitions are caught at validation stage")
        print("  • No LLM processing occurs for invalid requisitions")
        print("  • Valid requisitions proceed through parsing normally")
        print("  • Validation reasons are clearly reported in error_message")
        print("="*70 + "\n")
        
    except AssertionError as e:
        print("\n" + "="*70)
        print(f"❌ TEST FAILED: {e}")
        print("="*70)
        sys.exit(1)
    except Exception as e:
        print("\n" + "="*70)
        print(f"❌ ERROR: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
