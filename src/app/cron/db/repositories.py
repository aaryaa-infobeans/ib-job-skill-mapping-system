"""
Database repositories for batch ingestion operations.

Provides UPSERT operations for team member data with transaction support
and natural key conflict handling.
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.cron.db.metadata import (
    category_master,
    skill_master,
    team_member,
    team_member_skill,
    team_member_allocation,
    team_member_skill_certification,
    ingestion_batch_state,
    ingestion_audit_log,
)


def _parse_date(value) -> Optional[date]:
    """Convert a string like '2026-01-29' to a date object, or return None."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


class TeamMemberRepository:
    """
    Repository for team member-related UPSERT operations.
    
    Handles natural key conflicts and foreign key relationships across:
    - category_master
    - skill_master
    - team_member
    - team_member_skill
    - team_member_allocation
    - team_member_skill_certification
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session for database operations
        """
        self.session = session
    
    async def upsert_category(self, category_name: str) -> int:
        """
        Insert or retrieve category by name.
        
        Uses natural key (category_name) for conflict detection.
        
        Args:
            category_name: Name of the category (unique)
        
        Returns:
            category_id: Primary key of category
        
        Raises:
            ValueError: If category_name is empty or invalid
        """
        if not category_name or not category_name.strip():
            raise ValueError("category_name cannot be empty")
        
        category_name = category_name.strip()
        
        # Try to insert, on conflict do nothing (natural key already exists)
        stmt = pg_insert(category_master).values(
            category_name=category_name
        ).on_conflict_do_nothing(
            index_elements=['category_name']
        ).returning(category_master.c.category_id)
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        # If conflict occurred, fetch existing category_id
        if row is None:
            select_stmt = select(category_master.c.category_id).where(
                category_master.c.category_name == category_name
            )
            result = await self.session.execute(select_stmt)
            row = result.fetchone()
        
        if row is None:
            raise RuntimeError(f"Failed to upsert category: {category_name}")
        
        return row[0]
    
    async def upsert_skill(self, skill_name: str, category_id: int) -> str:
        """
        Insert or update skill with generated skill_id from skill_name.
        
        skill_id is derived as: lowercase(skill_name) with special chars replaced by hyphen
        
        Args:
            skill_name: Name of the skill (unique)
            category_id: Foreign key to category_master
        
        Returns:
            skill_id: Primary key (derived from skill_name)
        
        Raises:
            ValueError: If skill_name is empty or invalid
        """
        if not skill_name or not skill_name.strip():
            raise ValueError("skill_name cannot be empty")
        
        skill_name = skill_name.strip()
        
        # Generate skill_id: lowercase, replace non-alphanumeric with hyphen, strip leading/trailing hyphens
        skill_id = re.sub(r'[^a-z0-9]+', '-', skill_name.lower()).strip('-')
        
        # Ensure skill_id is not empty after transformation
        if not skill_id:
            raise ValueError(f"Invalid skill_name generates empty skill_id: {skill_name}")
        
        # Truncate to 50 chars (database constraint)
        skill_id = skill_id[:50]
        
        # UPSERT: on conflict update category_id
        stmt = pg_insert(skill_master).values(
            skill_id=skill_id,
            skill_name=skill_name,
            category_id=category_id
        ).on_conflict_do_update(
            index_elements=['skill_id'],
            set_={'category_id': category_id}
        ).returning(skill_master.c.skill_id)
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if row is None:
            raise RuntimeError(f"Failed to upsert skill: {skill_name}")
        
        return row[0]
    
    async def upsert_team_member(self, member_data: Dict[str, Any]) -> str:
        """
        Insert or update team member record.
        
        Maps external API fields to database schema:
        - work-mode → work_type enum
        - profile_url (or legacy 'profile') → profile_url
        - team_member_status (active/inactive) → is_active boolean
        
        Args:
            member_data: Dict with keys:
                - team_member_id (required)
                - designation
                - profile_type
                - team_member_status
                - experience_in_months
                - base_location
                - work-mode
                - profile_url (or 'profile')
        
        Returns:
            team_member_id: Primary key
        
        Raises:
            ValueError: If team_member_id is missing
        """
        team_member_id = member_data.get('team_member_id')
        if not team_member_id:
            raise ValueError("team_member_id is required")
        team_member_id = str(team_member_id)

        # Map external API fields to database schema
        work_mode = member_data.get('work-mode', '').lower()
        _work_mode_map = {'hybrid': 'hybrid', 'remote': 'wfh', 'wfh': 'wfh', 'office': 'wfo', 'wfo': 'wfo'}
        work_type = _work_mode_map.get(work_mode)
        
        status = member_data.get('team_member_status', '').lower()
        is_active = status == 'active'
        
        values = {
            'team_member_id': team_member_id,
            'designation': member_data.get('designation'),
            'profile_type': member_data.get('profile_type'),
            'is_active': is_active,
            'experience_in_months': member_data.get('experience_in_months'),
            'base_location': member_data.get('base_location'),
            'work_type': work_type,
            'profile_url': member_data.get('profile_url') or member_data.get('profile'),
        }
        
        # UPSERT: on conflict update all fields
        stmt = pg_insert(team_member).values(**values).on_conflict_do_update(
            index_elements=['team_member_id'],
            set_={
                'designation': values['designation'],
                'profile_type': values['profile_type'],
                'is_active': values['is_active'],
                'experience_in_months': values['experience_in_months'],
                'base_location': values['base_location'],
                'work_type': values['work_type'],
                'profile_url': values['profile_url'],
            }
        ).returning(team_member.c.team_member_id)
        
        result = await self.session.execute(stmt)
        row = result.fetchone()
        
        if row is None:
            raise RuntimeError(f"Failed to upsert team_member: {team_member_id}")
        
        return row[0]
    
    async def upsert_team_member_skills(
        self,
        team_member_id: str,
        skills: List[Dict[str, Any]],
        category_id: int
    ) -> None:
        """
        Insert or update team member skills (many-to-many relationship).
        
        Handles:
        - New skills: insert
        - Existing skills: update rating/experience
        - Deleted skills: mark is_deleted=True
        
        Args:
            team_member_id: Foreign key to team_member
            skills: List of dicts with keys:
                - skill_name (required)
                - rating
                - experience_in_months
                - is_deleted (optional, default False)
            category_id: Category for upserting skills
        
        Raises:
            ValueError: If team_member_id or skills is invalid
        """
        if not team_member_id:
            raise ValueError("team_member_id is required")
        
        if not skills:
            return  # No skills to process
        
        for skill_data in skills:
            skill_name = skill_data.get('skill_name')
            if not skill_name:
                continue  # Skip invalid skill entries
            
            # Ensure skill exists in skill_master
            skill_id = await self.upsert_skill(skill_name, category_id)
            
            is_deleted = skill_data.get('is_deleted', False)
            
            values = {
                'team_member_id': team_member_id,
                'skill_id': skill_id,
                'rating': skill_data.get('rating'),
                'experience_in_months': skill_data.get('experience_in_months'),
                'is_deleted': is_deleted,
            }
            
            # UPSERT: on conflict update rating, experience, is_deleted
            stmt = pg_insert(team_member_skill).values(**values).on_conflict_do_update(
                index_elements=['team_member_id', 'skill_id'],
                set_={
                    'rating': values['rating'],
                    'experience_in_months': values['experience_in_months'],
                    'is_deleted': values['is_deleted'],
                }
            )
            
            await self.session.execute(stmt)
    
    async def upsert_allocations(
        self,
        team_member_id: str,
        allocations: List[Dict[str, Any]]
    ) -> None:
        """
        Insert or update team member project allocations.
        
        Handles allocation updates including billable status and soft deletes.
        
        Args:
            team_member_id: Foreign key to team_member
            allocations: List of dicts with keys:
                - project_id (required)
                - allocation_percentage
                - start_date
                - end_date
                - billable
                - is_deleted (optional, default False)
        
        Raises:
            ValueError: If team_member_id or allocations is invalid
        """
        if not team_member_id:
            raise ValueError("team_member_id is required")
        
        if not allocations:
            return  # No allocations to process
        
        for alloc_data in allocations:
            project_id = alloc_data.get('project_id')
            if not project_id:
                continue  # Skip invalid allocation entries
            
            is_deleted = alloc_data.get('is_deleted', False)
            
            values = {
                'team_member_id': team_member_id,
                'project_id': project_id,
                'allocation_percentage': alloc_data.get('allocation_percentage'),
                'start_date': _parse_date(alloc_data.get('start_date')),
                'end_date': _parse_date(alloc_data.get('end_date')),
                'billable': alloc_data.get('billable'),
                'is_deleted': is_deleted,
            }
            
            # UPSERT: on conflict update all fields
            stmt = pg_insert(team_member_allocation).values(**values).on_conflict_do_update(
                index_elements=['team_member_id', 'project_id'],
                set_={
                    'allocation_percentage': values['allocation_percentage'],
                    'start_date': values['start_date'],
                    'end_date': values['end_date'],
                    'billable': values['billable'],
                    'is_deleted': values['is_deleted'],
                }
            )
            
            await self.session.execute(stmt)
    
    async def upsert_certifications(
        self,
        team_member_id: str,
        certifications: List[Dict[str, Any]],
        category_id: int
    ) -> None:
        """
        Insert or update skill certifications.
        
        Handles array of certifications with skill relationships.
        
        Args:
            team_member_id: Foreign key to team_member
            certifications: List of dicts with keys:
                - certification_id (optional, for updates)
                - skill_name (required)
                - certificate
                - issuer
                - issued_date
                - valid_till
            category_id: Category for upserting skills
        
        Raises:
            ValueError: If team_member_id or certifications is invalid
        """
        if not team_member_id:
            raise ValueError("team_member_id is required")
        
        if not certifications:
            return  # No certifications to process
        
        for cert_data in certifications:
            skill_name = cert_data.get('skill_name')
            if not skill_name:
                continue  # Skip invalid certification entries
            
            # Ensure skill exists in skill_master
            skill_id = await self.upsert_skill(skill_name, category_id)
            
            certification_id = cert_data.get('certification_id')
            
            values = {
                'certification_id': certification_id,
                'team_member_id': team_member_id,
                'skill_id': skill_id,
                'certificate': cert_data.get('certificate'),
                'issuer': cert_data.get('issuer'),
                'issued_date': _parse_date(cert_data.get('issued_date')),
                'valid_till': _parse_date(cert_data.get('valid_till')),
            }
            
            if certification_id:
                # Update existing certification by certification_id
                stmt = update(team_member_skill_certification).where(
                    team_member_skill_certification.c.certification_id == certification_id
                ).values(**values)
            else:
                # Insert new certification (no natural key, so simple insert)
                stmt = insert(team_member_skill_certification).values(**values)
            
            await self.session.execute(stmt)


class BatchStateRepository:
    """
    Repository for ingestion batch state and audit log operations.
    
    Manages:
    - ingestion_batch_state (batch processing state)
    - ingestion_audit_log (audit trail)
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session for database operations
        """
        self.session = session
    
    async def initialize_batch(
        self,
        batch_id: str,
        correlation_id: str,
        total_records: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize a new batch processing state.
        
        Args:
            batch_id: Unique batch identifier (primary key)
            correlation_id: External correlation ID for tracing
            total_records: Total number of records in batch
            metadata: Optional JSON metadata
        
        Raises:
            ValueError: If batch_id or correlation_id is missing
        """
        if not batch_id:
            raise ValueError("batch_id is required")
        if not correlation_id:
            raise ValueError("correlation_id is required")
        
        values = {
            'batch_id': batch_id,
            'correlation_id': correlation_id,
            'status': 'PENDING',
            'total_records': total_records,
            'processed_records': 0,
            'failed_records': 0,
            'started_at': datetime.utcnow(),
            'metadata': metadata or {},
        }
        
        stmt = pg_insert(ingestion_batch_state).values(**values).on_conflict_do_nothing(
            index_elements=['batch_id']
        )
        await self.session.execute(stmt)
        
        # Audit log entry for initialization
        await self.audit_log(
            correlation_id=correlation_id,
            event_type='BATCH_INITIALIZED',
            status='PENDING',
            message=f'Batch {batch_id} initialized with {total_records} records',
            event_details={'batch_id': batch_id, 'total_records': total_records}
        )
    
    async def update_batch_status(
        self,
        batch_id: str,
        status: str,
        processed_records: Optional[int] = None,
        failed_records: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update batch processing status.
        
        Args:
            batch_id: Batch identifier
            status: New status (PROCESSING, SUCCESS, FAILED)
            processed_records: Number of successfully processed records
            failed_records: Number of failed records
            error_message: Error message if status is FAILED
        
        Raises:
            ValueError: If batch_id is missing
        """
        if not batch_id:
            raise ValueError("batch_id is required")
        
        values = {'status': status}
        
        if processed_records is not None:
            values['processed_records'] = processed_records
        
        if failed_records is not None:
            values['failed_records'] = failed_records
        
        if error_message is not None:
            values['error_message'] = error_message
        
        if status in ['SUCCESS', 'FAILED']:
            values['completed_at'] = datetime.utcnow()
        
        stmt = update(ingestion_batch_state).where(
            ingestion_batch_state.c.batch_id == batch_id
        ).values(**values)
        
        await self.session.execute(stmt)
        
        # Retrieve correlation_id for audit log
        select_stmt = select(ingestion_batch_state.c.correlation_id).where(
            ingestion_batch_state.c.batch_id == batch_id
        )
        result = await self.session.execute(select_stmt)
        row = result.fetchone()
        
        if row:
            correlation_id = row[0]
            await self.audit_log(
                correlation_id=correlation_id,
                event_type='BATCH_STATUS_UPDATED',
                status=status,
                message=f'Batch {batch_id} status updated to {status}',
                event_details={
                    'batch_id': batch_id,
                    'processed_records': processed_records,
                    'failed_records': failed_records,
                    'error_message': error_message,
                }
            )
    
    async def get_failed_batches(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve batches with FAILED status for retry.
        
        Args:
            limit: Maximum number of failed batches to return
        
        Returns:
            List of dicts with batch details (batch_id, correlation_id, error_message, etc.)
        """
        stmt = select(ingestion_batch_state).where(
            ingestion_batch_state.c.status == 'FAILED'
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        
        batches = []
        for row in rows:
            batches.append({
                'batch_id': row.batch_id,
                'correlation_id': row.correlation_id,
                'status': row.status,
                'total_records': row.total_records,
                'processed_records': row.processed_records,
                'failed_records': row.failed_records,
                'started_at': row.started_at,
                'completed_at': row.completed_at,
                'error_message': row.error_message,
                'metadata': row.metadata,
            })
        
        return batches
    
    async def audit_log(
        self,
        correlation_id: str,
        event_type: str,
        status: str,
        message: str,
        event_details: Optional[Dict[str, Any]] = None,
        severity: Optional[str] = None,
        source: Optional[str] = None
    ) -> None:
        """
        Log an audit event.
        
        Args:
            correlation_id: External correlation ID for tracing
            event_type: Type of event (BATCH_INITIALIZED, BATCH_STATUS_UPDATED, etc.)
            status: Status at time of event
            message: Human-readable message
            event_details: Optional JSON event details
            severity: Optional severity level (INFO, WARNING, ERROR)
            source: Optional source system/component
        
        Raises:
            ValueError: If correlation_id is missing
        """
        if not correlation_id:
            raise ValueError("correlation_id is required")
        
        # Look up batch_id from correlation_id (optional, may not exist for non-batch events)
        select_stmt = select(ingestion_batch_state.c.batch_id).where(
            ingestion_batch_state.c.correlation_id == correlation_id
        )
        result = await self.session.execute(select_stmt)
        row = result.fetchone()
        batch_id = row[0] if row else None
        
        values = {
            'batch_id': batch_id,
            'correlation_id': correlation_id,
            'event_type': event_type,
            'event_details': {**(event_details or {}), 'status': status, 'message': message},
            'timestamp': datetime.utcnow(),
            'severity': severity,
            'source': source,
        }
        
        stmt = insert(ingestion_audit_log).values(**values)
        await self.session.execute(stmt)


# ---------------------------------------------------------------------------
# CR-EMB-002: Embedding upsert (TASK-EMB-033)
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field
from typing import Optional as _Opt
import numpy as np


@dataclass
class EmbeddingPayload:
    """Fields written by the embedding pipeline to team_member_embeddings."""

    member_id: str
    resume_embedding: _Opt[list] = None          # list[float] length 768
    skills_embedding: _Opt[list] = None
    certifications_embedding: _Opt[list] = None
    embedding: _Opt[list] = None                  # legacy weighted average
    resume_text: _Opt[str] = None
    skills_text: _Opt[str] = None
    certifications_text: _Opt[str] = None
    embedding_model: str = "embedding-gemma-300m"
    content_hash: _Opt[str] = None
    resume_fetched_at: _Opt[object] = None        # datetime
    embedding_updated_at: _Opt[object] = None     # datetime
    pii_scrubbed: bool = False
    scrubbed_at: _Opt[object] = None              # datetime


class EmbeddingRepository:
    """
    Sync SQLAlchemy repository for embedding upserts.

    Uses raw SQLAlchemy Core INSERT ... ON CONFLICT DO UPDATE so it works
    with the sync Session used by the cron embedding phase.
    """

    def __init__(self, session) -> None:
        self.session = session

    def upsert_team_member_embeddings(self, payload: "EmbeddingPayload") -> None:
        """
        Insert or update embedding columns for a team member.

        Columns intentionally NOT touched: profile_text, metadata.
        pii_scrubbed and scrubbed_at are set by the embedding phase when the
        PII scrubber runs successfully on the resume text.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy import insert as sa_insert, text as sa_text
        from datetime import datetime

        # Detect dialect first (needed by _to_list)
        bind = self.session.get_bind()
        dialect = bind.dialect.name if bind is not None else "postgresql"

        import json as _json

        def _to_list(arr):
            if arr is None:
                return None
            if isinstance(arr, np.ndarray):
                lst = arr.tolist()
            else:
                lst = list(arr)
            # SQLite doesn't accept Python lists; serialize to JSON string
            if dialect != "postgresql":
                return _json.dumps(lst)
            return lst

        now = datetime.utcnow()
        values = {
            "team_member_id": payload.member_id,
            "resume_embedding": _to_list(payload.resume_embedding),
            "skills_embedding": _to_list(payload.skills_embedding),
            "certifications_embedding": _to_list(payload.certifications_embedding),
            "embedding": _to_list(payload.embedding),
            "resume_text": payload.resume_text,
            "skills_text": payload.skills_text,
            "certifications_text": payload.certifications_text,
            "embedding_model": payload.embedding_model,
            "content_hash": payload.content_hash,
            "resume_fetched_at": payload.resume_fetched_at,
            "embedding_updated_at": payload.embedding_updated_at or now,
            "pii_scrubbed": payload.pii_scrubbed,
            "scrubbed_at": payload.scrubbed_at,
        }

        if dialect == "postgresql":
            from app.db.models.models import TeamMemberEmbedding
            stmt = pg_insert(TeamMemberEmbedding.__table__).values(**values)
            update_cols = {
                k: stmt.excluded[k]
                for k in values
                if k != "team_member_id"
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=["team_member_id"],
                set_=update_cols,
            )
            self.session.execute(stmt)
        else:
            # SQLite / test fallback: plain upsert
            from app.db.models.models import TeamMemberEmbedding
            existing = (
                self.session.query(TeamMemberEmbedding)
                .filter_by(team_member_id=payload.member_id)
                .first()
            )
            if existing is None:
                row = TeamMemberEmbedding(**values)
                self.session.add(row)
            else:
                for k, v in values.items():
                    if k != "team_member_id":
                        setattr(existing, k, v)
