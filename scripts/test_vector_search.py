#!/usr/bin/env python
"""Script to test vector search and candidate matching using embeddings."""

import sys
import json
import numpy as np
from datetime import datetime

# Add src to path
sys.path.insert(0, "src")

from app.db.session import SessionLocal
from app.db.models.models import TeamMember, TeamMemberSkill, SkillMaster
from sqlalchemy import text


def search_similar_candidates(db, query_designation: str, top_k: int = 5) -> list:
    """Search for candidates similar to a query designation using vector similarity."""
    
    # Generate embedding for query (using simple hash-based method for demo)
    query_seed = hash(query_designation)
    rng = np.random.RandomState(query_seed % (2**31))
    query_embedding = rng.randn(3072).astype(np.float32)
    query_embedding_str = f"[{','.join(str(x) for x in query_embedding.tolist())}]"
    
    # Query using pgvector similarity
    sql = f"""
        SELECT 
            tm.team_member_id,
            tm.designation,
            tm.experience_in_months,
            tm.base_location,
            tm.work_type,
            tme.profile_text,
            (tme.embedding <-> '{query_embedding_str}'::vector) as distance
        FROM team_member_embeddings tme
        JOIN team_member tm ON tm.team_member_id = tme.team_member_id
        WHERE tm.is_active = true
        ORDER BY distance ASC
        LIMIT {top_k}
    """
    
    results = db.execute(text(sql)).fetchall()
    
    return results


def get_candidate_details(db, team_member_id: str) -> dict:
    """Get detailed information about a candidate including skills."""
    
    candidate = db.query(TeamMember).filter(
        TeamMember.team_member_id == team_member_id
    ).first()
    
    if not candidate:
        return None
    
    skills = db.query(TeamMemberSkill).filter(
        TeamMemberSkill.team_member_id == team_member_id,
        TeamMemberSkill.is_deleted == False
    ).all()
    
    skill_list = []
    for ts in skills:
        skill_list.append({
            "skill_name": ts.skill.skill_name,
            "rating": ts.rating or 0,
            "experience_months": ts.experience_in_months or 0,
        })
    
    return {
        "team_member_id": candidate.team_member_id,
        "designation": candidate.designation,
        "experience_months": candidate.experience_in_months,
        "location": candidate.base_location,
        "work_type": candidate.work_type,
        "is_active": candidate.is_active,
        "skills": skill_list,
    }


def print_search_results(results: list, query: str):
    """Pretty print search results."""
    print(f"\n{'='*80}")
    print(f"🔍 SEARCH: Candidates similar to '{query}'")
    print(f"{'='*80}")
    
    if not results:
        print("❌ No results found")
        return
    
    for i, result in enumerate(results, 1):
        team_member_id, designation, experience, location, work_type, profile_text, distance = result
        
        print(f"\n#{i} [{team_member_id}] {designation}")
        print(f"   📍 Location: {location} | Work: {work_type}")
        print(f"   ⏱️  Experience: {experience} months")
        print(f"   📝 Profile: {profile_text[:80]}...")
        print(f"   📊 Similarity Distance: {distance:.4f} (lower is more similar)")


def print_candidate_details(db, team_member_id: str):
    """Print detailed candidate information."""
    details = get_candidate_details(db, team_member_id)
    
    if not details:
        print(f"❌ Candidate {team_member_id} not found")
        return
    
    print(f"\n{'='*80}")
    print(f"👤 CANDIDATE DETAILS: {details['designation']}")
    print(f"{'='*80}")
    print(f"ID: {details['team_member_id']}")
    print(f"Designation: {details['designation']}")
    print(f"Experience: {details['experience_months']} months")
    print(f"Location: {details['location']}")
    print(f"Work Type: {details['work_type']}")
    print(f"Active: {'✅ Yes' if details['is_active'] else '❌ No'}")
    
    print(f"\n📚 Skills ({len(details['skills'])} total):")
    for skill in details['skills']:
        rating_stars = "⭐" * (skill['rating'] or 3)
        print(f"   • {skill['skill_name']:20s} {rating_stars} ({skill['experience_months']} months)")


def get_candidates_by_skills(db, required_skills: list, optional_skills: list = None) -> list:
    """Get candidates that match required skills."""
    
    if optional_skills is None:
        optional_skills = []
    
    # Normalize skill names to lowercase
    required_skills_lower = [s.lower() for s in required_skills]
    optional_skills_lower = [s.lower() for s in optional_skills]
    
    sql = text("""
        SELECT 
            tm.team_member_id,
            tm.designation,
            tm.experience_in_months,
            tm.base_location,
            COUNT(CASE WHEN sm.skill_name ILIKE ANY(:required_skills) THEN 1 END) as required_match_count,
            COUNT(CASE WHEN sm.skill_name ILIKE ANY(:optional_skills) THEN 1 END) as optional_match_count,
            COUNT(DISTINCT tms.skill_id) as total_skills,
            STRING_AGG(DISTINCT sm.skill_name, ', ' ORDER BY sm.skill_name) as all_skills
        FROM team_member tm
        LEFT JOIN team_member_skill tms ON tm.team_member_id = tms.team_member_id AND tms.is_deleted = false
        LEFT JOIN skill_master sm ON tms.skill_id = sm.skill_id
        WHERE tm.is_active = true
        GROUP BY tm.team_member_id, tm.designation, tm.experience_in_months, tm.base_location
        HAVING COUNT(CASE WHEN sm.skill_name ILIKE ANY(:required_skills) THEN 1 END) > 0
        ORDER BY required_match_count DESC, optional_match_count DESC
    """)
    
    results = db.execute(
        sql,
        {
            "required_skills": required_skills_lower,
            "optional_skills": optional_skills_lower,
        }
    ).fetchall()
    
    return results


def print_skill_matches(results: list, required: list, optional: list = None):
    """Print skill matching results."""
    print(f"\n{'='*80}")
    print(f"🎯 SKILL MATCHING")
    print(f"{'='*80}")
    print(f"Required Skills: {', '.join(required)}")
    if optional:
        print(f"Optional Skills: {', '.join(optional)}")
    print()
    
    if not results:
        print("❌ No candidates found with required skills")
        return
    
    for i, result in enumerate(results, 1):
        team_member_id, designation, experience, location, req_match, opt_match, total_skills, all_skills = result
        
        print(f"{i}. [{team_member_id}] {designation}")
        print(f"   📍 {location} | ⏱️  {experience} months")
        print(f"   ✅ Required Match: {req_match}/{len(required)} | "
              f"🎁 Optional Match: {opt_match}/{len(optional or [])}")
        print(f"   📊 Total Skills: {total_skills} ({all_skills[:60]}...)" if all_skills else "   📊 No skills")
        print()


def main():
    """Main test function."""
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("🚀 CANDIDATE SEARCH & MATCHING SYSTEM - VECTOR SEARCH TEST")
        print("="*80)
        
        # Test 1: Vector similarity search
        print("\n\n[TEST 1] Vector Similarity Search")
        print("-" * 80)
        results = search_similar_candidates(db, "Senior Backend Developer", top_k=5)
        print_search_results(results, "Senior Backend Developer")
        
        # Test 2: Candidate details
        print("\n\n[TEST 2] Candidate Details & Skills")
        print("-" * 80)
        if results:
            team_member_id = results[0][0]
            print_candidate_details(db, team_member_id)
        
        # Test 3: Skill-based matching
        print("\n\n[TEST 3] Skill-Based Candidate Matching")
        print("-" * 80)
        skill_results = get_candidates_by_skills(
            db,
            required_skills=["Python", "FastAPI", "PostgreSQL"],
            optional_skills=["AWS", "Kubernetes"]
        )
        print_skill_matches(
            skill_results,
            ["Python", "FastAPI", "PostgreSQL"],
            ["AWS", "Kubernetes"]
        )
        
        # Test 4: Another skill search
        print("\n\n[TEST 4] Alternative Skill Search - Frontend Stack")
        print("-" * 80)
        frontend_results = get_candidates_by_skills(
            db,
            required_skills=["React"],
            optional_skills=["TypeScript", "JavaScript"]
        )
        print_skill_matches(
            frontend_results,
            ["React"],
            ["TypeScript", "JavaScript"]
        )
        
        # Summary statistics
        print("\n\n[SUMMARY] Database Statistics")
        print("-" * 80)
        
        total_candidates = db.query(TeamMember).filter(TeamMember.is_active == True).count()
        total_embeddings = db.execute(text("SELECT COUNT(*) FROM team_member_embeddings")).scalar()
        total_skills = db.query(SkillMaster).count()
        
        # Get location distribution
        location_dist = db.execute(text("""
            SELECT base_location, COUNT(*) as count
            FROM team_member
            WHERE is_active = true
            GROUP BY base_location
            ORDER BY count DESC
        """)).fetchall()
        
        # Get experience distribution
        exp_dist = db.execute(text("""
            SELECT 
                CASE 
                    WHEN experience_in_months < 24 THEN 'Junior (0-2 years)'
                    WHEN experience_in_months < 60 THEN 'Mid (2-5 years)'
                    WHEN experience_in_months < 96 THEN 'Senior (5-8 years)'
                    ELSE 'Expert (8+ years)'
                END as level,
                COUNT(*) as count
            FROM team_member
            WHERE is_active = true
            GROUP BY level
        """)).fetchall()
        
        print(f"✅ Total Active Candidates: {total_candidates}")
        print(f"✅ Total Embeddings: {total_embeddings}")
        print(f"✅ Total Skills in Database: {total_skills}")
        
        print(f"\n📍 Location Distribution:")
        for location, count in location_dist:
            pct = (count / total_candidates) * 100
            print(f"   {location:15s}: {count:3d} candidates ({pct:5.1f}%)")
        
        print(f"\n⏱️  Experience Distribution:")
        for level, count in exp_dist:
            pct = (count / total_candidates) * 100
            print(f"   {level:20s}: {count:3d} candidates ({pct:5.1f}%)")
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
