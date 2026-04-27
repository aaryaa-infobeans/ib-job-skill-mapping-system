
import logging
import sys
import os
import traceback

# Add src to path
sys.path.append(os.path.abspath("src"))

# Mock settings
os.environ["LOG_LEVEL"] = "INFO"
os.environ["SECRETS_BACKEND"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.ai.graph import create_graph
from app.ai.state import GraphState

def test_fail_fast():
    # Create graph
    graph = create_graph()
    
    # Define a state that will cause failure in the first node (requisition_parsing)
    state = {
        "requisition_input": None
    }
    
    print("Executing graph with invalid state...")
    try:
        final_state = graph.invoke(state)
        print(f"Graph execution completed. Error message: {final_state.get('error_message')}")
        
        if final_state.get("error_message") == "Missing requisition_input":
            print("SUCCESS: Graph failed fast as expected.")
        else:
            print(f"FAILURE: Graph did not fail as expected. Error: {final_state.get('error_message')}")
            
    except Exception as e:
        traceback.print_exc()
        print(f"EXCEPTION: {str(e)}")

if __name__ == "__main__":
    test_fail_fast()
