"""Repository for team member operations."""

from datetime import datetime
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.schemas.team_member import (
    AllocationDetails,
    SkillDetails,
    TeamMemberData,
    TeamMemberStatus,
)
from app.db.models.models import (
    CategoryMaster,
    SkillCertification,
    SkillMaster,
    TeamMember,
    TeamMemberAllocation,
    TeamMemberSkill,
    WorkTypeEnum,
)


class TeamMemberRepository:
    """Repository for team member data access."""

    def __init__(self, db: Session):
        self.db = db

    def upsert_team_member(self, member_data: TeamMemberData) -> tuple[bool, TeamMember]:
        """
        Upsert a team member.

        Returns:
            tuple: (was_created, team_member)
        """
        existing = (
            self.db.query(TeamMember)
            .filter(TeamMember.team_member_id == member_data.team_member_id)
            .first()
        )

        # Map work_type string to enum
        work_type = None
        if member_data.work_type:
            work_type_lower = member_data.work_type.lower()
            if work_type_lower in ["wfo", "wfh", "hybrid"]:
                work_type = WorkTypeEnum[work_type_lower]

        if existing:
            # Update existing member
            existing.designation = member_data.designation
            existing.profile_type = member_data.profile_type
            existing.is_active = member_data.team_member_status == TeamMemberStatus.active
            existing.experience_in_months = member_data.experience_in_months
            existing.base_location = member_data.base_location
            existing.work_type = work_type
            existing.profile_url = member_data.profile_url
            self.db.flush()
            return False, existing
        else:
            # Create new member
            new_member = TeamMember(
                team_member_id=member_data.team_member_id,
                designation=member_data.designation,
                profile_type=member_data.profile_type,
                is_active=member_data.team_member_status == TeamMemberStatus.active,
                experience_in_months=member_data.experience_in_months,
                base_location=member_data.base_location,
                work_type=work_type,
                profile_url=member_data.profile_url,
                created_at=datetime.utcnow(),
            )
            self.db.add(new_member)
            self.db.flush()
            return True, new_member

    def upsert_skills(self, team_member_id: str, skills: List[SkillDetails]) -> tuple[int, int]:
        """
        Upsert skills for a team member.

        Returns:
            tuple: (inserted_count, updated_count)
        """
        inserted = 0
        updated = 0

        # Step 1: Normalize all skills (ensure they exist in skill_master and have consistent IDs)
        normalized_skills = []
        for skill_data in skills:
            # Ensure skill exists in skill_master
            skill = (
                self.db.query(SkillMaster)
                .filter(SkillMaster.skill_id == skill_data.skill_id)
                .first()
            )

            if not skill:
                # Check if skill name exists with a different ID (case-insensitive)
                skill_by_name = (
                    self.db.query(SkillMaster)
                    .filter(SkillMaster.skill_name.ilike(skill_data.skill_name))
                    .first()
                )
                
                if skill_by_name:
                    # Use existing skill
                    skill = skill_by_name
                    # Update local skill_id to match db
                    skill_data.skill_id = skill.skill_id
                else:
                    # Create skill if it doesn't exist
                    category = None
                    if skill_data.category:
                        category = (
                            self.db.query(CategoryMaster)
                            .filter(CategoryMaster.category_name == skill_data.category)
                            .first()
                        )
                        if not category:
                            max_id = self.db.query(func.max(CategoryMaster.category_id)).scalar() or 0
                            category = CategoryMaster(
                                category_id=max_id + 1, category_name=skill_data.category
                            )
                            self.db.add(category)
                            self.db.flush()

                    category_id = category.category_id if category else 1
                    skill = SkillMaster(
                        skill_id=skill_data.skill_id,
                        skill_name=skill_data.skill_name,
                        category_id=category_id,
                    )
                    self.db.add(skill)
                    self.db.flush()
            
            normalized_skills.append(skill_data)

        # Step 2: De-duplicate normalized skills by ID
        unique_skills = {}
        for s in normalized_skills:
            # If duplicate, could merge here, but for now take the last one
            unique_skills[s.skill_id] = s

        # Step 3: Upsert team_member_skill
        for skill_data in unique_skills.values():
            existing_skill = (
                self.db.query(TeamMemberSkill)
                .filter(
                    TeamMemberSkill.team_member_id == team_member_id,
                    TeamMemberSkill.skill_id == skill_data.skill_id,
                )
                .first()
            )

            if existing_skill:
                existing_skill.rating = skill_data.rating
                existing_skill.experience_in_months = skill_data.experience_in_months
                existing_skill.is_deleted = skill_data.is_deleted
                updated += 1
            else:
                new_skill = TeamMemberSkill(
                    team_member_id=team_member_id,
                    skill_id=skill_data.skill_id,
                    rating=skill_data.rating,
                    experience_in_months=skill_data.experience_in_months,
                    is_deleted=skill_data.is_deleted,
                )
                self.db.add(new_skill)
                inserted += 1

            # Handle certifications if provided
            if skill_data.certifications:
                for cert in skill_data.certifications:
                    existing_cert = None
                    if cert.certification_id:
                        existing_cert = (
                            self.db.query(SkillCertification)
                            .filter(SkillCertification.certification_id == cert.certification_id)
                            .first()
                        )

                    if existing_cert:
                        existing_cert.certificate = cert.certificate
                        existing_cert.issuer = cert.issuer
                        existing_cert.issued_date = cert.issued_date
                        existing_cert.valid_till = cert.valid_till
                    else:
                        new_cert = SkillCertification(
                            certification_id=cert.certification_id,
                            team_member_id=team_member_id,
                            skill_id=skill_data.skill_id,
                            certificate=cert.certificate,
                            issuer=cert.issuer,
                            issued_date=cert.issued_date,
                            valid_till=cert.valid_till,
                        )
                        self.db.add(new_cert)

        self.db.flush()
        return inserted, updated

    def upsert_allocations(
        self, team_member_id: str, allocations: List[AllocationDetails]
    ) -> tuple[int, int]:
        """
        Upsert allocations for a team member.

        Returns:
            tuple: (inserted_count, updated_count)
        """
        inserted = 0
        updated = 0

        # De-duplicate allocations by project_id
        unique_allocs = {}
        for a in allocations:
            unique_allocs[a.project_id] = a

        for alloc_data in unique_allocs.values():
            existing = (
                self.db.query(TeamMemberAllocation)
                .filter(
                    TeamMemberAllocation.team_member_id == team_member_id,
                    TeamMemberAllocation.project_id == alloc_data.project_id,
                )
                .first()
            )

            if existing:
                existing.allocation_percentage = alloc_data.allocation_percentage
                existing.start_date = alloc_data.start_date
                existing.end_date = alloc_data.end_date
                existing.billable = alloc_data.billable
                existing.is_deleted = alloc_data.is_deleted
                updated += 1
            else:
                new_alloc = TeamMemberAllocation(
                    team_member_id=team_member_id,
                    project_id=alloc_data.project_id,
                    allocation_percentage=alloc_data.allocation_percentage,
                    start_date=alloc_data.start_date,
                    end_date=alloc_data.end_date,
                    billable=alloc_data.billable,
                    is_deleted=alloc_data.is_deleted,
                )
                self.db.add(new_alloc)
                inserted += 1

        self.db.flush()
        return inserted, updated

    def ensure_default_category(self) -> CategoryMaster:
        """Ensure a default category exists."""
        category = (
            self.db.query(CategoryMaster).filter(CategoryMaster.category_name == "General").first()
        )
        if not category:
            # Use category_id=1 for the default category
            category = CategoryMaster(category_id=1, category_name="General")
            self.db.add(category)
            self.db.commit()
        return category
