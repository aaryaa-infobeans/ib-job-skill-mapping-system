#!/usr/bin/env python3
"""
Enrich candidate data from resumes.json with Google Drive profile text and random metadata.
"""

import os
import sys
import json
import random
import logging
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add src to path
sys.path.insert(0, "src")

from app.db.session import SessionLocal
from app.db.models.models import (
    TeamMember, 
    TeamMemberSkill, 
    SkillMaster, 
    TeamMemberSkillCertification,
    WorkTypeEnum
)
from app.ai.utils.embedding import EmbeddingAgent
from app.ai.utils.models import EmbeddingResult
from sqlalchemy import text
from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
TOKEN_FILE = "token.json"
RESUMES_FILE = "resumes.json"
SCOPES = ["https://www.googleapis.com/auth/documents.readonly", "https://www.googleapis.com/auth/drive.readonly"]

# Sample Certification Issuers
ISSUERS = ["Microsoft", "AWS", "Google", "Oracle", "Cisco", "Scrum.org", "PMI", "Salesforce"]
CERT_NAMES = ["Certified Professional", "Associate Developer", "Specialist", "Architect", "Master"]

def get_gdocs_service():
    """Builds the Google Docs service."""
    if not os.path.exists(TOKEN_FILE):
        logger.error(f"Token file {TOKEN_FILE} not found.")
        return None
    
    with open(TOKEN_FILE, 'r') as token:
        creds_data = json.load(token)
        # Handle the format in token.json
        creds = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes')
        )
    
    return build('docs', 'v1', credentials=creds)

def extract_doc_id(url: str) -> Optional[str]:
    """Extracts the document ID from a Google Docs URL."""
    if not url or "docs.google.com/document/d/" not in url:
        return None
    try:
        parts = url.split("/d/")
        if len(parts) > 1:
            return parts[1].split("/")[0].split("?")[0]
    except Exception:
        pass
    return None

def read_structural_elements(elements):
    """Recursively reads structural elements from Google Doc."""
    text = ""
    for value in elements:
        if 'paragraph' in value:
            elements = value.get('paragraph').get('elements')
            for entry in elements:
                text_run = entry.get('textRun')
                if text_run:
                    text += text_run.get('content')
        elif 'table' in value:
            table = value.get('table')
            for row in table.get('tableRows'):
                cells = row.get('tableCells')
                for cell in cells:
                    text += read_structural_elements(cell.get('content'))
        elif 'tableOfContents' in value:
            toc = value.get('tableOfContents')
            text += read_structural_elements(toc.get('content'))
    return text

def get_doc_content(service, doc_id: str) -> str:
    """Fetches content of a Google Doc."""
    try:
        doc = service.documents().get(documentId=doc_id).execute()
        doc_content = doc.get('body').get('content')
        return read_structural_elements(doc_content)
    except HttpError as err:
        logger.error(f"An error occurred: {err}")
        return ""

def enrich_candidate(candidate: Dict[str, Any], gdocs_service, embedding_agent: EmbeddingAgent, db: Session):
    """Enriches a single candidate with GDrive text, random certs, and availability."""
    tm_id = candidate.get("team_member_id")
    logger.info(f"Processing candidate {tm_id}: {candidate.get('full_name')}")
    
    # 1. Extract GDrive Text
    profile_url = candidate.get("profile")
    doc_id = extract_doc_id(profile_url)
    gdrive_text = ""
    if doc_id and gdocs_service:
        logger.info(f"  Fetching GDrive content for {tm_id} from {doc_id}...")
        gdrive_text = get_doc_content(gdocs_service, doc_id)
        if gdrive_text:
            logger.info(f"  Successfully fetched {len(gdrive_text)} chars of content.")
    
    # 2. Random Certifications
    certs = []
    # Add 1-2 random certs for 50% of candidates
    if random.random() > 0.5:
        skills = candidate.get("skills", [])
        if skills:
            num_certs = random.randint(1, 2)
            for _ in range(num_certs):
                skill = random.choice(skills)
                issuer = random.choice(ISSUERS)
                cert_name = f"{issuer} {random.choice(CERT_NAMES)} for {skill.get('name')}"
                issued_date = date.today() - timedelta(days=random.randint(100, 1000))
                expiry_date = issued_date + timedelta(days=random.randint(365, 1095))
                certs.append({
                    "skill_id": skill.get("skill_id"),
                    "certificate": cert_name,
                    "issuer": issuer,
                    "issued_date": issued_date,
                    "valid_till": expiry_date
                })
    
    # 3. Availability is already in resumes.json, but let's make sure it's usable
    # We'll use the one from JSON.
    
    # 4. Construct Rich Profile Text
    # Format: Designation + Location + Work Mode + Experience + Skills + Certifications + GDrive Content
    skills_str = ", ".join([s.get("name") for s in candidate.get("skills", [])])
    certs_str = ", ".join([c.get("certificate") for c in certs])
    
    rich_text_parts = [
        f"Designation: {candidate.get('designation')}",
        f"Location: {candidate.get('base_location')}",
        f"Work Mode: {candidate.get('work-mode')}",
        f"Experience: {candidate.get('experience_in_months')} months",
        f"Skills: {skills_str}"
    ]
    if certs_str:
        rich_text_parts.append(f"Certifications: {certs_str}")
    
    if gdrive_text:
        rich_text_parts.append(f"Resume Content: {gdrive_text}")
    
    profile_text = "\n".join(rich_text_parts)
    
    # 5. Generate Embedding
    logger.info(f"  Generating embedding for {tm_id}...")
    try:
        # Using the now public embed_text method
        embedding_vec = embedding_agent.embed_text(profile_text)
    except Exception as e:
        logger.error(f"  Failed to generate embedding for {tm_id}: {e}")
        embedding_vec = None

    # 6. Database Upsert
    try:
        # Team Member
        existing_tm = db.query(TeamMember).filter(TeamMember.team_member_id == tm_id).first()
        if not existing_tm:
            existing_tm = TeamMember(team_member_id=tm_id)
            db.add(existing_tm)
        
        existing_tm.designation = candidate.get("designation")
        existing_tm.profile_type = candidate.get("profile_type")
        existing_tm.is_active = candidate.get("team_member_status") == "active"
        existing_tm.experience_in_months = candidate.get("experience_in_months")
        existing_tm.base_location = candidate.get("base_location")
        try:
            existing_tm.work_type = WorkTypeEnum(candidate.get("work-mode"))
        except:
            existing_tm.work_type = None
        existing_tm.profile_url = profile_url
        
        db.flush()
        
        # Skills
        # First remove old skills to ensure sync
        db.execute(text("DELETE FROM team_member_skill WHERE team_member_id = :id"), {"id": tm_id})
        for skill in candidate.get("skills", []):
            tm_skill = TeamMemberSkill(
                team_member_id=tm_id,
                skill_id=skill.get("skill_id"),
                rating=skill.get("rating"),
                experience_in_months=skill.get("experience_in_months")
            )
            db.add(tm_skill)
        
        db.flush()
        
        # Certifications
        # First remove old certs
        db.execute(text("DELETE FROM team_member_skill_certification WHERE team_member_id = :id"), {"id": tm_id})
        for cert in certs:
            tm_cert = TeamMemberSkillCertification(
                team_member_id=tm_id,
                skill_id=cert["skill_id"],
                certificate=cert["certificate"],
                issuer=cert["issuer"],
                issued_date=cert["issued_date"],
                valid_till=cert["valid_till"]
            )
            db.add(tm_cert)
        
        # Embedding
        if embedding_vec is not None:
            # Upsert into team_member_embeddings
            # SQLAlchemy doesn't support pgvector well in models without specific extensions, 
            # so we use raw SQL as in the seed script
            db.execute(text("DELETE FROM team_member_embeddings WHERE team_member_id = :id"), {"id": tm_id})
            
            embedding_str = f"[{','.join(str(x) for x in embedding_vec)}]"
            metadata_json = json.dumps({
                "location": candidate.get("base_location"),
                "work_type": candidate.get("work-mode"),
                "availability": candidate.get("availability"),
                "certs": [c["certificate"] for c in certs]
            })
            
            insert_sql = text("""
                INSERT INTO team_member_embeddings 
                (team_member_id, embedding, profile_text, metadata, created_at)
                VALUES (:team_member_id, :embedding, :profile_text, :metadata, :created_at)
            """)
            
            db.execute(
                insert_sql,
                {
                    "team_member_id": tm_id,
                    "embedding": embedding_str,
                    "profile_text": profile_text,
                    "metadata": metadata_json,
                    "created_at": datetime.utcnow(),
                },
            )
        
        db.commit()
        logger.info(f"✅ Successfully enriched and upserted candidate {tm_id}")
    except Exception as e:
        logger.error(f"❌ Error upserting candidate {tm_id}: {e}")
        db.rollback()

def main():
    if not os.path.exists(RESUMES_FILE):
        logger.error(f"Resumes file {RESUMES_FILE} not found.")
        return

    with open(RESUMES_FILE, 'r') as f:
        data = json.load(f)
    
    team_members = data.get("team_members", [])
    logger.info(f"Loaded {len(team_members)} team members from {RESUMES_FILE}")
    
    gdocs_service = get_gdocs_service()
    embedding_agent = EmbeddingAgent(logger=logger)
    db = SessionLocal()
    
    try:
        # Pre-fetch all valid skill IDs
        valid_skill_ids = {s.skill_id for s in db.query(SkillMaster).all()}
        logger.info(f"Loaded {len(valid_skill_ids)} valid skill IDs from SkillMaster")
        
        for tm in team_members:
            # Filter skills to only include those that exist in SkillMaster
            original_skills = tm.get("skills", [])
            tm["skills"] = [s for s in original_skills if s.get("skill_id") in valid_skill_ids]
            
            if len(tm["skills"]) < len(original_skills):
                logger.warning(f"  Filtered out {len(original_skills) - len(tm['skills'])} missing skills for {tm.get('team_member_id')}")
            
            enrich_candidate(tm, gdocs_service, embedding_agent, db)
    finally:
        db.close()

if __name__ == "__main__":
    main()
