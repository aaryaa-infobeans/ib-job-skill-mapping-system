import sys
import os
from datetime import datetime, timedelta

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from app.db.session import SessionLocal
from app.db.models.models import TeamMember, TeamMemberSkill, SkillCertification, SkillMaster
from sqlalchemy import text

# Mapping from team_member.profile_type to jd_certification_requirements.jd_type
PROFILE_TO_JD_TYPE = {
    'developer': ['Backend Engineer', 'Full Stack Engineer'],
    'lead': ['AI Engineer', 'Cloud Engineer'],
    'qa': ['DevOps Engineer'],
    'pm': ['Data Engineer']
}

# Mapping from certification (from jd_certification_requirements) to skill_id (from skill_master)
CERT_TO_SKILL = {
    'AWS ML': 'aws',
    'Azure AI': 'azure',
    'GCP ML': 'amazon-web-services', # Fallback to AWS if GCP missing for test
    'AWS SA': 'aws',
    'Azure Admin': 'azure',
    'AWS DevOps': 'aws',
    'Oracle Java': 'spring-mvc', # Fallback to spring-mvc if java not found
    'Spring Certification': 'spring-mvc',
    'AWS Developer': 'aws',
    'Azure Developer': 'azure',
    'Kubernetes CKA': 'kubernetes',
    'AWS Data Analytics': 'aws',
    'GCP Data Engineering': 'amazon-web-services'
}

def seed_certifications():
    db = SessionLocal()
    try:
        # 1. Fetch certification requirements
        result = db.execute(text("SELECT jd_type, certification FROM jd_certification_requirements"))
        requirements = result.fetchall()
        
        # 2. Group certifications by jd_type
        cert_map = {}
        for jd_type, cert in requirements:
            if jd_type not in cert_map:
                cert_map[jd_type] = []
            cert_map[jd_type].append(cert)
        
        # 3. Fetch all team members
        team_members = db.query(TeamMember).all()
        
        cert_count = 0
        skill_count = 0
        
        for tm in team_members:
            profile_type = tm.profile_type
            if not profile_type or profile_type not in PROFILE_TO_JD_TYPE:
                continue
            
            # Get matching JD types for this profile type
            matching_jd_types = PROFILE_TO_JD_TYPE[profile_type]
            
            for jd_type in matching_jd_types:
                if jd_type not in cert_map:
                    continue
                    
                allowed_certs = cert_map[jd_type]
                
                for cert_name in allowed_certs:
                    skill_id = CERT_TO_SKILL.get(cert_name)
                    if not skill_id:
                        continue
                    
                    # Check if skill exists in skill_master
                    skill_exists = db.query(SkillMaster).filter(SkillMaster.skill_id == skill_id).first()
                    if not skill_exists:
                        # If the specific mapping doesn't exist, try to find a fallback match in the DB
                        if 'aws' in skill_id:
                            skill_id = 'amazon-web-services'
                            skill_exists = db.query(SkillMaster).filter(SkillMaster.skill_id == skill_id).first()
                        
                        if not skill_exists:
                            continue

                    # Ensure team_member_skill entry exists
                    tm_skill = db.query(TeamMemberSkill).filter(
                        TeamMemberSkill.team_member_id == tm.team_member_id,
                        TeamMemberSkill.skill_id == skill_id
                    ).first()
                    
                    if not tm_skill:
                        tm_skill = TeamMemberSkill(
                            team_member_id=tm.team_member_id,
                            skill_id=skill_id,
                            rating=4,
                            experience_in_months=tm.experience_in_months or 24,
                            is_deleted=False
                        )
                        db.add(tm_skill)
                        db.flush() # Ensure tm_skill is added before certification
                        skill_count += 1
                    
                    # Check if certification already exists
                    existing_cert = db.query(SkillCertification).filter(
                        SkillCertification.team_member_id == tm.team_member_id,
                        SkillCertification.skill_id == skill_id,
                        SkillCertification.certificate == cert_name
                    ).first()
                    
                    if not existing_cert:
                        new_cert = SkillCertification(
                            certification_id=f"CERT-{tm.team_member_id}-{skill_id[:10]}-{abs(hash(cert_name)) % 10000}",
                            team_member_id=tm.team_member_id,
                            skill_id=skill_id,
                            certificate=cert_name,
                            issuer="Testing Authority",
                            issued_date=datetime.now().date() - timedelta(days=365),
                            valid_till=datetime.now().date() + timedelta(days=365)
                        )
                        db.add(new_cert)
                        cert_count += 1
        
        db.commit()
        print(f"Successfully added {cert_count} certifications and {skill_count} team member skills.")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding certifications: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_certifications()
