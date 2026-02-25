-- Clean candidate related tables for re-import
BEGIN;

-- Disable triggers to avoid constraint issues during bulk truncate if needed, 
-- but TRUNCATE CASCADE is cleaner.
TRUNCATE TABLE 
    team_member_skill, 
    team_member_allocation, 
    team_member_team_member_skill_certification, 
    team_member_embeddings, 
    team_member 
CASCADE;

-- Optionally clear ingestion logs if a full fresh start is desired
TRUNCATE TABLE 
    ingestion_audit_log, 
    ingestion_batch_state 
RESTART IDENTITY;

COMMIT;
