"""Data generation script for scalability testing.

Generates realistic test data at 5x production scale:
- Team Members: 2,500 (assuming 500 production)
- Skills: 500 unique skills
- Requisitions: 5,000
- Allocations: 10,000+

Usage:
    python scripts/generate_test_data.py --scale 5 --output test_data.sql
    
    # Or load directly to database:
    python scripts/generate_test_data.py --scale 5 --database postgresql://user:pass@localhost/db
"""

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Sample data pools
FIRST_NAMES = [
    "John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa",
    "James", "Maria", "William", "Jennifer", "Richard", "Linda", "Joseph",
    "Patricia", "Thomas", "Elizabeth", "Charles", "Susan", "Daniel", "Jessica",
    "Matthew", "Karen", "Anthony", "Nancy", "Mark", "Betty", "Donald", "Helen"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Kumar",
    "Patel", "Singh"
]

SKILLS = [
    # Programming Languages
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
    "Ruby", "PHP", "Kotlin", "Swift", "Scala", "R", "MATLAB",
    
    # Frameworks & Libraries
    "React", "Angular", "Vue.js", "FastAPI", "Django", "Flask", "Spring Boot",
    "Node.js", "Express.js", "Next.js", "NestJS", ".NET Core", "Ruby on Rails",
    
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
    "DynamoDB", "Oracle", "SQL Server", "Neo4j", "CouchDB",
    
    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Ansible",
    "Jenkins", "GitLab CI", "GitHub Actions", "CircleCI", "ArgoCD",
    
    # Data & AI/ML
    "Apache Spark", "Hadoop", "Airflow", "Kafka", "TensorFlow", "PyTorch",
    "Scikit-learn", "Pandas", "NumPy", "LangChain", "LangGraph", "OpenAI API",
    
    # Others
    "Microservices", "REST API", "GraphQL", "gRPC", "Message Queues",
    "Event-Driven Architecture", "CQRS", "Domain-Driven Design", "Test-Driven Development",
    "Agile", "Scrum", "CI/CD", "Monitoring", "Observability", "Security"
]

DESIGNATIONS = [
    "Junior Developer", "Software Engineer", "Senior Software Engineer",
    "Lead Engineer", "Staff Engineer", "Principal Engineer",
    "Engineering Manager", "Senior Manager", "Director of Engineering",
    "DevOps Engineer", "Senior DevOps Engineer", "SRE", "Data Engineer",
    "Senior Data Engineer", "ML Engineer", "Senior ML Engineer"
]

JOB_TITLES = [
    "Senior Software Engineer", "Full Stack Developer", "Backend Engineer",
    "Frontend Developer", "DevOps Engineer", "Data Engineer", "ML Engineer",
    "Cloud Architect", "Platform Engineer", "Site Reliability Engineer",
    "Security Engineer", "Mobile Developer", "QA Engineer", "Test Automation Engineer"
]

JOB_ROLES = [
    "Backend Developer", "Frontend Developer", "Full Stack Developer",
    "DevOps", "Data Engineering", "ML Engineering", "Architecture",
    "Platform Engineering", "SRE", "Security", "Mobile", "QA"
]

PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
LOCATIONS = ["Bangalore", "Mumbai", "Pune", "Hyderabad", "Remote", "US - Remote", "UK - Remote"]
WORK_MODES = ["Remote", "Hybrid", "On-site"]


def generate_team_members(count: int, start_id: int = 1) -> List[Tuple]:
    """Generate team member records."""
    members = []
    
    for i in range(count):
        member_id = f"TM{start_id + i:06d}"
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email = f"{name.lower().replace(' ', '.')}@example.com"
        designation = random.choice(DESIGNATIONS)
        
        # Primary skills (3-5)
        num_primary = random.randint(3, 5)
        primary_skills = random.sample(SKILLS, num_primary)
        
        # Secondary skills (2-4)
        remaining_skills = [s for s in SKILLS if s not in primary_skills]
        num_secondary = random.randint(2, 4)
        secondary_skills = random.sample(remaining_skills, min(num_secondary, len(remaining_skills)))
        
        total_exp = random.randint(2, 20)
        relevant_exp = random.randint(1, total_exp)
        
        members.append((
            member_id,
            name,
            email,
            designation,
            primary_skills,
            secondary_skills,
            total_exp,
            relevant_exp,
            random.choice([None, None, None, "AWS Certified Developer", "Azure Certified", "GCP Professional"]),
            datetime.now(),
            datetime.now()
        ))
    
    return members


def generate_allocations(team_members: List[Tuple], projects_per_member: int = 2) -> List[Tuple]:
    """Generate project allocations for team members."""
    allocations = []
    allocation_id = 1
    
    for member in team_members:
        member_id = member[0]
        num_projects = random.randint(0, projects_per_member)
        
        for _ in range(num_projects):
            project_id = f"PROJ{random.randint(1, 500):04d}"
            project_name = f"Project {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Phoenix', 'Nova'])}"
            
            allocation_pct = random.choice([25, 50, 75, 100])
            
            start_date = datetime.now() - timedelta(days=random.randint(0, 365))
            end_date = start_date + timedelta(days=random.randint(90, 540))
            
            allocations.append((
                f"ALLOC{allocation_id:06d}",
                member_id,
                project_id,
                project_name,
                allocation_pct,
                start_date.date(),
                end_date.date(),
                datetime.now(),
                datetime.now()
            ))
            allocation_id += 1
    
    return allocations


def generate_requisitions(count: int, start_id: int = 1) -> List[Tuple]:
    """Generate requisition requests."""
    requisitions = []
    
    for i in range(count):
        request_id = f"REQ{start_id + i:06d}"
        correlation_id = f"CORR-{datetime.now().strftime('%Y%m%d')}-{request_id}"
        
        title = random.choice(JOB_TITLES)
        role = random.choice(JOB_ROLES)
        priority = random.choice(PRIORITIES)
        location = random.sample(LOCATIONS, random.randint(1, 3))
        work_mode = random.sample(WORK_MODES, random.randint(1, 2))
        
        # JD text with required skills
        required_skills = random.sample(SKILLS, random.randint(4, 8))
        jd_text = f"We are seeking a {title} for our {role} team. "
        jd_text += f"Required skills: {', '.join(required_skills[:5])}. "
        jd_text += f"Nice to have: {', '.join(required_skills[5:])}. "
        jd_text += f"{random.randint(3, 8)}+ years of experience required."
        
        status = random.choice([1, 2, 3, 4])  # 1=Queued, 2=Processing, 3=Completed, 4=Failed
        
        requisitions.append((
            request_id,
            1,  # auth_client_id
            status,
            correlation_id,
            "Test Client",
            datetime.now(),
            title,
            role,
            priority,
            location,
            work_mode,
            jd_text,
            {"generated": True, "scale_test": True},
            datetime.now(),
            datetime.now()
        ))
    
    return requisitions


def generate_sql_inserts(team_members, allocations, requisitions) -> str:
    """Generate SQL INSERT statements."""
    sql = []
    
    sql.append("-- Generated test data for scalability testing")
    sql.append(f"-- Generated at: {datetime.now().isoformat()}")
    sql.append(f"-- Team Members: {len(team_members)}")
    sql.append(f"-- Allocations: {len(allocations)}")
    sql.append(f"-- Requisitions: {len(requisitions)}")
    sql.append("")
    
    sql.append("BEGIN;")
    sql.append("")
    
    # Team Members
    sql.append("-- Team Members")
    for member in team_members:
        primary_str = "{" + ",".join(f'"{s}"' for s in member[4]) + "}"
        secondary_str = "{" + ",".join(f'"{s}"' for s in member[5]) + "}"
        cert = f"'{member[8]}'" if member[8] else "NULL"
        
        sql.append(
            f"INSERT INTO team_members "
            f"(team_member_id, name, email, designation, primary_skills, secondary_skills, "
            f"total_experience_years, relevant_experience_years, certifications, created_at, updated_at) "
            f"VALUES ('{member[0]}', '{member[1]}', '{member[2]}', '{member[3]}', "
            f"'{primary_str}', '{secondary_str}', {member[6]}, {member[7]}, {cert}, "
            f"'{member[9].isoformat()}', '{member[10].isoformat()}');"
        )
    sql.append("")
    
    # Allocations
    sql.append("-- Project Allocations")
    for alloc in allocations:
        sql.append(
            f"INSERT INTO team_member_allocations "
            f"(allocation_id, team_member_id, project_id, project_name, allocation_percentage, "
            f"start_date, end_date, created_at, updated_at) "
            f"VALUES ('{alloc[0]}', '{alloc[1]}', '{alloc[2]}', '{alloc[3]}', {alloc[4]}, "
            f"'{alloc[5]}', '{alloc[6]}', '{alloc[7].isoformat()}', '{alloc[8].isoformat()}');"
        )
    sql.append("")
    
    # Requisitions
    sql.append("-- Requisition Requests")
    for req in requisitions:
        location_str = "{" + ",".join(f'"{loc}"' for loc in req[9]) + "}"
        work_mode_str = "{" + ",".join(f'"{wm}"' for wm in req[10]) + "}"
        
        # Escape single quotes in text
        jd_text = req[11].replace("'", "''")
        
        sql.append(
            f"INSERT INTO requisition_requests "
            f"(request_id, auth_client_id, status, correlation_id, client_name, received_at, "
            f"title, role, priority, location, work_mode, jd_text, metadata, created_at, updated_at) "
            f"VALUES ('{req[0]}', {req[1]}, {req[2]}, '{req[3]}', '{req[4]}', "
            f"'{req[5].isoformat()}', '{req[6]}', '{req[7]}', '{req[8]}', "
            f"'{location_str}', '{work_mode_str}', '{jd_text}', "
            f"'{str(req[12]).replace(\"'\", '\"')}', '{req[13].isoformat()}', '{req[14].isoformat()}');"
        )
    sql.append("")
    
    sql.append("COMMIT;")
    
    return "\n".join(sql)


def main():
    parser = argparse.ArgumentParser(description="Generate test data for scalability testing")
    parser.add_argument("--scale", type=int, default=5, help="Scale multiplier (default: 5x)")
    parser.add_argument("--output", type=str, help="Output SQL file path")
    parser.add_argument("--database", type=str, help="Database connection string for direct load")
    
    args = parser.parse_args()
    
    # Calculate quantities based on scale
    # Assume production baseline: 500 team members, 1000 requisitions
    base_members = 500
    base_requisitions = 1000
    
    num_members = base_members * args.scale
    num_requisitions = base_requisitions * args.scale
    
    print(f"Generating test data at {args.scale}x scale...")
    print(f"  Team Members: {num_members}")
    print(f"  Requisitions: {num_requisitions}")
    
    # Generate data
    print("Generating team members...")
    team_members = generate_team_members(num_members)
    
    print("Generating allocations...")
    allocations = generate_allocations(team_members)
    print(f"  Generated {len(allocations)} allocations")
    
    print("Generating requisitions...")
    requisitions = generate_requisitions(num_requisitions)
    
    # Generate SQL
    print("Generating SQL...")
    sql_content = generate_sql_inserts(team_members, allocations, requisitions)
    
    if args.output:
        # Write to file
        output_path = Path(args.output)
        output_path.write_text(sql_content)
        print(f"\nSQL written to: {output_path}")
        print(f"Load with: psql -U user -d dbname -f {output_path}")
    
    elif args.database:
        # Load directly to database
        try:
            from sqlalchemy import create_engine, text
            
            print(f"\nConnecting to database...")
            engine = create_engine(args.database)
            
            with engine.connect() as conn:
                print("Executing SQL...")
                conn.execute(text(sql_content))
                conn.commit()
            
            print("✅ Data loaded successfully!")
            
        except ImportError:
            print("❌ Error: sqlalchemy not installed. Install with: pip install sqlalchemy psycopg2-binary")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            sys.exit(1)
    
    else:
        # Print to stdout
        print(sql_content)
    
    print("\n✅ Test data generation complete!")


if __name__ == "__main__":
    main()
