"""
Text assembler for resume, skills, and certifications embedding input.

Three pure functions — no side effects beyond DB reads:
  assemble_resume_text()   — structured header + resume content
  assemble_skills_text()   — JOIN skill_master + category; proficiency labels
  assemble_certifications_text() — JOIN cert + skill; Active/Expired status

TASK-EMB-023 | Plan §6.5 | CR §3.5 | AC-5
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def assemble_resume_text(team_member: Any, resume_content: str) -> str:
    """
    Build structured resume text for embedding.

    Args:
        team_member: ORM TeamMember object (no DB call inside).
        resume_content: Raw resume text (pre-fetched from Google Drive).

    Returns:
        Structured string with header metadata + resume body.
    """
    designation = getattr(team_member, "designation", "") or ""
    location = getattr(team_member, "base_location", "") or ""
    work_type = getattr(team_member, "work_type", None)
    work_type_str = work_type.value if work_type and hasattr(work_type, "value") else str(work_type or "")
    experience_months = getattr(team_member, "experience_in_months", None) or 0

    header_lines = [
        f"Designation: {designation}",
        f"Location: {location}",
        f"Work Type: {work_type_str}",
        f"Experience: {experience_months} months",
        "Resume:",
    ]
    header = "\n".join(header_lines)
    return f"{header}\n{resume_content}"


def assemble_skills_text(member_id: str, db: "Session") -> str:
    """
    Build skills text from DB by JOINing team_member_skill → skill_master.

    Proficiency mapping:
        rating >= 8 → Expert
        rating >= 5 → Intermediate
        else        → Beginner

    Returns:
        Skills text string, or "" if member has no skills.
    """
    from app.db.models.models import TeamMemberSkill, SkillMaster, CategoryMaster

    rows = (
        db.query(
            SkillMaster.skill_name,
            CategoryMaster.category_name,
            TeamMemberSkill.rating,
        )
        .join(SkillMaster, TeamMemberSkill.skill_id == SkillMaster.skill_id)
        .join(CategoryMaster, SkillMaster.category_id == CategoryMaster.category_id)
        .filter(
            TeamMemberSkill.team_member_id == member_id,
            TeamMemberSkill.is_deleted == False,  # noqa: E712
        )
        .all()
    )

    if not rows:
        return ""

    lines = []
    for skill_name, category_name, rating in rows:
        rating = rating or 0
        if rating >= 8:
            proficiency = "Expert"
        elif rating >= 5:
            proficiency = "Intermediate"
        else:
            proficiency = "Beginner"
        lines.append(f"{skill_name} ({category_name}): {proficiency}")

    return "Skills:\n" + "\n".join(lines)


def assemble_certifications_text(member_id: str, db: "Session") -> str:
    """
    Build certifications text from DB.

    Status logic:
        valid_till >= today → Active
        valid_till < today  → Expired
        valid_till is None  → Active (no expiry)

    Returns:
        Certifications text string, or "" if member has no certs.
    """
    from app.db.models.models import TeamMemberSkillCertification, TeamMemberSkill, SkillMaster

    rows = (
        db.query(
            TeamMemberSkillCertification.certificate,
            TeamMemberSkillCertification.issuer,
            TeamMemberSkillCertification.valid_till,
            SkillMaster.skill_name,
        )
        .join(
            TeamMemberSkill,
            (TeamMemberSkillCertification.team_member_id == TeamMemberSkill.team_member_id)
            & (TeamMemberSkillCertification.skill_id == TeamMemberSkill.skill_id),
        )
        .join(SkillMaster, TeamMemberSkill.skill_id == SkillMaster.skill_id)
        .filter(TeamMemberSkillCertification.team_member_id == member_id)
        .all()
    )

    if not rows:
        return ""

    today = date.today()
    lines = []
    for certificate, issuer, valid_till, skill_name in rows:
        if valid_till is None or valid_till >= today:
            status = "Active"
        else:
            status = "Expired"
        cert_name = certificate or "Unknown Certification"
        issuer_str = f" ({issuer})" if issuer else ""
        lines.append(f"{cert_name}{issuer_str} — {skill_name}: {status}")

    return "Certifications:\n" + "\n".join(lines)
