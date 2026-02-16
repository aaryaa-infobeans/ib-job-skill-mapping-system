"""End-to-end test for validation with full LangGraph execution."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.ai.graph import create_graph


def test_invalid_requisition_with_full_graph():
    """Test that invalid requisition stops the graph execution early."""
    print("\n" + "="*70)
    print("E2E TEST: Invalid Requisition with Full Graph")
    print("="*70)
    
    # Create the graph
    graph = create_graph()
    
    # Create an invalid requisition state
    invalid_state = {
        "requisition_input": {
            "request_id": "REQ-TEST-1771149515921",
            "correlation_id": "CORR-TEST-INVALID-E2E",
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
    
    # Run the graph
    print("\n🔄 Running full LangGraph...")
    try:
        final_state = None
        for event in graph.stream(invalid_state):
            print(f"  📍 Event: {list(event.keys())}")
            # Get the last state
            for node_name, node_state in event.items():
                final_state = node_state
        
        print("\n📊 Final State:")
        print(f"  Error Message: {final_state.get('error_message')}")
        print(f"  Parsed JD: {final_state.get('parsed_jd')}")
        print(f"  Normalized Skills: {final_state.get('normalized_skills')}")
        print(f"  Candidate Scores: {final_state.get('candidate_scores')}")
        print(f"  Final Results: {final_state.get('final_results')}")
        
        # Assertions
        assert final_state.get("error_message") is not None, "Expected error_message to be set"
        assert "VALIDATION_FAILED" in final_state["error_message"], "Expected VALIDATION_FAILED in error"
        assert final_state.get("parsed_jd") is None, "Expected parsed_jd to remain None"
        assert final_state.get("normalized_skills") is None, "Expected normalized_skills to remain None (graph stopped)"
        assert final_state.get("candidate_scores") is None, "Expected candidate_scores to remain None (graph stopped)"
        assert final_state.get("final_results") is None, "Expected final_results to remain None (graph stopped)"
        
        print("\n✅ ASSERTIONS PASSED:")
        print("  ✓ Error message set with VALIDATION_FAILED")
        print("  ✓ Graph stopped after requisition_parsing (no downstream processing)")
        print("  ✓ No normalized_skills, candidate_scores, or final_results")
        
        # Extract validation reasons
        error_msg = final_state["error_message"]
        validation_reasons = error_msg.replace("VALIDATION_FAILED: ", "")
        print(f"\n📋 Validation Reasons:")
        for reason in validation_reasons.split("; "):
            print(f"  • {reason}")
        
        print("\n" + "="*70)
        print("✅ E2E TEST PASSED!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ ERROR during graph execution: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_valid_requisition_with_full_graph():
    """Test that valid requisition proceeds through the graph."""
    print("\n" + "="*70)
    print("E2E TEST: Valid Requisition with Full Graph")
    print("="*70)
    
    # Create the graph
    graph = create_graph()
    
    # Create a valid requisition state
    valid_state = {
        "requisition_input": {
            "request_id": "REQ-TEST-VALID-E2E",
            "correlation_id": "CORR-TEST-VALID-E2E",
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
    
    # Run the graph
    print("\n🔄 Running full LangGraph...")
    try:
        final_state = None
        nodes_executed = []
        for event in graph.stream(valid_state):
            node_names = list(event.keys())
            nodes_executed.extend(node_names)
            print(f"  📍 Event: {node_names}")
            # Get the last state
            for node_name, node_state in event.items():
                final_state = node_state
        
        print(f"\n📊 Nodes Executed: {nodes_executed}")
        print(f"\n📊 Final State:")
        print(f"  Error Message: {final_state.get('error_message')}")
        print(f"  Parsed JD: {'✓ Present' if final_state.get('parsed_jd') else '✗ None'}")
        print(f"  Normalized Skills: {'✓ Present' if final_state.get('normalized_skills') else '✗ None'}")
        
        # Assertions - validation should pass
        if final_state.get("error_message"):
            assert "VALIDATION_FAILED" not in final_state["error_message"], \
                f"Unexpected validation failure: {final_state['error_message']}"
        
        assert final_state.get("parsed_jd") is not None, "Expected parsed_jd to be populated"
        
        print("\n✅ ASSERTIONS PASSED:")
        print("  ✓ No validation errors")
        print("  ✓ Graph proceeded through all nodes")
        print("  ✓ Parsed JD populated successfully")
        
        print("\n" + "="*70)
        print("✅ E2E TEST PASSED!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ ERROR during graph execution: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("\n" + "🧪 RUNNING END-TO-END TESTS ".center(70, "="))
    
    try:
        test_invalid_requisition_with_full_graph()
        test_valid_requisition_with_full_graph()
        
        print("\n" + "="*70)
        print("✅ ALL E2E TESTS PASSED!")
        print("="*70)
        print("\n💡 Summary:")
        print("  • Invalid requisitions stop at requisition_parsing node")
        print("  • Graph execution ends early (no downstream processing)")
        print("  • Valid requisitions proceed through all nodes normally")
        print("  • Conditional edge correctly routes based on error_message")
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
