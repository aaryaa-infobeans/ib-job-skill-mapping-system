"""
Manually create the team_member_embeddings row for candidate 11274.

Replicates the cron's EmbeddingProcessor._process_member logic WITHOUT the
MCP/PII path:
  - resume_text + resume_embedding  → copied from candidate 10908 (consistent pair)
  - skills_text / certifications_text → assembled via the real text_assembler
  - skills_embedding / certifications_embedding → freshly generated with
    embedding-gemma-300m (the same model/agent the cron uses)
  - embedding (legacy) → weighted average 0.50 resume / 0.30 skills / 0.20 certs
  - content_hash, profile_text, embedding_model → identical to cron formatting

Run:  python -m scripts.dev.embed_11274_manual    (or: python scripts/dev/embed_11274_manual.py)
"""

import hashlib
from datetime import datetime

import numpy as np

from app.db.session import SessionLocal
from app.db.models.models import TeamMemberEmbedding
from app.cron.embedding.text_assembler import (
    assemble_skills_text,
    assemble_certifications_text,
)
from app.cron.db.repositories import EmbeddingRepository, EmbeddingPayload
from app.ai.utils.embedding import get_embedding_agent

SOURCE_ID = "10908"   # copy resume from
TARGET_ID = "11274"   # build embedding for


def _weighted_average(resume, skills, certs):
    """L2-normalized weighted average — mirrors EmbeddingProcessor._weighted_average."""
    available, weights = [], []
    if resume is not None:
        available.append(resume); weights.append(0.50)
    if skills is not None:
        available.append(skills); weights.append(0.30)
    if certs is not None:
        available.append(certs); weights.append(0.20)
    if not available:
        return None
    total_w = sum(weights)
    combined = np.zeros(768, dtype=np.float32)
    for vec, w in zip(available, weights):
        combined += (w / total_w) * np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(combined)
    return combined if norm < 1e-9 else combined / norm


def _compute_hash(resume_text, skills_text, certs_text):
    raw = f"{resume_text}||{skills_text}||{certs_text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main():
    db = SessionLocal()
    try:
        # 1. Pull resume_text + resume_embedding from source candidate
        src = (
            db.query(TeamMemberEmbedding)
            .filter_by(team_member_id=SOURCE_ID)
            .first()
        )
        if src is None:
            raise SystemExit(f"Source {SOURCE_ID} has no embedding row — aborting.")
        resume_text = src.resume_text
        resume_emb = (
            np.array(src.resume_embedding, dtype=np.float32)
            if src.resume_embedding is not None
            else None
        )
        print(f"[1] Copied resume_text ({len(resume_text or '')} chars) and "
              f"resume_embedding ({'present' if resume_emb is not None else 'NULL'}) from {SOURCE_ID}")

        # 2. Assemble skills + cert text for target from DB (same as cron)
        skills_text = assemble_skills_text(TARGET_ID, db)
        certs_text = assemble_certifications_text(TARGET_ID, db)
        print(f"[2] Assembled skills_text ({len(skills_text)} chars), "
              f"certifications_text ({len(certs_text)} chars)")
        print("---- skills_text ----")
        print(skills_text)
        print("---- certifications_text ----")
        print(certs_text)

        # 3. Generate fresh vectors for the NEW skills/cert text
        agent = get_embedding_agent()
        skills_emb = agent.embed_text(skills_text) if skills_text else None
        certs_emb = agent.embed_text(certs_text) if certs_text else None
        print(f"[3] Generated skills_embedding ({'ok' if skills_emb is not None else 'NULL'}), "
              f"certifications_embedding ({'ok' if certs_emb is not None else 'NULL'})")

        # 4. Weighted-average legacy embedding + hash + profile_text
        legacy_emb = _weighted_average(resume_emb, skills_emb, certs_emb)
        new_hash = _compute_hash(resume_text or "", skills_text, certs_text)
        profile_text = f"Skills: {skills_text}\nCertifications: {certs_text}\nResume: {resume_text}"

        # 5. Upsert via the same repository the cron uses
        now = datetime.utcnow()
        payload = EmbeddingPayload(
            member_id=TARGET_ID,
            resume_embedding=resume_emb,
            skills_embedding=skills_emb,
            certifications_embedding=certs_emb,
            embedding=legacy_emb,
            profile_text=profile_text,
            resume_text=resume_text,
            skills_text=skills_text,
            certifications_text=certs_text,
            embedding_model="embedding-gemma-300m",
            content_hash=new_hash,
            resume_fetched_at=now,
            embedding_updated_at=now,
            pii_scrubbed=bool(src.pii_scrubbed),
            scrubbed_at=src.scrubbed_at,
        )
        EmbeddingRepository(db).upsert_team_member_embeddings(payload)
        db.commit()
        print(f"[5] Upserted team_member_embeddings for {TARGET_ID} — committed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
