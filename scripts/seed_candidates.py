#!/usr/bin/env python
"""Script to generate and seed 50 candidate records with embeddings."""

import sys
import json
import numpy as np
from datetime import datetime, date
from sqlalchemy.orm import Session

# Add src to path
sys.path.insert(0, "src")

from app.db.session import SessionLocal
from app.db.models.models import TeamMember, TeamMemberSkill, SkillMaster
from sqlalchemy import text

# Sample candidate data
CANDIDATES = [
    {
        "id": "TM-001",
        "name": "Rajesh Kumar",
        "designation": "Senior Python Developer",
        "experience": 72,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
    },
    {
        "id": "TM-002",
        "name": "Priya Singh",
        "designation": "Full Stack Engineer",
        "experience": 60,
        "location": "Pune",
        "work_type": "wfh",
        "skills": ["React", "Node.js", "MongoDB", "Docker", "AWS"],
    },
    {
        "id": "TM-003",
        "name": "Amit Patel",
        "designation": "Backend Engineer",
        "experience": 48,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Java", "Spring", "PostgreSQL", "Kubernetes", "AWS"],
    },
    {
        "id": "TM-004",
        "name": "Deepak Sharma",
        "designation": "Cloud Architect",
        "experience": 84,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["AWS", "Kubernetes", "Terraform", "Docker", "Python"],
    },
    {
        "id": "TM-005",
        "name": "Neha Gupta",
        "designation": "Data Engineer",
        "experience": 54,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Python", "Spark", "PostgreSQL", "Airflow", "AWS"],
    },
    {
        "id": "TM-006",
        "name": "Vikram Singh",
        "designation": "DevOps Engineer",
        "experience": 48,
        "location": "Pune",
        "work_type": "hybrid",
        "skills": ["Kubernetes", "Docker", "Terraform", "AWS", "Python"],
    },
    {
        "id": "TM-007",
        "name": "Ananya Das",
        "designation": "Frontend Developer",
        "experience": 42,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["React", "TypeScript", "CSS", "JavaScript", "Node.js"],
    },
    {
        "id": "TM-008",
        "name": "Rohan Verma",
        "designation": "ML Engineer",
        "experience": 36,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Python", "TensorFlow", "PyTorch", "AWS", "PostgreSQL"],
    },
    {
        "id": "TM-009",
        "name": "Sneha Kumar",
        "designation": "QA Automation Engineer",
        "experience": 42,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Python", "Selenium", "Docker", "AWS", "Java"],
    },
    {
        "id": "TM-010",
        "name": "Arjun Nair",
        "designation": "Solutions Architect",
        "experience": 96,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Java", "AWS", "Kubernetes", "Terraform", "Spring"],
    },
    {
        "id": "TM-011",
        "name": "Pooja Reddy",
        "designation": "Senior Backend Developer",
        "experience": 66,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "AWS"],
    },
    {
        "id": "TM-012",
        "name": "Nikhil Choudhury",
        "designation": "Frontend Architect",
        "experience": 72,
        "location": "Pune",
        "work_type": "hybrid",
        "skills": ["React", "Vue.js", "TypeScript", "Webpack", "Node.js"],
    },
    {
        "id": "TM-013",
        "name": "Richa Patel",
        "designation": "Database Administrator",
        "experience": 54,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "Docker"],
    },
    {
        "id": "TM-014",
        "name": "Sameer Khan",
        "designation": "iOS Developer",
        "experience": 48,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Swift", "Objective-C", "iOS", "REST API", "AWS"],
    },
    {
        "id": "TM-015",
        "name": "Divya Singh",
        "designation": "Android Developer",
        "experience": 42,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Kotlin", "Java", "Android", "REST API", "Firebase"],
    },
    {
        "id": "TM-016",
        "name": "Harish Desai",
        "designation": "Security Engineer",
        "experience": 78,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["AWS", "Kubernetes", "Linux", "Python", "Docker"],
    },
    {
        "id": "TM-017",
        "name": "Kavya Menon",
        "designation": "Product Manager",
        "experience": 60,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["AWS", "Java", "Python", "SQL", "Agile"],
    },
    {
        "id": "TM-018",
        "name": "Manish Kumar",
        "designation": "Tech Lead",
        "experience": 84,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Java", "Spring", "PostgreSQL", "Kubernetes", "AWS"],
    },
    {
        "id": "TM-019",
        "name": "Anushka Sharma",
        "designation": "Data Scientist",
        "experience": 48,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Python", "Machine Learning", "Spark", "AWS", "PostgreSQL"],
    },
    {
        "id": "TM-020",
        "name": "Karthik Reddy",
        "designation": "Software Architect",
        "experience": 108,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Java", "Python", "AWS", "Kubernetes", "Microservices"],
    },
    {
        "id": "TM-021",
        "name": "Shreya Gupta",
        "designation": "Junior Python Developer",
        "experience": 24,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Python", "Django", "PostgreSQL", "REST API", "Git"],
    },
    {
        "id": "TM-022",
        "name": "Varun Singh",
        "designation": "Senior Java Developer",
        "experience": 72,
        "location": "Pune",
        "work_type": "hybrid",
        "skills": ["Java", "Spring Boot", "PostgreSQL", "Microservices", "AWS"],
    },
    {
        "id": "TM-023",
        "name": "Avni Desai",
        "designation": "UI/UX Designer",
        "experience": 36,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Figma", "Design Systems", "Prototyping", "CSS", "React"],
    },
    {
        "id": "TM-024",
        "name": "Suresh Reddy",
        "designation": "Infrastructure Engineer",
        "experience": 60,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Terraform", "AWS", "Docker", "Kubernetes", "Python"],
    },
    {
        "id": "TM-025",
        "name": "Isha Patel",
        "designation": "API Developer",
        "experience": 42,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Node.js", "Express", "MongoDB", "AWS", "REST API"],
    },
    {
        "id": "TM-026",
        "name": "Rahul Kumar",
        "designation": "Database Engineer",
        "experience": 54,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["PostgreSQL", "Elasticsearch", "Redis", "AWS", "Python"],
    },
    {
        "id": "TM-027",
        "name": "Zara Khan",
        "designation": "ML Operations Engineer",
        "experience": 36,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Python", "Kubernetes", "Docker", "AWS", "TensorFlow"],
    },
    {
        "id": "TM-028",
        "name": "Bhavesh Patel",
        "designation": "GraphQL Developer",
        "experience": 42,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["GraphQL", "Node.js", "React", "MongoDB", "AWS"],
    },
    {
        "id": "TM-029",
        "name": "Vidya Singh",
        "designation": "Cloud Security Engineer",
        "experience": 60,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["AWS", "Security", "Linux", "Python", "Docker"],
    },
    {
        "id": "TM-030",
        "name": "Chetan Verma",
        "designation": "Full Stack Architect",
        "experience": 96,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["React", "Node.js", "PostgreSQL", "Docker", "AWS"],
    },
    {
        "id": "TM-031",
        "name": "Payal Chopra",
        "designation": "Senior React Developer",
        "experience": 60,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["React", "TypeScript", "Redux", "Jest", "Node.js"],
    },
    {
        "id": "TM-032",
        "name": "Sanjay Desai",
        "designation": "Microservices Architect",
        "experience": 84,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Java", "Spring Cloud", "Kubernetes", "Docker", "AWS"],
    },
    {
        "id": "TM-033",
        "name": "Nisha Sharma",
        "designation": "Performance Engineer",
        "experience": 48,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Java", "Python", "Performance Testing", "AWS", "Linux"],
    },
    {
        "id": "TM-034",
        "name": "Ravi Kumar",
        "designation": "Big Data Engineer",
        "experience": 60,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Spark", "Hadoop", "Python", "AWS", "Scala"],
    },
    {
        "id": "TM-035",
        "name": "Sunita Patel",
        "designation": "Integration Engineer",
        "experience": 54,
        "location": "Pune",
        "work_type": "hybrid",
        "skills": ["Java", "REST API", "Message Queue", "PostgreSQL", "AWS"],
    },
    {
        "id": "TM-036",
        "name": "Gaurav Singh",
        "designation": "DevOps Lead",
        "experience": 72,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Kubernetes", "Docker", "Jenkins", "Terraform", "AWS"],
    },
    {
        "id": "TM-037",
        "name": "Meera Nair",
        "designation": "Web Performance Specialist",
        "experience": 42,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["JavaScript", "React", "Performance", "CSS", "Node.js"],
    },
    {
        "id": "TM-038",
        "name": "Abhishek Reddy",
        "designation": "Release Engineer",
        "experience": 48,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Jenkins", "Docker", "Python", "AWS", "Git"],
    },
    {
        "id": "TM-039",
        "name": "Ritika Chopra",
        "designation": "Software Testing Lead",
        "experience": 60,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Python", "Selenium", "TestNG", "AWS", "Docker"],
    },
    {
        "id": "TM-040",
        "name": "Siddharth Patel",
        "designation": "Elasticsearch Specialist",
        "experience": 42,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Elasticsearch", "Kibana", "Python", "AWS", "PostgreSQL"],
    },
    {
        "id": "TM-041",
        "name": "Anjali Singh",
        "designation": "Message Queue Engineer",
        "experience": 48,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["RabbitMQ", "Kafka", "Java", "Python", "AWS"],
    },
    {
        "id": "TM-042",
        "name": "Pranav Kumar",
        "designation": "Cache Specialist",
        "experience": 42,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Redis", "Memcached", "Python", "Java", "AWS"],
    },
    {
        "id": "TM-043",
        "name": "Sakshi Reddy",
        "designation": "API Tester",
        "experience": 36,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["REST API", "Postman", "Python", "Selenium", "AWS"],
    },
    {
        "id": "TM-044",
        "name": "Manoj Singh",
        "designation": "ORM Specialist",
        "experience": 48,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["SQLAlchemy", "ORM", "Python", "PostgreSQL", "AWS"],
    },
    {
        "id": "TM-045",
        "name": "Disha Patel",
        "designation": "Monitoring Specialist",
        "experience": 42,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Prometheus", "Grafana", "ELK Stack", "AWS", "Python"],
    },
    {
        "id": "TM-046",
        "name": "Aryan Verma",
        "designation": "Container Orchestration Specialist",
        "experience": 48,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Kubernetes", "Docker", "Helm", "AWS", "Python"],
    },
    {
        "id": "TM-047",
        "name": "Prachi Singh",
        "designation": "Load Balancing Specialist",
        "experience": 42,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Nginx", "HAProxy", "AWS", "Linux", "Python"],
    },
    {
        "id": "TM-048",
        "name": "Vishal Kumar",
        "designation": "Encryption Specialist",
        "experience": 54,
        "location": "Bangalore",
        "work_type": "hybrid",
        "skills": ["Cryptography", "Python", "Java", "AWS", "Linux"],
    },
    {
        "id": "TM-049",
        "name": "Neetu Reddy",
        "designation": "Logging Engineer",
        "experience": 42,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["ELK Stack", "Logstash", "Python", "AWS", "Docker"],
    },
    {
        "id": "TM-050",
        "name": "Aditya Patel",
        "designation": "Staff Engineer",
        "experience": 120,
        "location": "Remote",
        "work_type": "wfh",
        "skills": ["Python", "Java", "AWS", "Kubernetes", "Leadership"],
    },
]


def generate_embedding_vector(team_member: dict) -> np.ndarray:
    """Generate a deterministic embedding vector based on skills and designation.
    
    In production, this would use OpenAI's embedding API.
    For now, we generate a mock 3072-dimensional vector based on skill hash.
    """
    seed = hash(f"{team_member['designation']}:{','.join(sorted(team_member['skills']))}")
    rng = np.random.RandomState(seed % (2**31))
    return rng.randn(3072).astype(np.float32)


def seed_candidates(db: Session):
    """Seed 50 candidate records with embeddings."""
    print("Starting candidate seeding...")
    
    # Get all skills from database
    skills = db.query(SkillMaster).all()
    skill_map = {skill.skill_name.lower(): skill.skill_id for skill in skills}
    
    print(f"Found {len(skill_map)} skills in database: {list(skill_map.keys())}")
    
    created_count = 0
    skipped_count = 0
    
    for candidate in CANDIDATES:
        try:
            # Check if candidate already exists
            existing = db.query(TeamMember).filter(
                TeamMember.team_member_id == candidate["id"]
            ).first()
            
            if existing:
                print(f"⚠️  Candidate {candidate['id']} already exists, skipping")
                skipped_count += 1
                continue
            
            # Create team member
            team_member = TeamMember(
                team_member_id=candidate["id"],
                designation=candidate["designation"],
                experience_in_months=candidate["experience"],
                base_location=candidate["location"],
                work_type=candidate["work_type"],
                is_active=True,
                profile_type="candidate",
            )
            db.add(team_member)
            db.flush()  # Flush to ensure team_member_id is available
            
            # Assign skills to candidate
            for skill_name in candidate["skills"]:
                skill_id = skill_map.get(skill_name.lower())
                
                if skill_id:
                    team_member_skill = TeamMemberSkill(
                        team_member_id=candidate["id"],
                        skill_id=skill_id,
                        rating=4 + (hash(skill_name) % 2),  # Rating 4 or 5
                        experience_in_months=candidate["experience"],
                    )
                    db.add(team_member_skill)
                else:
                    print(f"  ⚠️  Skill '{skill_name}' not found for {candidate['id']}")
            
            # Generate and store embedding
            embedding_vector = generate_embedding_vector(candidate)
            
            # Insert embedding using raw SQL (SQLAlchemy doesn't support pgvector inserts well)
            embedding_list = embedding_vector.tolist()
            embedding_str = f"[{','.join(str(x) for x in embedding_list)}]"
            
            insert_sql = text("""
                INSERT INTO team_member_embeddings 
                (team_member_id, embedding, profile_text, metadata, created_at)
                VALUES (:team_member_id, :embedding, :profile_text, :metadata, :created_at)
            """)
            
            profile_text = f"{candidate['designation']} with skills: {', '.join(candidate['skills'])}"
            metadata_json = json.dumps({
                "location": candidate["location"],
                "work_type": candidate["work_type"],
                "skills": candidate["skills"],
            })
            
            db.execute(
                insert_sql,
                {
                    "team_member_id": candidate["id"],
                    "embedding": embedding_str,
                    "profile_text": profile_text,
                    "metadata": metadata_json,
                    "created_at": datetime.utcnow(),
                },
            )
            
            created_count += 1
            print(f"✅ Created {candidate['id']}: {candidate['designation']} with {len(candidate['skills'])} skills")
            
        except Exception as e:
            print(f"❌ Error creating candidate {candidate['id']}: {str(e)}")
            db.rollback()
            continue
    
    # Commit all changes
    try:
        db.commit()
        print(f"\n✅ Successfully seeded {created_count} candidates")
        print(f"⚠️  Skipped {skipped_count} existing candidates")
        
        # Verify
        total_candidates = db.query(TeamMember).count()
        total_embeddings = db.execute(text("SELECT COUNT(*) FROM team_member_embeddings")).scalar()
        
        print(f"\n📊 Database Summary:")
        print(f"   Total candidates: {total_candidates}")
        print(f"   Total embeddings: {total_embeddings}")
        
    except Exception as e:
        print(f"❌ Error committing changes: {str(e)}")
        db.rollback()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_candidates(db)
    finally:
        db.close()
