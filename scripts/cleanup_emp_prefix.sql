-- SQL script to remove EMP_ prefix from employee IDs

BEGIN;

-- 1. Drop foreign key constraints
ALTER TABLE team_member_embeddings DROP CONSTRAINT team_member_embeddings_team_member_id_fkey;
ALTER TABLE skill_certification DROP CONSTRAINT skill_certification_team_member_id_skill_id_fkey;
ALTER TABLE team_member_skill DROP CONSTRAINT team_member_skill_team_member_id_fkey;
ALTER TABLE team_member_allocation DROP CONSTRAINT team_member_allocation_team_member_id_fkey;

-- 2. Update IDs in all tables
UPDATE team_member_embeddings SET team_member_id = REPLACE(team_member_id, 'EMP_', '') WHERE team_member_id LIKE 'EMP_%';
UPDATE skill_certification SET team_member_id = REPLACE(team_member_id, 'EMP_', '') WHERE team_member_id LIKE 'EMP_%';
UPDATE team_member_skill SET team_member_id = REPLACE(team_member_id, 'EMP_', '') WHERE team_member_id LIKE 'EMP_%';
UPDATE team_member_allocation SET team_member_id = REPLACE(team_member_id, 'EMP_', '') WHERE team_member_id LIKE 'EMP_%';
UPDATE team_member SET team_member_id = REPLACE(team_member_id, 'EMP_', '') WHERE team_member_id LIKE 'EMP_%';

-- 3. Update langgraph_checkpoints (JSON field)
UPDATE langgraph_checkpoints SET state_json = CAST(REPLACE(state_json::text, 'EMP_', '') AS JSONB) WHERE state_json::text LIKE '%EMP_%';

-- 4. Recreate foreign key constraints
ALTER TABLE team_member_embeddings ADD CONSTRAINT team_member_embeddings_team_member_id_fkey 
    FOREIGN KEY (team_member_id) REFERENCES team_member(team_member_id);
ALTER TABLE team_member_skill ADD CONSTRAINT team_member_skill_team_member_id_fkey 
    FOREIGN KEY (team_member_id) REFERENCES team_member(team_member_id);
ALTER TABLE team_member_allocation ADD CONSTRAINT team_member_allocation_team_member_id_fkey 
    FOREIGN KEY (team_member_id) REFERENCES team_member(team_member_id);
ALTER TABLE skill_certification ADD CONSTRAINT skill_certification_team_member_id_skill_id_fkey 
    FOREIGN KEY (team_member_id, skill_id) REFERENCES team_member_skill(team_member_id, skill_id);

COMMIT;
