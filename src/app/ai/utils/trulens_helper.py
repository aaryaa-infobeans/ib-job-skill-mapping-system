"""TruLens helper utility for observability and feedback."""

import logging
from typing import Any, Dict, List, Optional
from trulens.core import Tru, Feedback
from trulens.feedback.templates.rag import Relevance, Groundedness
from trulens.apps.app import TruApp as App, instrument
from app.ai.utils.llm_client import llm_client

logger = logging.getLogger(__name__)

# Initialize TruLens
tru = Tru()

# Define Feedbacks
# Note: In a real scenario, providers for Relevance and Groundedness would be configured.
# For now, we initialize them as requested.
# f_relevance = Feedback(Relevance(examples=[])).on_input_output()
# f_grounded = Feedback(Groundedness(examples=[])).on_input_output()
# tru.add_feedbacks([f_relevance, f_grounded])

def _call_groq_api(
    messages: List[Dict[str, str]], 
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict] = None
):
    """Internal function to call Groq API via llm_client with full signature compatibility."""
    return llm_client.chat_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format
    )

class GroqAppWrapper:
    """Wrapper class to provide chat_completion method for TruLens instrumentation."""
    @instrument
    def chat_completion(self, **kwargs):
        # Map model_name to model for llm_client compatibility
        if "model_name" in kwargs:
            kwargs["model"] = kwargs.pop("model_name")
        return _call_groq_api(**kwargs)

# Wrap the LLM app
groq_tru_app = App(GroqAppWrapper(), app_name="groq_enrichment")
# Expose the inner app so callers can use it directly while being instrumented
groq_app = groq_tru_app.app

def compute_relevance_scores(query, results):
    """Compute relevance scores for results."""
    return [
        Relevance(examples=[]).evaluate(query, r.get("skills", "") + " " + r.get("role", ""))
        for r in results
    ]

# Unified instrumentation: and then use a single app for the whole pipeline
# Only instrument the methods, don't create separate Apps for components if we want a single trace.

class TalentSearchPipeline:
    """Class to wrap the talent search pipeline for TruLens instrumentation."""
    @instrument
    def search(self, query_text: str, db, request_id: str, job_description: Optional[Dict] = None):
        from app.ai.graph_executor import execute_graph_with_audit
        
        # Prepare initial state
        # Use provided job_description if available, else use default
        jd = job_description or {
            "jd_text": query_text,
            "title": "Senior Python Developer",
            "role": "Developer",
            "location": ["Mumbai"],
            "work_mode": ["Hybrid"],
            "client_name": "InfoBeans",
            "mandatory_skills": ["Python", "FastAPI"],
        }
        
        # Ensure jd_text is set correctly from query_text if jd_text is missing in dict
        if "jd_text" not in jd:
            jd["jd_text"] = query_text

        initial_state = {
            "requisition_input": {
                "request_id": request_id,
                "job_description": jd,
                "requested_team_ids": [],
                "min_availability_percentage": 50,
                "correlation_id": f"corr_{request_id}",
            },
            "parsed_jd": None,
            "normalized_skills": None,
            "candidate_scores": None,
            "final_results": None,
            "error_message": None,
            "token_metrics": {},
            "llm_call_logs": [],
            "cumulative_tokens": 0,
            "cumulative_cost_usd": 0.0,
            "total_evaluated": 0,
            "total_qualified": 0,
        }

        # Execute graph
        final_state = execute_graph_with_audit(initial_state, request_id, db)
        results = final_state.get("final_results") or []
        return results, final_state

# Global instance for shared use
pipeline_logic = TalentSearchPipeline()
# We create a single TruApp for the entire talent search system
tru_app = App(app=pipeline_logic, app_name='talent_search_pipeline')

# Backward compatibility or internal usage
groq_app = GroqAppWrapper()
# Re-point groq_tru_app to tru_app to keep imports working but consolidate recording
groq_tru_app = tru_app 

def avg_match_score(results):
    """Calculate average match score."""
    return sum(r.get("final_similarity", 0) for r in results) / len(results) if results else 0

def mandatory_hit_rate(results):
    """Calculate mandatory hit rate."""
    return sum(1 for r in results if r.get("mandatory_similarity", 0) > 0) / len(results) if results else 0

def search_team_members_by_job_spec(query_text: str, db, request_id: str = "trulens_run"):
    """
    Main entrypoint for talent search pipeline with TruLens instrumentation.
    """
    with tru_app as recording:
        results, final_state = pipeline_logic.search(query_text, db, request_id)

        # Log custom metrics to TruLens via metadata
        recording.record_metadata = {
            "query": query_text,
            "num_results": len(results),
            "avg_match_score": avg_match_score(results),
            "mandatory_hit_rate": mandatory_hit_rate(results)
        }

        return results

if __name__ == "__main__":
    tru.run_dashboard()
