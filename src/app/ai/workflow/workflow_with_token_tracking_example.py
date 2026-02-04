"""
Example: Integrating Token Tracking into LangGraph Workflow

This module shows how to integrate TokenTracker and ExtendedAgentState
into your actual LangGraph workflow for the 5 checkpoints.

Real-world usage patterns and best practices.
"""

import logging
from typing import Optional
from datetime import datetime
from openai import OpenAI

from src.app.ai.workflow.extended_state import ExtendedAgentState
from src.app.ai.workflow.checkpoint_display import CheckpointDisplay


class WorkflowWithTokenTracking:
    """
    Example workflow integrating token tracking at each checkpoint.
    """
    
    def __init__(self, llm_client: OpenAI, logger: Optional[logging.Logger] = None):
        """
        Initialize workflow.
        
        Args:
            llm_client: OpenAI client
            logger: Optional logger
        """
        self.llm_client = llm_client
        self.logger = logger or logging.getLogger(__name__)
    
    async def checkpoint_1_jd_parsing(self, state: ExtendedAgentState) -> ExtendedAgentState:
        """
        Checkpoint 1: Parse requisition JD using LLM.
        
        Token tracking:
        - Records LLM call tokens
        - Tracks prompt and completion tokens
        - Calculates cost for this checkpoint
        """
        self.logger.info("=" * 80)
        self.logger.info("CHECKPOINT 1: JD Parsing")
        self.logger.info("=" * 80)
        
        # Mark entry into checkpoint
        state.enter_checkpoint("jd_parsing")
        state.log_checkpoint_entry(self.logger)
        
        try:
            # Parse JD using LLM
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Parse the job description into structured fields."
                    },
                    {
                        "role": "user",
                        "content": f"JD: {state.parsed_jd}"
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Record tokens for this LLM call
            state.record_tokens(
                segment="jd_parsing",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                model=response.model
            )
            
            # Process result
            state.parsed_jd = response.choices[0].message.content
            state.status = "parsing_complete"
            
            self.logger.info("✓ JD parsing complete")
            
        except Exception as e:
            self.logger.error(f"✗ JD parsing failed: {str(e)}")
            state.mark_error(f"JD parsing error: {str(e)}")
            raise
        
        finally:
            # Mark exit from checkpoint
            state.exit_checkpoint("jd_parsing")
            state.log_checkpoint_exit(self.logger)
        
        return state
    
    async def checkpoint_2_skill_normalization(self, state: ExtendedAgentState) -> ExtendedAgentState:
        """
        Checkpoint 2: Normalize and expand skills.
        
        Token tracking:
        - Multiple LLM calls (skill canonicalization, expansion)
        - Aggregate tokens across all calls in this checkpoint
        - Track cost per call and total for checkpoint
        """
        self.logger.info("=" * 80)
        self.logger.info("CHECKPOINT 2: Skill Normalization")
        self.logger.info("=" * 80)
        
        state.enter_checkpoint("skill_normalization")
        state.log_checkpoint_entry(self.logger)
        
        try:
            # Call 1: Normalize skills
            response1 = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Normalize skill names to canonical form."
                    },
                    {
                        "role": "user",
                        "content": f"Skills: {state.parsed_jd}"
                    }
                ]
            )
            
            state.record_tokens(
                segment="skill_normalization",
                prompt_tokens=response1.usage.prompt_tokens,
                completion_tokens=response1.usage.completion_tokens,
                model=response1.model
            )
            
            # Call 2: Expand skills
            response2 = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Expand skills with related terms and synonyms."
                    },
                    {
                        "role": "user",
                        "content": f"Skills: {response1.choices[0].message.content}"
                    }
                ]
            )
            
            # Record second call tokens
            state.record_tokens(
                segment="skill_normalization",
                prompt_tokens=response2.usage.prompt_tokens,
                completion_tokens=response2.usage.completion_tokens,
                model=response2.model
            )
            
            # Checkpoint 2 now has aggregated tokens from both calls
            state.normalized_skills = response2.choices[0].message.content
            state.status = "normalization_complete"
            
            self.logger.info("✓ Skill normalization complete (2 LLM calls)")
            
        except Exception as e:
            self.logger.error(f"✗ Skill normalization failed: {str(e)}")
            state.mark_error(f"Normalization error: {str(e)}")
            raise
        
        finally:
            state.exit_checkpoint("skill_normalization")
            state.log_checkpoint_exit(self.logger)
        
        return state
    
    async def checkpoint_3_matching_scoring(
        self,
        state: ExtendedAgentState,
        candidates: list
    ) -> ExtendedAgentState:
        """
        Checkpoint 3: Score candidates.
        
        Token tracking:
        - Many LLM calls (one per candidate)
        - Aggregate all tokens across all scoring calls
        - Track total cost for entire checkpoint
        """
        self.logger.info("=" * 80)
        self.logger.info("CHECKPOINT 3: Matching & Scoring")
        self.logger.info("=" * 80)
        
        state.enter_checkpoint("matching_scoring")
        state.log_checkpoint_entry(self.logger)
        
        try:
            scored_candidates = []
            
            # Score each candidate
            for i, candidate in enumerate(candidates, 1):
                response = self.llm_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "Score how well this candidate matches the requisition."
                        },
                        {
                            "role": "user",
                            "content": f"Candidate: {candidate}\nRequisition: {state.parsed_jd}"
                        }
                    ],
                    temperature=0.0,
                    max_tokens=200
                )
                
                # Record tokens for each scoring call
                state.record_tokens(
                    segment="matching_scoring",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    model=response.model
                )
                
                scored_candidates.append({
                    "candidate_id": candidate["id"],
                    "score": response.choices[0].message.content
                })
                
                if (i % 10) == 0:
                    self.logger.debug(f"  Scored {i}/{len(candidates)} candidates")
            
            state.scored_candidates = scored_candidates
            state.status = "scoring_complete"
            
            self.logger.info(f"✓ Matched and scored {len(candidates)} candidates")
            
        except Exception as e:
            self.logger.error(f"✗ Scoring failed: {str(e)}")
            state.mark_error(f"Scoring error: {str(e)}")
            raise
        
        finally:
            state.exit_checkpoint("matching_scoring")
            state.log_checkpoint_exit(self.logger)
        
        return state
    
    async def checkpoint_4_explanation_generation(self, state: ExtendedAgentState) -> ExtendedAgentState:
        """
        Checkpoint 4: Generate explanations for top candidates.
        
        Token tracking:
        - LLM calls for generating narratives
        - Typically fewer calls than checkpoint 3 (only top N candidates)
        - Aggregate tokens across all explanation calls
        """
        self.logger.info("=" * 80)
        self.logger.info("CHECKPOINT 4: Explanation Generation")
        self.logger.info("=" * 80)
        
        state.enter_checkpoint("explanation_generation")
        state.log_checkpoint_entry(self.logger)
        
        try:
            explanations = []
            
            # Generate explanations for top 10 candidates
            top_candidates = state.scored_candidates[:10]
            
            for i, candidate in enumerate(top_candidates, 1):
                response = self.llm_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "Generate a brief professional explanation of why this candidate matches."
                        },
                        {
                            "role": "user",
                            "content": f"Candidate {candidate['candidate_id']}: {candidate['score']}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                
                # Record tokens for each explanation
                state.record_tokens(
                    segment="explanation_generation",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    model=response.model
                )
                
                explanations.append({
                    "candidate_id": candidate["candidate_id"],
                    "explanation": response.choices[0].message.content
                })
            
            state.explanations = explanations
            state.status = "explanations_complete"
            
            self.logger.info(f"✓ Generated explanations for {len(explanations)} candidates")
            
        except Exception as e:
            self.logger.error(f"✗ Explanation generation failed: {str(e)}")
            state.mark_error(f"Explanation error: {str(e)}")
            raise
        
        finally:
            state.exit_checkpoint("explanation_generation")
            state.log_checkpoint_exit(self.logger)
        
        return state
    
    async def checkpoint_5_result_aggregation(self, state: ExtendedAgentState) -> ExtendedAgentState:
        """
        Checkpoint 5: Aggregate and format final results.
        
        Token tracking:
        - Single or few LLM calls for formatting
        - Finalize token tracking
        - Display final summary with all metrics
        """
        self.logger.info("=" * 80)
        self.logger.info("CHECKPOINT 5: Result Aggregation")
        self.logger.info("=" * 80)
        
        state.enter_checkpoint("result_aggregation")
        state.log_checkpoint_entry(self.logger)
        
        try:
            # Format final results with LLM
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Format the matching results as a professional report."
                    },
                    {
                        "role": "user",
                        "content": f"Results: {state.explanations}"
                    }
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            # Record final LLM call tokens
            state.record_tokens(
                segment="result_aggregation",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                model=response.model
            )
            
            state.ranked_candidates = state.explanations
            state.status = "completed"
            state.mark_complete()
            
            self.logger.info("✓ Results aggregated and formatted")
            
        except Exception as e:
            self.logger.error(f"✗ Result aggregation failed: {str(e)}")
            state.mark_error(f"Aggregation error: {str(e)}")
            raise
        
        finally:
            state.exit_checkpoint("result_aggregation")
            state.log_checkpoint_exit(self.logger)
        
        # Display final summary with all token metrics
        self._display_final_summary(state)
        
        return state
    
    def _display_final_summary(self, state: ExtendedAgentState) -> None:
        """Display final workflow summary with all metrics."""
        self.logger.info("\n" + "=" * 100)
        
        # Use CheckpointDisplay to format output
        display = CheckpointDisplay(state, self.logger)
        display.print_all_checkpoints()
        
        self.logger.info("=" * 100)
        
        # Also log structured summary
        state.log_final_summary(self.logger)


# Example execution
if __name__ == "__main__":
    import asyncio
    from openai import OpenAI
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Initialize
    llm_client = OpenAI()  # Uses OPENAI_API_KEY env var
    workflow = WorkflowWithTokenTracking(llm_client, logger)
    
    async def run_example():
        """Run example workflow with token tracking."""
        # Create initial state
        state = ExtendedAgentState(
            requisition_id="req-example-001",
            correlation_id="corr-example-xyz",
            parsed_jd="Senior Python Developer needed..."
        )
        
        # Mock candidates
        candidates = [
            {"id": f"cand-{i:03d}", "experience": f"{5+i*2} years"} 
            for i in range(50)
        ]
        
        try:
            # Run through checkpoints
            state = await workflow.checkpoint_1_jd_parsing(state)
            state = await workflow.checkpoint_2_skill_normalization(state)
            state = await workflow.checkpoint_3_matching_scoring(state, candidates[:50])
            state = await workflow.checkpoint_4_explanation_generation(state)
            state = await workflow.checkpoint_5_result_aggregation(state)
            
            # Results now include token metrics
            print("\n" + "=" * 100)
            print("FINAL METRICS")
            print("=" * 100)
            print(f"Total Tokens: {state.cumulative_tokens}")
            print(f"Total Cost: ${state.cumulative_cost_usd:.6f}")
            print(f"Checkpoints: {len(state.token_checkpoints)}")
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
    
    # Run
    asyncio.run(run_example())
