
import os
import sys
import numpy as np
from sqlalchemy import text, func, type_coerce, case, literal
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

load_dotenv()

from app.db.session import SessionLocal
from app.db.models.models import TeamMember, TeamMemberEmbedding

def debug_query():
    db = SessionLocal()
    try:
        # Try a simple join without filters
        raw_join_count = db.query(TeamMember.team_member_id).join(TeamMemberEmbedding).count()
        print(f"Total RAW joined candidates: {raw_join_count}")
        
        # Check first 5 IDs
        raw_ids = db.query(TeamMember.team_member_id).join(TeamMemberEmbedding).limit(5).all()
        print(f"Raw IDs: {[r.team_member_id for r in raw_ids]}")
        
        if count == 0:
            return

        # Try a simple vector similarity query
        # Mock vector (all ones)
        mock_vec = [1.0] * 768
        
        v_sim = (1 - type_coerce(TeamMemberEmbedding.embedding, Vector(768)).cosine_distance(mock_vec)).label("v_sim")
        
        results = db.query(TeamMember.team_member_id, v_sim).join(TeamMemberEmbedding).filter(TeamMember.is_active == True).limit(5).all()
        
        print("\nSimple Vector Sim Results (Mock Vector):")
        for row in results:
            print(f"ID: {row.team_member_id}, Sim: {row.v_sim}")

        # Try a simple BM25 query
        query_text = "AI Lead"
        ts_query = func.plainto_tsquery('english', query_text)
        search_text = func.coalesce(TeamMemberEmbedding.profile_text, "") + " " + func.coalesce(TeamMemberEmbedding.skills_text, "")
        bm25 = func.ts_rank_cd(func.to_tsvector('english', search_text), ts_query)
        
        results = db.query(TeamMember.team_member_id, bm25.label("b_score")).join(TeamMemberEmbedding).filter(TeamMember.is_active == True).order_by(text("b_score DESC")).limit(5).all()
        
        print("\nSimple BM25 Results:")
        for row in results:
            print(f"ID: {row.team_member_id}, BM25: {row.b_score}")

    finally:
        db.close()

if __name__ == "__main__":
    debug_query()
