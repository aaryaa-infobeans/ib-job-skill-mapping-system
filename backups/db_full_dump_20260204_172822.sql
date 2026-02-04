-- ========================================================
-- FULL DATABASE DUMP WITH SCHEMA
-- Database: ib_job_skill_mapping
-- Generated: 2026-02-04T17:28:22.773106
-- ========================================================

-- ========================================================
-- TABLE SCHEMAS
-- ========================================================


-- Table: alembic_version

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
)

;

-- Table: auth_clients

CREATE TABLE auth_clients (
	id SMALLSERIAL NOT NULL, 
	client_name VARCHAR(100) NOT NULL, 
	client_code VARCHAR(50) NOT NULL, 
	client_secret_hash VARCHAR(255) NOT NULL, 
	auth_type VARCHAR(10) DEFAULT 'OAUTH'::character varying NOT NULL, 
	is_active BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT auth_clients_pkey PRIMARY KEY (id), 
	CONSTRAINT auth_clients_client_code_key UNIQUE NULLS DISTINCT (client_code)
)

;

-- Table: auth_access_tokens

CREATE TABLE auth_access_tokens (
	id SERIAL NOT NULL, 
	auth_client_id SMALLINT NOT NULL, 
	access_token VARCHAR(255) NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_revoked BOOLEAN DEFAULT false NOT NULL, 
	issued_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT auth_access_tokens_pkey PRIMARY KEY (id), 
	CONSTRAINT auth_access_tokens_auth_client_id_fkey FOREIGN KEY(auth_client_id) REFERENCES auth_clients (id), 
	CONSTRAINT auth_access_tokens_access_token_key UNIQUE NULLS DISTINCT (access_token)
)

;

-- Table: requisition_requests

CREATE TABLE requisition_requests (
	id SERIAL NOT NULL, 
	request_id VARCHAR(64) NOT NULL, 
	auth_client_id SMALLINT NOT NULL, 
	status SMALLINT NOT NULL, 
	client_name VARCHAR(100) NOT NULL, 
	correlation_id VARCHAR(100), 
	received_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	CONSTRAINT requisition_requests_pkey PRIMARY KEY (id), 
	CONSTRAINT requisition_requests_auth_client_id_fkey FOREIGN KEY(auth_client_id) REFERENCES auth_clients (id), 
	CONSTRAINT requisition_requests_status_fkey FOREIGN KEY(status) REFERENCES requisition_status_master (status_id), 
	CONSTRAINT requisition_requests_request_id_key UNIQUE NULLS DISTINCT (request_id)
)

;

-- Table: requisition_status_master

CREATE TABLE requisition_status_master (
	status_id SMALLSERIAL NOT NULL, 
	status_key VARCHAR(40) NOT NULL, 
	status_message VARCHAR(255) NOT NULL, 
	CONSTRAINT requisition_status_master_pkey PRIMARY KEY (status_id), 
	CONSTRAINT requisition_status_master_status_key_key UNIQUE NULLS DISTINCT (status_key)
)

;

-- Table: requisition_detail

CREATE TABLE requisition_detail (
	id SERIAL NOT NULL, 
	requisition_request_id INTEGER NOT NULL, 
	payload_json JSONB NOT NULL, 
	payload_hash CHAR(64) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT requisition_detail_pkey PRIMARY KEY (id), 
	CONSTRAINT requisition_detail_requisition_request_id_fkey FOREIGN KEY(requisition_request_id) REFERENCES requisition_requests (id), 
	CONSTRAINT requisition_detail_payload_hash_key UNIQUE NULLS DISTINCT (payload_hash), 
	CONSTRAINT requisition_detail_requisition_request_id_key UNIQUE NULLS DISTINCT (requisition_request_id)
)

;

-- Table: category_master

CREATE TABLE category_master (
	category_id SMALLSERIAL NOT NULL, 
	category_name VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	CONSTRAINT category_master_pkey PRIMARY KEY (category_id), 
	CONSTRAINT category_master_category_name_key UNIQUE NULLS DISTINCT (category_name)
)

;

-- Table: skill_master

CREATE TABLE skill_master (
	skill_id VARCHAR(50) NOT NULL, 
	skill_name VARCHAR(100) NOT NULL, 
	category_id SMALLINT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	CONSTRAINT skill_master_pkey PRIMARY KEY (skill_id), 
	CONSTRAINT skill_master_category_id_fkey FOREIGN KEY(category_id) REFERENCES category_master (category_id), 
	CONSTRAINT skill_master_skill_name_key UNIQUE NULLS DISTINCT (skill_name)
)

;

-- Table: team_member

CREATE TABLE team_member (
	team_member_id VARCHAR(50) NOT NULL, 
	designation VARCHAR(100), 
	profile_type VARCHAR(50), 
	is_active BOOLEAN DEFAULT true, 
	experience_in_months INTEGER, 
	base_location VARCHAR(100), 
	work_type work_type_enum, 
	profile_url VARCHAR(1024), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	CONSTRAINT team_member_pkey PRIMARY KEY (team_member_id)
)

;

-- Table: team_member_allocation

CREATE TABLE team_member_allocation (
	team_member_id VARCHAR(50) NOT NULL, 
	project_id VARCHAR(50) NOT NULL, 
	allocation_percentage NUMERIC(5, 2), 
	start_date DATE, 
	end_date DATE, 
	billable BOOLEAN, 
	is_deleted BOOLEAN DEFAULT false, 
	CONSTRAINT team_member_allocation_pkey PRIMARY KEY (team_member_id, project_id), 
	CONSTRAINT team_member_allocation_team_member_id_fkey FOREIGN KEY(team_member_id) REFERENCES team_member (team_member_id)
)

;

-- Table: team_member_skill

CREATE TABLE team_member_skill (
	team_member_id VARCHAR(50) NOT NULL, 
	skill_id VARCHAR(50) NOT NULL, 
	rating INTEGER, 
	experience_in_months INTEGER, 
	is_deleted BOOLEAN DEFAULT false, 
	CONSTRAINT team_member_skill_pkey PRIMARY KEY (team_member_id, skill_id), 
	CONSTRAINT team_member_skill_skill_id_fkey FOREIGN KEY(skill_id) REFERENCES skill_master (skill_id), 
	CONSTRAINT team_member_skill_team_member_id_fkey FOREIGN KEY(team_member_id) REFERENCES team_member (team_member_id)
)

;

-- Table: skill_certification

CREATE TABLE skill_certification (
	id SERIAL NOT NULL, 
	certification_id VARCHAR(100), 
	team_member_id VARCHAR(50) NOT NULL, 
	skill_id VARCHAR(50) NOT NULL, 
	certificate VARCHAR(150), 
	issuer VARCHAR(100), 
	issued_date DATE, 
	valid_till DATE, 
	CONSTRAINT skill_certification_pkey PRIMARY KEY (id), 
	CONSTRAINT skill_certification_team_member_id_skill_id_fkey FOREIGN KEY(team_member_id, skill_id) REFERENCES team_member_skill (team_member_id, skill_id)
)

;

-- Table: langgraph_checkpoints

CREATE TABLE langgraph_checkpoints (
	id SERIAL NOT NULL, 
	request_id VARCHAR(64) NOT NULL, 
	node_name VARCHAR(50) NOT NULL, 
	state_json JSONB NOT NULL, 
	token_count INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT langgraph_checkpoints_pkey PRIMARY KEY (id), 
	CONSTRAINT langgraph_checkpoints_request_id_fkey FOREIGN KEY(request_id) REFERENCES requisition_requests (request_id)
)

;

-- Table: team_member_embeddings
