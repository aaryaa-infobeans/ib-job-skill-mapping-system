from src.app.ai.agents.candidate_availability import (
    CandidateAvailabilityRequest,
    evaluate_availability,
    CandidateAvailabilityResponse,
)
from src.app.db.session import get_db
from langgraph.graph import StateGraph
from typing import Dict, Any
from fastapi import Depends

# LangGraph node: prepare
async def prepare_node(input_data: Dict[str, Any]) -> Dict[str, Any]:
    req = CandidateAvailabilityRequest(**input_data)
    return {"request": req}

# LangGraph node: query_db
async def query_db_node(state: Dict[str, Any], db=Depends(get_db)) -> Dict[str, Any]:
    req = state["request"]
    state["db"] = next(get_db())
    return state

# LangGraph node: decide
async def decide_node(state: Dict[str, Any]) -> Dict[str, Any]:
    db = state["db"]
    req = state["request"]
    response = evaluate_availability(db, req)
    state["response"] = response
    return state

# LangGraph node: finalize
async def finalize_node(state: Dict[str, Any]) -> CandidateAvailabilityResponse:
    return state["response"]

# Graph construction

def create_availability_graph():
    graph = StateGraph()
    graph.add_node("prepare", prepare_node)
    graph.add_node("query_db", query_db_node)
    graph.add_node("decide", decide_node)
    graph.add_node("finalize", finalize_node)
    graph.set_entry("prepare")
    graph.add_edge("prepare", "query_db")
    graph.add_edge("query_db", "decide")
    graph.add_edge("decide", "finalize")
    graph.set_exit("finalize")
    return graph

# Singleton instance (compile once)
availability_graph = create_availability_graph()
