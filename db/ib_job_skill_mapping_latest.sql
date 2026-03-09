--
-- PostgreSQL database dump
--

\restrict RXuJiDoQL5xh7u7XNfayzeWcBmDdmIVJwhuSehama9FYJF9R6zv1fbXz0q8Bl2O

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg12+1)
-- Dumped by pg_dump version 18.1

-- Started on 2026-03-09 12:12:06

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE IF EXISTS ib_job_skill_mapping;
--
-- TOC entry 3852 (class 1262 OID 24577)
-- Name: ib_job_skill_mapping; Type: DATABASE; Schema: -; Owner: user
--

CREATE DATABASE ib_job_skill_mapping WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'en_US.utf8';


ALTER DATABASE ib_job_skill_mapping OWNER TO "user";

\unrestrict RXuJiDoQL5xh7u7XNfayzeWcBmDdmIVJwhuSehama9FYJF9R6zv1fbXz0q8Bl2O
\connect ib_job_skill_mapping
\restrict RXuJiDoQL5xh7u7XNfayzeWcBmDdmIVJwhuSehama9FYJF9R6zv1fbXz0q8Bl2O

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 2 (class 3079 OID 24780)
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- TOC entry 3853 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- TOC entry 1011 (class 1247 OID 24683)
-- Name: work_type_enum; Type: TYPE; Schema: public; Owner: user
--

CREATE TYPE public.work_type_enum AS ENUM (
    'wfo',
    'wfh',
    'hybrid'
);


ALTER TYPE public.work_type_enum OWNER TO "user";

--
-- TOC entry 375 (class 1255 OID 25217)
-- Name: prevent_pii_audit_modification(); Type: FUNCTION; Schema: public; Owner: user
--

CREATE FUNCTION public.prevent_pii_audit_modification() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF (TG_OP = 'UPDATE' OR TG_OP = 'DELETE') THEN
                RAISE EXCEPTION 'pii_scrub_audit table is immutable - UPDATE/DELETE not permitted (NFR-PII-003)';
            END IF;
            RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.prevent_pii_audit_modification() OWNER TO "user";

--
-- TOC entry 374 (class 1255 OID 25188)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: user
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO "user";

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 215 (class 1259 OID 24578)
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO "user";

--
-- TOC entry 219 (class 1259 OID 24596)
-- Name: auth_access_tokens; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.auth_access_tokens (
    id integer NOT NULL,
    auth_client_id smallint NOT NULL,
    access_token character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    is_revoked boolean DEFAULT false NOT NULL,
    issued_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.auth_access_tokens OWNER TO "user";

--
-- TOC entry 218 (class 1259 OID 24595)
-- Name: auth_access_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.auth_access_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.auth_access_tokens_id_seq OWNER TO "user";

--
-- TOC entry 3854 (class 0 OID 0)
-- Dependencies: 218
-- Name: auth_access_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.auth_access_tokens_id_seq OWNED BY public.auth_access_tokens.id;


--
-- TOC entry 217 (class 1259 OID 24584)
-- Name: auth_clients; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.auth_clients (
    id smallint NOT NULL,
    client_name character varying(100) NOT NULL,
    client_code character varying(50) NOT NULL,
    client_secret_hash character varying(255) NOT NULL,
    auth_type character varying(10) DEFAULT 'OAUTH'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.auth_clients OWNER TO "user";

--
-- TOC entry 216 (class 1259 OID 24583)
-- Name: auth_clients_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.auth_clients_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.auth_clients_id_seq OWNER TO "user";

--
-- TOC entry 3855 (class 0 OID 0)
-- Dependencies: 216
-- Name: auth_clients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.auth_clients_id_seq OWNED BY public.auth_clients.id;


--
-- TOC entry 227 (class 1259 OID 24660)
-- Name: category_master; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.category_master (
    category_id smallint NOT NULL,
    category_name character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.category_master OWNER TO "user";

--
-- TOC entry 226 (class 1259 OID 24659)
-- Name: category_master_category_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.category_master_category_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.category_master_category_id_seq OWNER TO "user";

--
-- TOC entry 3856 (class 0 OID 0)
-- Dependencies: 226
-- Name: category_master_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.category_master_category_id_seq OWNED BY public.category_master.category_id;


--
-- TOC entry 238 (class 1259 OID 24763)
-- Name: ingestion_audit_log; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.ingestion_audit_log (
    id integer NOT NULL,
    batch_id character varying(100) NOT NULL,
    correlation_id character varying(100) NOT NULL,
    event_type character varying(50) NOT NULL,
    event_details jsonb,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    severity character varying(20),
    source character varying(100)
);


ALTER TABLE public.ingestion_audit_log OWNER TO "user";

--
-- TOC entry 237 (class 1259 OID 24762)
-- Name: ingestion_audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.ingestion_audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ingestion_audit_log_id_seq OWNER TO "user";

--
-- TOC entry 3857 (class 0 OID 0)
-- Dependencies: 237
-- Name: ingestion_audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.ingestion_audit_log_id_seq OWNED BY public.ingestion_audit_log.id;


--
-- TOC entry 236 (class 1259 OID 24752)
-- Name: ingestion_batch_state; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.ingestion_batch_state (
    batch_id character varying(100) NOT NULL,
    correlation_id character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    total_records integer,
    processed_records integer,
    failed_records integer,
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at timestamp without time zone,
    error_message text,
    metadata jsonb
);


ALTER TABLE public.ingestion_batch_state OWNER TO "user";

--
-- TOC entry 242 (class 1259 OID 25143)
-- Name: jd_certification_requirements; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.jd_certification_requirements (
    jd_type character varying(255) NOT NULL,
    certification character varying(255) NOT NULL,
    id integer NOT NULL
);


ALTER TABLE public.jd_certification_requirements OWNER TO "user";

--
-- TOC entry 246 (class 1259 OID 25197)
-- Name: jd_certification_requirements_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.jd_certification_requirements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.jd_certification_requirements_id_seq OWNER TO "user";

--
-- TOC entry 3858 (class 0 OID 0)
-- Dependencies: 246
-- Name: jd_certification_requirements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.jd_certification_requirements_id_seq OWNED BY public.jd_certification_requirements.id;


--
-- TOC entry 235 (class 1259 OID 24738)
-- Name: langgraph_checkpoints; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.langgraph_checkpoints (
    id integer NOT NULL,
    request_id character varying(64) NOT NULL,
    node_name character varying(50) NOT NULL,
    state_json jsonb NOT NULL,
    token_count integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.langgraph_checkpoints OWNER TO "user";

--
-- TOC entry 234 (class 1259 OID 24737)
-- Name: langgraph_checkpoints_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.langgraph_checkpoints_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.langgraph_checkpoints_id_seq OWNER TO "user";

--
-- TOC entry 3859 (class 0 OID 0)
-- Dependencies: 234
-- Name: langgraph_checkpoints_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.langgraph_checkpoints_id_seq OWNED BY public.langgraph_checkpoints.id;


--
-- TOC entry 240 (class 1259 OID 25124)
-- Name: llm_request_log; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.llm_request_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    request_id character varying(64),
    agent_name character varying(255) NOT NULL,
    prompt_name character varying(255) NOT NULL,
    model character varying(255) NOT NULL,
    prompt_tokens integer NOT NULL,
    completion_tokens integer NOT NULL,
    total_tokens integer NOT NULL,
    cost_usd numeric(10,6) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    status character varying(50) DEFAULT 'SUCCESS'::character varying NOT NULL,
    error_message text
);


ALTER TABLE public.llm_request_log OWNER TO "user";

--
-- TOC entry 248 (class 1259 OID 25207)
-- Name: pii_scrub_audit; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.pii_scrub_audit (
    id bigint NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    operation character varying(50) NOT NULL,
    entity_type character varying(50),
    entity_id bigint,
    field_name character varying(100),
    pii_type character varying(50),
    action_taken character varying(50) NOT NULL,
    original_value_hash character varying(64),
    scrubbed_value text,
    detection_method character varying(50) NOT NULL,
    confidence_score numeric(5,4),
    user_id bigint,
    session_id character varying(100),
    metadata jsonb
)
PARTITION BY RANGE ("timestamp");


ALTER TABLE public.pii_scrub_audit OWNER TO "user";

--
-- TOC entry 247 (class 1259 OID 25206)
-- Name: pii_scrub_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.pii_scrub_audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pii_scrub_audit_id_seq OWNER TO "user";

--
-- TOC entry 3860 (class 0 OID 0)
-- Dependencies: 247
-- Name: pii_scrub_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.pii_scrub_audit_id_seq OWNED BY public.pii_scrub_audit.id;


--
-- TOC entry 225 (class 1259 OID 24641)
-- Name: requisition_detail; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.requisition_detail (
    id integer NOT NULL,
    requisition_request_id integer NOT NULL,
    payload_json jsonb NOT NULL,
    payload_hash character(64) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.requisition_detail OWNER TO "user";

--
-- TOC entry 224 (class 1259 OID 24640)
-- Name: requisition_detail_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.requisition_detail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.requisition_detail_id_seq OWNER TO "user";

--
-- TOC entry 3861 (class 0 OID 0)
-- Dependencies: 224
-- Name: requisition_detail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.requisition_detail_id_seq OWNED BY public.requisition_detail.id;


--
-- TOC entry 244 (class 1259 OID 25173)
-- Name: requisition_match_team_member_feedback; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.requisition_match_team_member_feedback (
    id bigint NOT NULL,
    team_member_id character varying(50) NOT NULL,
    correlation_id character varying(100) NOT NULL,
    reviewer_email character varying(100) NOT NULL,
    liked boolean DEFAULT false NOT NULL,
    rating smallint,
    comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT check_rating_range CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.requisition_match_team_member_feedback OWNER TO "user";

--
-- TOC entry 243 (class 1259 OID 25172)
-- Name: requisition_match_team_member_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

ALTER TABLE public.requisition_match_team_member_feedback ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.requisition_match_team_member_feedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 223 (class 1259 OID 24621)
-- Name: requisition_requests; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.requisition_requests (
    id integer NOT NULL,
    request_id character varying(64) NOT NULL,
    auth_client_id smallint NOT NULL,
    status smallint NOT NULL,
    client_name character varying(100) NOT NULL,
    correlation_id character varying(100),
    received_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at timestamp without time zone
);


ALTER TABLE public.requisition_requests OWNER TO "user";

--
-- TOC entry 222 (class 1259 OID 24620)
-- Name: requisition_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.requisition_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.requisition_requests_id_seq OWNER TO "user";

--
-- TOC entry 3862 (class 0 OID 0)
-- Dependencies: 222
-- Name: requisition_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.requisition_requests_id_seq OWNED BY public.requisition_requests.id;


--
-- TOC entry 221 (class 1259 OID 24612)
-- Name: requisition_status_master; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.requisition_status_master (
    status_id smallint NOT NULL,
    status_key character varying(40) NOT NULL,
    status_message character varying(255) NOT NULL
);


ALTER TABLE public.requisition_status_master OWNER TO "user";

--
-- TOC entry 220 (class 1259 OID 24611)
-- Name: requisition_status_master_status_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.requisition_status_master_status_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.requisition_status_master_status_id_seq OWNER TO "user";

--
-- TOC entry 3863 (class 0 OID 0)
-- Dependencies: 220
-- Name: requisition_status_master_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.requisition_status_master_status_id_seq OWNED BY public.requisition_status_master.status_id;


--
-- TOC entry 233 (class 1259 OID 24726)
-- Name: team_member_skill_certification; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.team_member_skill_certification (
    id integer NOT NULL,
    certification_id character varying(100),
    team_member_id character varying(50) NOT NULL,
    skill_id character varying(50) NOT NULL,
    certificate character varying(150),
    issuer character varying(100),
    issued_date date,
    valid_till date
);


ALTER TABLE public.team_member_skill_certification OWNER TO "user";

--
-- TOC entry 232 (class 1259 OID 24725)
-- Name: skill_certification_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.skill_certification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.skill_certification_id_seq OWNER TO "user";

--
-- TOC entry 3864 (class 0 OID 0)
-- Dependencies: 232
-- Name: skill_certification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.skill_certification_id_seq OWNED BY public.team_member_skill_certification.id;


--
-- TOC entry 228 (class 1259 OID 24669)
-- Name: skill_master; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.skill_master (
    skill_id character varying(50) NOT NULL,
    skill_name character varying(100) NOT NULL,
    category_id smallint NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.skill_master OWNER TO "user";

--
-- TOC entry 241 (class 1259 OID 25135)
-- Name: skill_ontology; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.skill_ontology (
    core_skill character varying(255) NOT NULL,
    enriched_terms character varying(255)[],
    id integer NOT NULL
);


ALTER TABLE public.skill_ontology OWNER TO "user";

--
-- TOC entry 245 (class 1259 OID 25193)
-- Name: skill_ontology_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.skill_ontology_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.skill_ontology_id_seq OWNER TO "user";

--
-- TOC entry 3865 (class 0 OID 0)
-- Dependencies: 245
-- Name: skill_ontology_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.skill_ontology_id_seq OWNED BY public.skill_ontology.id;


--
-- TOC entry 229 (class 1259 OID 24689)
-- Name: team_member; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.team_member (
    team_member_id character varying(50) NOT NULL,
    designation character varying(100),
    profile_type character varying(50),
    is_active boolean DEFAULT true,
    experience_in_months integer,
    base_location character varying(100),
    work_type public.work_type_enum,
    profile_url character varying(1024),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.team_member OWNER TO "user";

--
-- TOC entry 230 (class 1259 OID 24698)
-- Name: team_member_allocation; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.team_member_allocation (
    team_member_id character varying(50) NOT NULL,
    project_id character varying(50) NOT NULL,
    allocation_percentage numeric(5,2),
    start_date date,
    end_date date,
    billable boolean,
    is_deleted boolean DEFAULT false
);


ALTER TABLE public.team_member_allocation OWNER TO "user";

--
-- TOC entry 239 (class 1259 OID 25108)
-- Name: team_member_embeddings; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.team_member_embeddings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    team_member_id character varying(50) NOT NULL,
    embedding public.vector(3072) NOT NULL,
    profile_text text,
    metadata json,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    pii_scrubbed boolean DEFAULT false NOT NULL,
    scrubbed_at timestamp with time zone,
    CONSTRAINT ck_team_member_embeddings_pii_scrubbed CHECK ((pii_scrubbed = ANY (ARRAY[true, false])))
);


ALTER TABLE public.team_member_embeddings OWNER TO "user";

--
-- TOC entry 231 (class 1259 OID 24709)
-- Name: team_member_skill; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.team_member_skill (
    team_member_id character varying(50) NOT NULL,
    skill_id character varying(50) NOT NULL,
    rating integer,
    experience_in_months integer,
    is_deleted boolean DEFAULT false
);


ALTER TABLE public.team_member_skill OWNER TO "user";

--
-- TOC entry 3541 (class 2604 OID 24599)
-- Name: auth_access_tokens id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.auth_access_tokens ALTER COLUMN id SET DEFAULT nextval('public.auth_access_tokens_id_seq'::regclass);


--
-- TOC entry 3537 (class 2604 OID 24587)
-- Name: auth_clients id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.auth_clients ALTER COLUMN id SET DEFAULT nextval('public.auth_clients_id_seq'::regclass);


--
-- TOC entry 3549 (class 2604 OID 24663)
-- Name: category_master category_id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.category_master ALTER COLUMN category_id SET DEFAULT nextval('public.category_master_category_id_seq'::regclass);


--
-- TOC entry 3560 (class 2604 OID 24766)
-- Name: ingestion_audit_log id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.ingestion_audit_log ALTER COLUMN id SET DEFAULT nextval('public.ingestion_audit_log_id_seq'::regclass);


--
-- TOC entry 3569 (class 2604 OID 25198)
-- Name: jd_certification_requirements id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.jd_certification_requirements ALTER COLUMN id SET DEFAULT nextval('public.jd_certification_requirements_id_seq'::regclass);


--
-- TOC entry 3557 (class 2604 OID 24741)
-- Name: langgraph_checkpoints id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.langgraph_checkpoints ALTER COLUMN id SET DEFAULT nextval('public.langgraph_checkpoints_id_seq'::regclass);


--
-- TOC entry 3573 (class 2604 OID 25210)
-- Name: pii_scrub_audit id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.pii_scrub_audit ALTER COLUMN id SET DEFAULT nextval('public.pii_scrub_audit_id_seq'::regclass);


--
-- TOC entry 3547 (class 2604 OID 24644)
-- Name: requisition_detail id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_detail ALTER COLUMN id SET DEFAULT nextval('public.requisition_detail_id_seq'::regclass);


--
-- TOC entry 3545 (class 2604 OID 24624)
-- Name: requisition_requests id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_requests ALTER COLUMN id SET DEFAULT nextval('public.requisition_requests_id_seq'::regclass);


--
-- TOC entry 3544 (class 2604 OID 24615)
-- Name: requisition_status_master status_id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_status_master ALTER COLUMN status_id SET DEFAULT nextval('public.requisition_status_master_status_id_seq'::regclass);


--
-- TOC entry 3568 (class 2604 OID 25194)
-- Name: skill_ontology id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.skill_ontology ALTER COLUMN id SET DEFAULT nextval('public.skill_ontology_id_seq'::regclass);


--
-- TOC entry 3556 (class 2604 OID 25191)
-- Name: team_member_skill_certification id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_skill_certification ALTER COLUMN id SET DEFAULT nextval('public.skill_certification_id_seq'::regclass);


--
-- TOC entry 3814 (class 0 OID 24578)
-- Dependencies: 215
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.alembic_version (version_num) VALUES ('bca284b2d901');


--
-- TOC entry 3818 (class 0 OID 24596)
-- Dependencies: 219
-- Data for Name: auth_access_tokens; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- TOC entry 3816 (class 0 OID 24584)
-- Dependencies: 217
-- Data for Name: auth_clients; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.auth_clients (id, client_name, client_code, client_secret_hash, auth_type, is_active, created_at) VALUES (1, 'Test Client', 'test-client', '9caf06bb4436cdbfa20af9121a626bc1093c4f54b31c0fa937957856135345b6', 'OAUTH', true, '2026-03-06 07:39:12.647021');


--
-- TOC entry 3826 (class 0 OID 24660)
-- Dependencies: 227
-- Data for Name: category_master; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.category_master (category_id, category_name, created_at) VALUES (13, 'Primary', '2026-03-06 07:30:34.469334');


--
-- TOC entry 3837 (class 0 OID 24763)
-- Dependencies: 238
-- Data for Name: ingestion_audit_log; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (25, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-06 07:30:34.480652', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (26, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-06 07:30:34.492546', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (27, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-06 07:30:34.746203', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (45, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-06 07:32:54.091093', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (28, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "FAILED", "message": "Batch sync_2026_03_06_039 status updated to FAILED", "batch_id": "sync_2026_03_06_039", "error_message": "(sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) <class ''asyncpg.exceptions.UniqueViolationError''>: duplicate key value violates unique constraint \"ingestion_batch_state_pkey\"\nDETAIL:  Key (batch_id)=(sync_2026_03_06_039) already exists.\n[SQL: INSERT INTO ingestion_batch_state (batch_id, correlation_id, status, total_records, processed_records, failed_records, started_at, metadata) VALUES ($1::VARCHAR, $2::VARCHAR, $3::VARCHAR, $4::INTEGER, $5::INTEGER, $6::INTEGER, $7::TIMESTAMP WITHOUT TIME ZONE, $8::JSONB)]\n[parameters: (''sync_2026_03_06_039'', ''sync_2026_03_06_039'', ''PENDING'', 10, 0, 0, datetime.datetime(2026, 3, 6, 7, 30, 34, 754640), ''{\"batch_id\": \"sync_2026_03_06_039\", \"timestamp\": \"2026-03-06T11:26:53.198Z\", \"total_records\": 39, \"batch_number\": 2, \"total_batches\": 4, \"records_in_batch\": 10, \"source_system\": \"EAGLE_v1\", \"schema_version\": \"1.1\", \"status\": {\"code\": 0, \"key\": \"SUCCESS\", \"message\": \"Request successful\"}}'')]\n(Background on this error at: https://sqlalche.me/e/20/gkpj)", "failed_records": null, "processed_records": null}', '2026-03-06 07:30:34.767953', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (29, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "FAILED", "message": "Batch sync_2026_03_06_039 status updated to FAILED", "batch_id": "sync_2026_03_06_039", "error_message": "(sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) <class ''asyncpg.exceptions.UniqueViolationError''>: duplicate key value violates unique constraint \"ingestion_batch_state_pkey\"\nDETAIL:  Key (batch_id)=(sync_2026_03_06_039) already exists.\n[SQL: INSERT INTO ingestion_batch_state (batch_id, correlation_id, status, total_records, processed_records, failed_records, started_at, metadata) VALUES ($1::VARCHAR, $2::VARCHAR, $3::VARCHAR, $4::INTEGER, $5::INTEGER, $6::INTEGER, $7::TIMESTAMP WITHOUT TIME ZONE, $8::JSONB)]\n[parameters: (''sync_2026_03_06_039'', ''sync_2026_03_06_039'', ''PENDING'', 10, 0, 0, datetime.datetime(2026, 3, 6, 7, 30, 34, 779834), ''{\"batch_id\": \"sync_2026_03_06_039\", \"timestamp\": \"2026-03-06T11:26:53.204Z\", \"total_records\": 39, \"batch_number\": 3, \"total_batches\": 4, \"records_in_batch\": 10, \"source_system\": \"EAGLE_v1\", \"schema_version\": \"1.1\", \"status\": {\"code\": 0, \"key\": \"SUCCESS\", \"message\": \"Request successful\"}}'')]\n(Background on this error at: https://sqlalche.me/e/20/gkpj)", "failed_records": null, "processed_records": null}', '2026-03-06 07:30:34.789102', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (30, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "FAILED", "message": "Batch sync_2026_03_06_039 status updated to FAILED", "batch_id": "sync_2026_03_06_039", "error_message": "(sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) <class ''asyncpg.exceptions.UniqueViolationError''>: duplicate key value violates unique constraint \"ingestion_batch_state_pkey\"\nDETAIL:  Key (batch_id)=(sync_2026_03_06_039) already exists.\n[SQL: INSERT INTO ingestion_batch_state (batch_id, correlation_id, status, total_records, processed_records, failed_records, started_at, metadata) VALUES ($1::VARCHAR, $2::VARCHAR, $3::VARCHAR, $4::INTEGER, $5::INTEGER, $6::INTEGER, $7::TIMESTAMP WITHOUT TIME ZONE, $8::JSONB)]\n[parameters: (''sync_2026_03_06_039'', ''sync_2026_03_06_039'', ''PENDING'', 9, 0, 0, datetime.datetime(2026, 3, 6, 7, 30, 34, 800866), ''{\"batch_id\": \"sync_2026_03_06_039\", \"timestamp\": \"2026-03-06T11:26:53.208Z\", \"total_records\": 39, \"batch_number\": 4, \"total_batches\": 4, \"records_in_batch\": 9, \"source_system\": \"EAGLE_v1\", \"schema_version\": \"1.1\", \"status\": {\"code\": 0, \"key\": \"SUCCESS\", \"message\": \"Request successful\"}}'')]\n(Background on this error at: https://sqlalche.me/e/20/gkpj)", "failed_records": null, "processed_records": null}', '2026-03-06 07:30:34.810795', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (31, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-06 07:31:29.469665', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (32, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-06 07:31:29.485504', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (33, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-06 07:31:29.696826', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (36, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "FAILED", "message": "Batch sync_2026_03_06_039 status updated to FAILED", "batch_id": "sync_2026_03_06_039", "error_message": "''str'' object has no attribute ''copy''", "failed_records": null, "processed_records": null}', '2026-03-06 07:31:29.835227', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (39, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "FAILED", "message": "Batch sync_2026_03_06_039 status updated to FAILED", "batch_id": "sync_2026_03_06_039", "error_message": "''str'' object has no attribute ''copy''", "failed_records": null, "processed_records": null}', '2026-03-06 07:31:29.961445', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (42, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "FAILED", "message": "Batch sync_2026_03_06_039 status updated to FAILED", "batch_id": "sync_2026_03_06_039", "error_message": "''str'' object has no attribute ''copy''", "failed_records": null, "processed_records": null}', '2026-03-06 07:31:30.055215', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (43, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-06 07:32:53.849134', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (44, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-06 07:32:53.867892', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (46, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-06 07:32:54.106431', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (47, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-06 07:32:54.113386', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (48, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-06 07:32:54.342106', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (49, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-06 07:32:54.35615', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (50, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-06 07:32:54.362359', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (51, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-06 07:32:54.544704', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (52, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 9 records", "batch_id": "sync_2026_03_06_039", "total_records": 9}', '2026-03-06 07:32:54.559488', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (53, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-06 07:32:54.564773', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (54, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 9}', '2026-03-06 07:32:54.743208', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (55, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-09 03:24:58.971252', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (56, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-09 03:24:58.982753', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (57, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-09 03:24:59.129397', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (58, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-09 03:24:59.140818', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (59, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-09 03:24:59.144851', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (60, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-09 03:24:59.295467', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (61, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-09 03:24:59.305878', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (62, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-09 03:24:59.309009', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (63, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-09 03:24:59.443609', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (64, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 9 records", "batch_id": "sync_2026_03_06_039", "total_records": 9}', '2026-03-09 03:24:59.454384', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (65, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-09 03:24:59.457336', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (66, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 9}', '2026-03-09 03:24:59.607796', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (67, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-09 03:40:40.595427', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (68, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-09 03:40:40.604973', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (69, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-09 03:40:40.768094', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (70, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-09 03:40:40.780665', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (71, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-09 03:40:40.785023', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (72, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-09 03:40:40.948455', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (73, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 10 records", "batch_id": "sync_2026_03_06_039", "total_records": 10}', '2026-03-09 03:40:40.959475', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (74, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-09 03:40:40.963882', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (75, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 10}', '2026-03-09 03:40:41.115595', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (76, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_INITIALIZED', '{"status": "PENDING", "message": "Batch sync_2026_03_06_039 initialized with 9 records", "batch_id": "sync_2026_03_06_039", "total_records": 9}', '2026-03-09 03:40:41.126629', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (77, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "PROCESSING", "message": "Batch sync_2026_03_06_039 status updated to PROCESSING", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": null, "processed_records": null}', '2026-03-09 03:40:41.130872', NULL, NULL);
INSERT INTO public.ingestion_audit_log (id, batch_id, correlation_id, event_type, event_details, "timestamp", severity, source) VALUES (78, 'sync_2026_03_06_039', 'sync_2026_03_06_039', 'BATCH_STATUS_UPDATED', '{"status": "SUCCESS", "message": "Batch sync_2026_03_06_039 status updated to SUCCESS", "batch_id": "sync_2026_03_06_039", "error_message": null, "failed_records": 0, "processed_records": 9}', '2026-03-09 03:40:41.250325', NULL, NULL);


--
-- TOC entry 3835 (class 0 OID 24752)
-- Dependencies: 236
-- Data for Name: ingestion_batch_state; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.ingestion_batch_state (batch_id, correlation_id, status, total_records, processed_records, failed_records, started_at, completed_at, error_message, metadata) VALUES ('sync_2026_03_06_039', 'sync_2026_03_06_039', 'SUCCESS', 10, 9, 0, '2026-03-06 07:30:34.320852', '2026-03-09 03:40:41.247715', '''str'' object has no attribute ''copy''', '{"status": {"key": "SUCCESS", "code": 0, "message": "Request successful"}, "batch_id": "sync_2026_03_06_039", "timestamp": "2026-03-06T11:26:53.194Z", "batch_number": 1, "source_system": "EAGLE_v1", "total_batches": 4, "total_records": 39, "schema_version": "1.1", "records_in_batch": 10}');


--
-- TOC entry 3841 (class 0 OID 25143)
-- Dependencies: 242
-- Data for Name: jd_certification_requirements; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- TOC entry 3834 (class 0 OID 24738)
-- Dependencies: 235
-- Data for Name: langgraph_checkpoints; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (1, 'REQ-2026-000145', 'requisition_parsing', '{"parsed_jd": {"jd_text": "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL.", "location": ["Bangalore", "Pune"], "metadata": {}, "priority": "HIGH", "work_mode": ["wfh"], "experience": {"max_months": 60, "min_months": 48}, "client_name": "DNC", "normalized_role": "Backend Engineer", "normalized_title": "Senior Backend Engineer", "expected_start_date": "2026-02-15", "certifications_required": null, "extracted_mandatory_skills": ["REST API", "PostgreSQL", "Django", "AWS", "Python"], "extracted_preferred_skills": ["Kubernetes", "Docker"], "requisition_duration_month": 3}, "final_results": null, "correlation_id": "CORR-20260306073943-REQ-2026", "total_evaluated": 0, "total_qualified": 0, "candidate_scores": null, "cumulative_tokens": 0, "normalized_skills": null, "cumulative_cost_usd": 0.0, "retrieved_candidates": null}', NULL, '2026-03-06 07:39:48.694229');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (2, 'REQ-2026-000145', 'skill_normalization', '{"parsed_jd": {"jd_text": "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL.", "location": ["Bangalore", "Pune"], "metadata": {}, "priority": "HIGH", "work_mode": ["wfh"], "experience": {"max_months": 60, "min_months": 48}, "client_name": "DNC", "normalized_role": "Backend Engineer", "normalized_title": "Senior Backend Engineer", "expected_start_date": "2026-02-15", "certifications_required": null, "extracted_mandatory_skills": ["REST API", "PostgreSQL", "Django", "AWS", "Python"], "extracted_preferred_skills": ["Kubernetes", "Docker"], "requisition_duration_month": 3}, "error_message": "Normalization fallback used due to: LLM normalization failed - no content returned", "final_results": null, "correlation_id": "CORR-20260306073943-REQ-2026", "total_evaluated": 0, "total_qualified": 0, "candidate_scores": null, "cumulative_tokens": 0, "normalized_skills": {"mandatory_enriched": {}, "preferred_enriched": {}, "mandatory_skill_ids": ["aws"], "preferred_skill_ids": ["kubernetes", "docker"], "certification_enriched": {}, "mandatory_alternatives": {"AWS": ["aws"]}, "preferred_alternatives": {"Docker": ["docker"], "Kubernetes": ["kubernetes"]}, "original_certifications": null, "normalized_certifications": null}, "cumulative_cost_usd": 0.0, "retrieved_candidates": null}', NULL, '2026-03-06 07:39:50.301458');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (3, 'REQ-2026-000145', 'embedding', '{"parsed_jd": {"jd_text": "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL.", "location": ["Bangalore", "Pune"], "metadata": {}, "priority": "HIGH", "work_mode": ["wfh"], "experience": {"max_months": 60, "min_months": 48}, "client_name": "DNC", "normalized_role": "Backend Engineer", "normalized_title": "Senior Backend Engineer", "expected_start_date": "2026-02-15", "certifications_required": null, "extracted_mandatory_skills": ["REST API", "PostgreSQL", "Django", "AWS", "Python"], "extracted_preferred_skills": ["Kubernetes", "Docker"], "requisition_duration_month": 3}, "error_message": "Embedding generation failed: can only join an iterable", "final_results": null, "correlation_id": "CORR-20260306073943-REQ-2026", "total_evaluated": 0, "total_qualified": 0, "candidate_scores": null, "cumulative_tokens": 0, "normalized_skills": {"mandatory_enriched": {}, "preferred_enriched": {}, "mandatory_skill_ids": ["aws"], "preferred_skill_ids": ["kubernetes", "docker"], "certification_enriched": {}, "mandatory_alternatives": {"AWS": ["aws"]}, "preferred_alternatives": {"Docker": ["docker"], "Kubernetes": ["kubernetes"]}, "original_certifications": null, "normalized_certifications": null}, "cumulative_cost_usd": 0.0, "retrieved_candidates": null}', NULL, '2026-03-06 07:39:50.309658');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (4, 'REQ-2026-000145', 'rag_retrieval', '{"parsed_jd": {"jd_text": "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL.", "location": ["Bangalore", "Pune"], "metadata": {}, "priority": "HIGH", "work_mode": ["wfh"], "experience": {"max_months": 60, "min_months": 48}, "client_name": "DNC", "normalized_role": "Backend Engineer", "normalized_title": "Senior Backend Engineer", "expected_start_date": "2026-02-15", "certifications_required": null, "extracted_mandatory_skills": ["REST API", "PostgreSQL", "Django", "AWS", "Python"], "extracted_preferred_skills": ["Kubernetes", "Docker"], "requisition_duration_month": 3}, "final_results": null, "correlation_id": "CORR-20260306073943-REQ-2026", "total_evaluated": 0, "total_qualified": 0, "candidate_scores": null, "cumulative_tokens": 0, "normalized_skills": {"mandatory_enriched": {}, "preferred_enriched": {}, "mandatory_skill_ids": ["aws"], "preferred_skill_ids": ["kubernetes", "docker"], "certification_enriched": {}, "mandatory_alternatives": {"AWS": ["aws"]}, "preferred_alternatives": {"Docker": ["docker"], "Kubernetes": ["kubernetes"]}, "original_certifications": null, "normalized_certifications": null}, "cumulative_cost_usd": 0.0, "retrieved_candidates": []}', NULL, '2026-03-06 07:39:50.322772');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (5, 'REQ-2026-000145', 'matching_scoring', '{"parsed_jd": {"jd_text": "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL.", "location": ["Bangalore", "Pune"], "metadata": {}, "priority": "HIGH", "work_mode": ["wfh"], "experience": {"max_months": 60, "min_months": 48}, "client_name": "DNC", "normalized_role": "Backend Engineer", "normalized_title": "Senior Backend Engineer", "expected_start_date": "2026-02-15", "certifications_required": null, "extracted_mandatory_skills": ["REST API", "PostgreSQL", "Django", "AWS", "Python"], "extracted_preferred_skills": ["Kubernetes", "Docker"], "requisition_duration_month": 3}, "final_results": null, "correlation_id": "CORR-20260306073943-REQ-2026", "total_evaluated": 0, "total_qualified": 0, "candidate_scores": [{"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.729, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9963", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.729, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.729, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5974", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.729, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.729, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6248", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.729, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5537", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4974", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5392", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9567", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1458", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5700", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Qualified"}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9413", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5536", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "7701", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1370", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9744", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3757", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1989", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1237", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "2549", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6047", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "7268", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6017", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "8175", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6681", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "2748", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "8921", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3090", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5597", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5716", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3780", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4399", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3061", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6679", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1276", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 0.75, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4870", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5981", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4205", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 0.75, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "2868", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9681", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5678", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 0.75, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}], "cumulative_tokens": 0, "normalized_skills": {"mandatory_enriched": {}, "preferred_enriched": {}, "mandatory_skill_ids": ["aws"], "preferred_skill_ids": ["kubernetes", "docker"], "certification_enriched": {}, "mandatory_alternatives": {"AWS": ["aws"]}, "preferred_alternatives": {"Docker": ["docker"], "Kubernetes": ["kubernetes"]}, "original_certifications": null, "normalized_certifications": null}, "cumulative_cost_usd": 0.0, "retrieved_candidates": []}', NULL, '2026-03-06 07:40:49.582921');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (6, 'REQ-2026-000145', 'explanation_generation', '{"parsed_jd": {"jd_text": "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL.", "location": ["Bangalore", "Pune"], "metadata": {}, "priority": "HIGH", "work_mode": ["wfh"], "experience": {"max_months": 60, "min_months": 48}, "client_name": "DNC", "normalized_role": "Backend Engineer", "normalized_title": "Senior Backend Engineer", "expected_start_date": "2026-02-15", "certifications_required": null, "extracted_mandatory_skills": ["REST API", "PostgreSQL", "Django", "AWS", "Python"], "extracted_preferred_skills": ["Kubernetes", "Docker"], "requisition_duration_month": 3}, "final_results": null, "correlation_id": "CORR-20260306073943-REQ-2026", "total_evaluated": 0, "total_qualified": 0, "candidate_scores": [{"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.729, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9963", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.729, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 9963", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.73. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.729, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5974", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.729, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 5974", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.73. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.729, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6248", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.729, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 6248", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.73. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5537", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 5537", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4974", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 4974", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5392", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 5392", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9567", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 9567", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1458", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 1458", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5700", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 5700", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9413", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 9413", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5536", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5536", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "7701", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 7701", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1370", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 1370", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9744", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 9744", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3757", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 3757", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1989", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 1989", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1237", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 1237", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "2549", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 2549", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6047", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 6047", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "7268", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 7268", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6017", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 6017", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "8175", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 8175", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6681", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 6681", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "2748", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 2748", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "8921", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 8921", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3090", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 3090", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5597", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5597", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5716", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5716", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3780", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 3780", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4399", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 4399", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3061", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 3061", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6679", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 6679", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1276", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 0.75, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 1276", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4870", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 4870", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5981", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5981", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4205", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 0.75, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 4205", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "2868", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 2868", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9681", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 9681", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5678", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 0.75, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5678", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}], "cumulative_tokens": 0, "normalized_skills": {"mandatory_enriched": {}, "preferred_enriched": {}, "mandatory_skill_ids": ["aws"], "preferred_skill_ids": ["kubernetes", "docker"], "certification_enriched": {}, "mandatory_alternatives": {"AWS": ["aws"]}, "preferred_alternatives": {"Docker": ["docker"], "Kubernetes": ["kubernetes"]}, "original_certifications": null, "normalized_certifications": null}, "cumulative_cost_usd": 0.0, "retrieved_candidates": []}', NULL, '2026-03-06 07:40:57.365574');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (7, 'REQ-2026-000145', 'result_aggregation', '{"parsed_jd": {"jd_text": "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL.", "location": ["Bangalore", "Pune"], "metadata": {}, "priority": "HIGH", "work_mode": ["wfh"], "experience": {"max_months": 60, "min_months": 48}, "client_name": "DNC", "normalized_role": "Backend Engineer", "normalized_title": "Senior Backend Engineer", "expected_start_date": "2026-02-15", "certifications_required": null, "extracted_mandatory_skills": ["REST API", "PostgreSQL", "Django", "AWS", "Python"], "extracted_preferred_skills": ["Kubernetes", "Docker"], "requisition_duration_month": 3}, "final_results": [{"status": "QUALIFIED", "fit_level": "MEDIUM", "explanation": ["Summary: Match Analysis for 9963", "Analysis: Final Score: 0.73. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Strengths: Satisfies all mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 72.9, "team_member_id": "9963", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Qualified"}}, {"status": "QUALIFIED", "fit_level": "MEDIUM", "explanation": ["Summary: Match Analysis for 5974", "Analysis: Final Score: 0.73. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Strengths: Satisfies all mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 72.9, "team_member_id": "5974", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Qualified"}}, {"status": "QUALIFIED", "fit_level": "MEDIUM", "explanation": ["Summary: Match Analysis for 6248", "Analysis: Final Score: 0.73. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Strengths: Satisfies all mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 72.9, "team_member_id": "6248", "availability_match": false, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Qualified"}}, {"status": "QUALIFIED", "fit_level": "MEDIUM", "explanation": ["Summary: Match Analysis for 5537", "Analysis: Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Strengths: Satisfies all mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 62.9, "team_member_id": "5537", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Qualified"}}, {"status": "QUALIFIED", "fit_level": "MEDIUM", "explanation": ["Summary: Match Analysis for 4974", "Analysis: Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Strengths: Satisfies all mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 62.9, "team_member_id": "4974", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Qualified"}}, {"status": "QUALIFIED", "fit_level": "MEDIUM", "explanation": ["Summary: Match Analysis for 5392", "Analysis: Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Strengths: Satisfies all mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 62.9, "team_member_id": "5392", "availability_match": false, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Qualified"}}, {"status": "QUALIFIED", "fit_level": "MEDIUM", "explanation": ["Summary: Match Analysis for 9567", "Analysis: Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Strengths: Satisfies all mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 62.9, "team_member_id": "9567", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Qualified"}}, {"status": "QUALIFIED", "fit_level": "MEDIUM", "explanation": ["Summary: Match Analysis for 1458", "Analysis: Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Strengths: Satisfies all mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 62.9, "team_member_id": "1458", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Qualified"}}, {"status": "QUALIFIED", "fit_level": "MEDIUM", "explanation": ["Summary: Match Analysis for 5700", "Analysis: Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Strengths: Satisfies all mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 62.9, "team_member_id": "5700", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Qualified"}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 9413", "Analysis: Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 15.0, "team_member_id": "9413", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 5536", "Analysis: Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 15.0, "team_member_id": "5536", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 7701", "Analysis: Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 15.0, "team_member_id": "7701", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 1370", "Analysis: Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 15.0, "team_member_id": "1370", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 9744", "Analysis: Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 15.0, "team_member_id": "9744", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 3757", "Analysis: Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 15.0, "team_member_id": "3757", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 1989", "Analysis: Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 15.0, "team_member_id": "1989", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 1237", "Analysis: Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 15.0, "team_member_id": "1237", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 2549", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "2549", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 6047", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "6047", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 7268", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "7268", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 6017", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "6017", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 8175", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "8175", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 6681", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "6681", "availability_match": false, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 2748", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "2748", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 8921", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "8921", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 3090", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "3090", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 5597", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "5597", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 5716", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "5716", "availability_match": false, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 3780", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "3780", "availability_match": false, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 4399", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "4399", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 3061", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "3061", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 6679", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "6679", "availability_match": true, "detailed_breakdown": {"role_type": "SENIOR", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 1276", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "1276", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 4870", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "4870", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 5981", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "5981", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 4205", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "4205", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 2868", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "2868", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 9681", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "9681", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}, {"status": "DISQUALIFIED", "fit_level": "LOW", "explanation": ["Summary: Match Analysis for 5678", "Analysis: Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "Gaps: Missing mandatory skill groups", "Recommendation: Review profile for specific gaps."], "profile_score": 12.5, "team_member_id": "5678", "availability_match": true, "detailed_breakdown": {"role_type": "MID", "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "ai_boost_applied": 0.0, "ai_confidence_score": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}}], "correlation_id": "CORR-20260306073943-REQ-2026", "total_evaluated": 39, "total_qualified": 9, "candidate_scores": [{"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.729, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9963", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.729, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 9963", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.73. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.729, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5974", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.729, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 5974", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.73. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.729, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6248", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.729, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 6248", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.73. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5537", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 5537", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4974", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 4974", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5392", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 5392", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9567", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 9567", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1458", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 1458", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Qualified", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.629, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": true, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 1.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Qualified", "qualification_status": "QUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5700", "meets_threshold": true, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": true, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 1.0}, "experience_score": 1.0, "base_agentic_score": 0.629, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": [], "summary": "Match Analysis for 5700", "strengths": ["Satisfies all mandatory skill groups"], "fit_analysis": "Final Score: 0.63. Ledger: Mandatory Group=1.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Qualified"}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9413", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 9413", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5536", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5536", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "7701", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 7701", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1370", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 1370", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9744", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 9744", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3757", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 3757", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1989", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 1989", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.15, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.5, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1237", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.5, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.15, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 1237", "strengths": [], "fit_analysis": "Final Score: 0.15. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "2549", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 2549", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6047", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 6047", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "7268", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 7268", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6017", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 6017", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "8175", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 8175", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6681", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 6681", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "2748", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 2748", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "8921", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 8921", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3090", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 3090", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5597", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5597", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5716", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5716", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": false, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3780", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 3780", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4399", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 4399", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "3061", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 3061", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": true, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "6679", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.05, "weight_m": 0.5, "weight_p": 0.2, "weight_s": 0.25, "role_type": "SENIOR", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 6679", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 60% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "1276", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 0.75, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 1276", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4870", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 4870", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5981", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5981", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": false, "work_mode_matched": false, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "4205", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 0.75, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 4205", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "2868", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 2868", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 1.0, "location_matched": false, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "9681", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 1.0, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 9681", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}, {"reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "total_m": 1, "ai_boost": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "final_score": 0.125, "ai_reasoning": "LLM failed to respond", "is_available": true, "is_qualified": false, "match_reasons": {"gaps": [], "strengths": [], "ai_reasoning": "LLM failed to respond", "mandatory_score": 0.0, "preferred_score": 0.0, "experience_score": 0.75, "location_matched": true, "work_mode_matched": true, "certification_score": 1.0, "semantic_similarity": 0.5, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold.", "qualification_status": "DISQUALIFIED", "certification_matched": [], "certification_missing": []}, "phase0_ledger": {}, "team_member_id": "5678", "meets_threshold": false, "score_breakdown": {"penalty": 0.0, "weight_c": 0.15, "weight_m": 0.4, "weight_p": 0.2, "weight_s": 0.25, "role_type": "MID", "is_qualified": false, "context_score": 0.08, "preferred_skills": 0.0, "semantic_similarity": 0.5, "mandatory_skills_group": 0.0}, "experience_score": 0.75, "base_agentic_score": 0.125, "ai_confidence_score": 0.5, "ai_override_applied": false, "semantic_similarity": 0.5, "detailed_explanation": {"gaps": ["Missing mandatory skill groups"], "summary": "Match Analysis for 5678", "strengths": [], "fit_analysis": "Final Score: 0.12. Ledger: Mandatory Group=0.00, Semantic=0.50, Context Boost=0.00, Penalties=0.00, AI Boost=0.00.", "recommendation": "Review profile for specific gaps."}, "qualification_reason": "Disqualified: Mandatory skill match (0%) below 40% threshold."}], "cumulative_tokens": 0, "normalized_skills": {"mandatory_enriched": {}, "preferred_enriched": {}, "mandatory_skill_ids": ["aws"], "preferred_skill_ids": ["kubernetes", "docker"], "certification_enriched": {}, "mandatory_alternatives": {"AWS": ["aws"]}, "preferred_alternatives": {"Docker": ["docker"], "Kubernetes": ["kubernetes"]}, "original_certifications": null, "normalized_certifications": null}, "cumulative_cost_usd": 0.0, "retrieved_candidates": []}', NULL, '2026-03-06 07:40:57.439254');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (8, 'REQ-2026-000201', 'pii_scrubber', '{"parsed_jd": null, "pii_scrubbed": true, "final_results": null, "correlation_id": "CORR-20260309041154-REQ-2026", "fields_scrubbed": ["client_name", "jd_text"], "total_evaluated": 0, "total_pii_found": 4, "total_qualified": 0, "candidate_scores": null, "cumulative_tokens": 0, "normalized_skills": null, "cumulative_cost_usd": 0.0, "retrieved_candidates": null}', NULL, '2026-03-09 04:11:55.394638');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (9, 'REQ-2026-000201', 'requisition_parsing', '{"parsed_jd": null, "error_message": "SEMANTIC_VALIDATION_FAILED: Client Name ''CLIENT_TOKEN_b1b000ad'' appears to be a placeholder or token, not a plausible company name; Job Description contains redacted information ([NAME_REDACTED], [EMAIL_REDACTED], [PHONE_REDACTED]) which may indicate incomplete or placeholder data", "final_results": null, "correlation_id": "CORR-20260309041154-REQ-2026", "total_evaluated": 0, "total_qualified": 0, "candidate_scores": null, "cumulative_tokens": 0, "normalized_skills": null, "cumulative_cost_usd": 0.0, "retrieved_candidates": null}', NULL, '2026-03-09 04:11:56.339614');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (10, 'REQ-2026-000202', 'pii_scrubber', '{"parsed_jd": null, "pii_scrubbed": true, "final_results": null, "correlation_id": "CORR-20260309041306-REQ-2026", "fields_scrubbed": ["client_name"], "total_evaluated": 0, "total_pii_found": 1, "total_qualified": 0, "candidate_scores": null, "cumulative_tokens": 0, "normalized_skills": null, "cumulative_cost_usd": 0.0, "retrieved_candidates": null}', NULL, '2026-03-09 04:13:06.753695');
INSERT INTO public.langgraph_checkpoints (id, request_id, node_name, state_json, token_count, created_at) VALUES (11, 'REQ-2026-000202', 'requisition_parsing', '{"parsed_jd": null, "error_message": "SEMANTIC_VALIDATION_FAILED: Client name ''CLIENT_TOKEN_a5754bfd'' appears to be a placeholder or token, not a plausible company name", "final_results": null, "correlation_id": "CORR-20260309041306-REQ-2026", "total_evaluated": 0, "total_qualified": 0, "candidate_scores": null, "cumulative_tokens": 0, "normalized_skills": null, "cumulative_cost_usd": 0.0, "retrieved_candidates": null}', NULL, '2026-03-09 04:13:07.176445');


--
-- TOC entry 3839 (class 0 OID 25124)
-- Dependencies: 240
-- Data for Name: llm_request_log; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.llm_request_log (id, request_id, agent_name, prompt_name, model, prompt_tokens, completion_tokens, total_tokens, cost_usd, created_at, status, error_message) VALUES ('1162cd7c-157a-4e0c-b2c5-7637bf3f05e7', 'REQ-2026-000145', 'skill_normalization', 'skill_ontology_normalization', 'gpt-4', 0, 0, 0, 0.000000, '2026-03-06 07:39:50.291414', 'FAILED', 'LLM normalization failed - no content returned');


--
-- TOC entry 3824 (class 0 OID 24641)
-- Dependencies: 225
-- Data for Name: requisition_detail; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.requisition_detail (id, requisition_request_id, payload_json, payload_hash, created_at) VALUES (1, 3, '{"metadata": {"department": "Engineering", "submitted_at": "2026-02-19T00:00:00", "submitted_by": "Aarya"}, "request_id": "REQ-2026-000145", "client_name": "DNC", "source_system": "EAGLE_v1", "schema_version": "1.1", "job_description": {"role": "Backend Engineer", "title": "Senior Backend Engineer", "jd_text": "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL.", "location": ["Bangalore", "Pune"], "priority": "HIGH", "work_mode": ["wfh"], "experience": {"max_months": 60, "min_months": 48}, "client_name": "DNC", "mandatory_skills": ["Python", "Django", "REST API", "AWS", "PostgreSQL"], "preferred_skills": ["Docker", "Kubernetes"], "expected_start_date": "2026-02-15", "certifications_required": null, "requisition_duration_month": 3}}', 'a6144c0f9c0d29a924b9ab33b416b5589c9f9d6dd7069d49b8ac3cd104c82997', '2026-03-06 07:39:44.007021');
INSERT INTO public.requisition_detail (id, requisition_request_id, payload_json, payload_hash, created_at) VALUES (2, 4, '{"metadata": {"department": "Engineering", "submitted_at": null, "submitted_by": "recruiter@dnc.com"}, "request_id": "REQ-2026-000201", "client_name": "DNC", "source_system": "HR_SYSTEM", "schema_version": "v1", "job_description": {"role": "Backend Developer", "title": "Senior Backend Engineer", "jd_text": "We are looking for a Senior Backend Engineer with 3-5 years of experience in Python, Django, and cloud services. Contact John Smith at john.smith@company.com or call 555-123-4567.", "location": ["Bangalore", "Remote"], "priority": "HIGH", "work_mode": ["Hybrid", "Remote"], "experience": {"max_months": 60, "min_months": 36}, "client_name": "DNC", "mandatory_skills": ["Python", "Django", "REST API", "AWS", "PostgreSQL"], "preferred_skills": ["Docker", "Kubernetes", "Redis"], "expected_start_date": "2026-04-01", "certifications_required": ["AWS Solutions Architect"], "requisition_duration_month": 6}}', 'af7bb79a4205c96a7ecec94472286272e36b264bbf218eaac1298cf35160cc50', '2026-03-09 04:11:54.047784');
INSERT INTO public.requisition_detail (id, requisition_request_id, payload_json, payload_hash, created_at) VALUES (3, 5, '{"metadata": {"department": "Engineering", "submitted_at": null, "submitted_by": "recruiter@acme.com"}, "request_id": "REQ-2026-000202", "client_name": "Acme Corp", "source_system": "HR_SYSTEM", "schema_version": "v1", "job_description": {"role": "Backend Developer", "title": "Senior Backend Engineer", "jd_text": "We are looking for a Senior Backend Engineer with 3-5 years of experience in Python, Django, and cloud services. The ideal candidate will have strong experience building REST APIs and working with relational databases.", "location": ["Bangalore", "Remote"], "priority": "HIGH", "work_mode": ["Hybrid", "Remote"], "experience": {"max_months": 60, "min_months": 36}, "client_name": "Acme Corp", "mandatory_skills": ["Python", "Django", "REST API", "AWS", "PostgreSQL"], "preferred_skills": ["Docker", "Kubernetes", "Redis"], "expected_start_date": "2026-04-01", "certifications_required": ["AWS Solutions Architect"], "requisition_duration_month": 6}}', '9e8fceeb06ccf321d83f90604630ba19dca81cfda09defb3d9e5bd75f206e6a4', '2026-03-09 04:13:06.25302');


--
-- TOC entry 3843 (class 0 OID 25173)
-- Dependencies: 244
-- Data for Name: requisition_match_team_member_feedback; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- TOC entry 3822 (class 0 OID 24621)
-- Dependencies: 223
-- Data for Name: requisition_requests; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.requisition_requests (id, request_id, auth_client_id, status, client_name, correlation_id, received_at, completed_at) VALUES (3, 'REQ-2026-000145', 1, 4, 'DNC', 'CORR-20260306073943-REQ-2026', '2026-03-06 07:39:43.999642', '2026-03-06 07:40:57.467371');
INSERT INTO public.requisition_requests (id, request_id, auth_client_id, status, client_name, correlation_id, received_at, completed_at) VALUES (4, 'REQ-2026-000201', 1, 5, 'DNC', 'CORR-20260309041154-REQ-2026', '2026-03-09 04:11:54.04111', NULL);
INSERT INTO public.requisition_requests (id, request_id, auth_client_id, status, client_name, correlation_id, received_at, completed_at) VALUES (5, 'REQ-2026-000202', 1, 5, 'Acme Corp', 'CORR-20260309041306-REQ-2026', '2026-03-09 04:13:06.251114', NULL);


--
-- TOC entry 3820 (class 0 OID 24612)
-- Dependencies: 221
-- Data for Name: requisition_status_master; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.requisition_status_master (status_id, status_key, status_message) VALUES (1, 'RECEIVED', 'Request received and queued for processing');
INSERT INTO public.requisition_status_master (status_id, status_key, status_message) VALUES (2, 'PROCESSING', 'AI pipeline is processing the request');
INSERT INTO public.requisition_status_master (status_id, status_key, status_message) VALUES (3, 'MATCHING', 'AI pipeline is finding skill matches');
INSERT INTO public.requisition_status_master (status_id, status_key, status_message) VALUES (4, 'COMPLETED', 'Request processed successfully');
INSERT INTO public.requisition_status_master (status_id, status_key, status_message) VALUES (5, 'FAILED', 'Request processing failed');
INSERT INTO public.requisition_status_master (status_id, status_key, status_message) VALUES (6, 'CANCELLED', 'Request was cancelled');


--
-- TOC entry 3827 (class 0 OID 24669)
-- Dependencies: 228
-- Data for Name: skill_master; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('aws', 'AWS', 13, '2026-03-06 07:30:34.613894');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('python-django', 'Python & Django', 13, '2026-03-06 07:32:54.202936');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('react-js', 'React JS', 13, '2026-03-06 07:32:54.20704');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('azure', 'Azure', 13, '2026-03-06 07:30:34.522169');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('ci-cd-unit-testing', 'CI/CD & Unit Testing', 13, '2026-03-06 07:32:54.213786');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('mlops', 'MLOps', 13, '2026-03-06 07:30:34.589892');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('machine-learning-nlp-limited-genai-exposure', 'Machine Learning, NLP, Limited GenAI Exposure', 13, '2026-03-06 07:30:34.699333');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('prompt-engineering-openai-api-langchain-pinecone-c', 'Prompt Engineering, OpenAI API, LangChain, Pinecone, Chroma, RAG Pipelines, GitHub Copilot', 13, '2026-03-06 07:30:34.515275');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('scala-spark', 'Scala & Spark', 13, '2026-03-06 07:32:54.442914');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('mssql-nosql', 'MSSQL / NoSQL', 13, '2026-03-06 07:32:54.446155');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('docker', 'Docker', 13, '2026-03-06 07:30:34.526779');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('openai-api-langchain-basic-rag-advanced-machine-le', 'OpenAI API, LangChain, Basic RAG, Advanced Machine Learning', 13, '2026-03-06 07:30:34.607706');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('gcp', 'GCP', 13, '2026-03-06 07:30:34.550842');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('kubernetes', 'Kubernetes', 13, '2026-03-06 07:30:34.557963');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('aws-big-data-stack', 'AWS Big Data Stack', 13, '2026-03-06 07:32:54.44903');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('data-warehousing-etl', 'Data Warehousing & ETL', 13, '2026-03-06 07:32:54.626159');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('vertica-mssql', 'Vertica / MSSQL', 13, '2026-03-06 07:32:54.629508');
INSERT INTO public.skill_master (skill_id, skill_name, category_id, created_at) VALUES ('qlikview-tableau-power-bi', 'QlikView / Tableau / Power BI', 13, '2026-03-06 07:32:54.632865');


--
-- TOC entry 3840 (class 0 OID 25135)
-- Dependencies: 241
-- Data for Name: skill_ontology; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- TOC entry 3828 (class 0 OID 24689)
-- Dependencies: 229
-- Data for Name: team_member; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('4974', 'Lead', 'lead', true, 132, 'Mumbai', 'wfh', 'https://docs.google.com/document/d/1JapEbvPntAXIJFJHIb7zUN4u2m3X1k_G/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.119003');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('9744', 'Project Manager', 'project manager', true, 144, 'Bangalore', 'wfo', 'https://docs.google.com/document/d/172Byj10ESOBYWO7gcaeTJ3gtIQxLmuud/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.136646');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('9413', 'Senior Software Engineer', 'senior software engineer', true, 96, 'Bangalore', 'hybrid', 'https://docs.google.com/document/d/1nORFwiVZTXZ3wJHZn5-vJH6rnY51OLsJ/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:30:34.49827');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('3757', 'Project Manager', 'project manager', true, 96, 'Bangalore', 'wfh', 'https://docs.google.com/document/d/18hGdqbjBVZC-JqKSi_N6s0TQCWbnBcZ_/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.152139');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('1989', 'Project Manager', 'project manager', true, 144, 'Hyderabad', 'hybrid', 'https://docs.google.com/document/d/1_PQesVD5gGR4uxva_viGAQrY_fE6gY-y/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.16735');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('1237', 'Project Manager', 'project manager', true, 144, 'Pune', 'wfh', 'https://docs.google.com/document/d/1mf3GdvQkuG0AU9igsTy_EqkaC5svzOp3/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.183479');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('5716', 'Senior Python Django Developer', 'senior software engineer', true, 120, 'Bangalore', 'wfh', 'https://docs.google.com/document/d/1RUKt7Capva6LQPXjauYdFZQnBONhHUM4/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.201221');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('5392', 'Lead Python Developer', 'lead', true, 120, 'Bangalore', 'wfo', 'https://docs.google.com/document/d/1PC8T8eMLhWr1QT4G2uDnWiWoPUPeOaiK/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.238356');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('3780', 'Senior Backend Engineer', 'project lead', true, 108, 'Mumbai', 'wfo', 'https://docs.google.com/document/d/1OVKSjGMaRuHjzXjouw0uxNFxN2_nwqEj/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.272033');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('9567', 'Python Django Developer', 'senior software engineer', true, 108, 'Mumbai', 'wfo', 'https://docs.google.com/document/d/1cS1DaWpzTQF8x6qtq-SdqYij7xLntM1n/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.302573');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('1458', 'Senior Software Engineer', 'project manager', true, 108, 'Mumbai', 'wfh', 'https://docs.google.com/document/d/1QkFjH1n4mxmuB-41iOdgikN144KARcO3/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.321809');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('5700', 'Backend Developer', 'lead', true, 120, 'Pune', 'hybrid', 'https://docs.google.com/document/d/1kTr-6OGqn4zvwEikqx9BUOLiU41e02e6/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.367484');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('4399', 'Full Stack Developer', 'project lead', true, 108, 'Bangalore', 'wfo', 'https://docs.google.com/document/d/1WiONn_z2EoR6AaHmPGpFcR8F9KflMECy/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.388549');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('3061', 'Software Developer', 'senior software engineer', true, 108, 'Hyderabad', 'wfo', 'https://docs.google.com/document/d/1i6ukF3kiY60cESuPjpFfH1leMp8-Ri4d/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.405936');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('6679', 'Application Developer', 'senior software engineer', true, 132, 'Pune', 'hybrid', 'https://docs.google.com/document/d/1ugaoYkOAbHf_Z4FnBsoC-68AwX56pDHg/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.422768');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('1276', 'Scala Developer', 'project lead', true, 36, 'Hyderabad', 'wfo', 'https://docs.google.com/document/d/1L-NQ9MEZy0SidD3INBBdXHATu7453yVE/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.441441');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('5678', 'Backend Developer', 'software engineer', true, 36, 'Pune', 'wfh', 'https://docs.google.com/document/d/1eRlgejRTpCqbOgcVJur12s2lm5sguCh2/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.570086');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('2549', 'Application Developer', 'project lead', true, 48, 'Bangalore', 'wfh', 'https://docs.google.com/document/d/1H4-0iA8PH9Ot_KT9_-5SbdbATG3dXBux/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.588887');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('6047', 'Java Developer', 'senior software engineer', true, 72, 'Bangalore', 'wfo', 'https://docs.google.com/document/d/1hWvLabkCNvK_K7M2vXaNEYv2uErgcASM/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.606503');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('7268', 'Senior BI/DWH Specialist', 'project manager', true, 72, 'Pune', 'wfh', 'https://docs.google.com/document/d/1Dnqh3ZLAM9_RlAKfAWWGKOSXgFDL20ds/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.624422');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('5536', 'Senior Software Engineer', 'senior software engineer', true, 108, 'Pune', 'wfh', 'https://docs.google.com/document/d/iorIHpOBbWiLPu66vyWzHa30u/edit', '2026-03-06 07:30:34.544901');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('3090', 'Project Lead', 'project lead', true, 96, 'Pune', 'hybrid', 'https://docs.google.com/document/d/1ZWrYsG_QL5G11Nw_KgOxifgVFxM28yOC/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:30:34.576103');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('9963', 'Lead', 'lead', true, 120, 'Bangalore', 'hybrid', 'https://docs.google.com/document/d/1mgVlXx5PxrFkmoV9UcJ9kLL-yOlx-LBA/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:30:34.604664');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('5974', 'Project Manager', 'project manager', true, 132, 'Hyderabad', 'wfo', 'https://docs.google.com/document/d/1Mae--2p6O0T1Gl-xO5gw2aQeRl-s3JFl/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:30:34.633658');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('5597', 'Project Lead', 'project lead', true, 120, 'Pune', 'wfh', 'https://docs.google.com/document/d/1pPSgVIMCPM8oclZf5Iv0twfLg6j4pLbr/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:30:34.658767');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('6248', 'Project Manager', 'project manager', true, 132, 'Pune', 'hybrid', 'https://docs.google.com/document/d/1bsDCbTyKllAKAsDGPIiLTh7SWn2JciB0/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:30:34.678372');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('7701', 'Project Manager', 'project manager', true, 96, 'Mumbai', 'wfo', 'https://docs.google.com/document/d/1yy62tVB-F2FCqUyPH-obuP2XsLU_NspP/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:30:34.69774');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('5537', 'Project Manager', 'project manager', true, 108, 'Hyderabad', 'hybrid', 'https://docs.google.com/document/d/1gWDDuracuiOL48Ruk9-u36MoSS4yl7rZ/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:30:34.712907');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('1370', 'Lead', 'lead', true, 96, 'Mumbai', 'wfh', 'https://docs.google.com/document/d/1p6vYr5oIyTyvcpUo4z5AlsJyOsvfsVjW/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:30:34.728637');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('4870', 'Big Data Engineer', 'senior software engineer', true, 48, 'Hyderabad', 'hybrid', 'https://docs.google.com/document/d/1vSKhEPU-wciVWwwQ85qjlh7S1K83wW-j/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.46057');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('5981', 'Scala Spark Developer', 'project lead', true, 72, 'Mumbai', 'hybrid', 'https://docs.google.com/document/d/1mfzVDFXsmBGjP1ykL37SJd6YBJBTOwHG/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.480862');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('4205', 'Data Engineer', 'senior software engineer', true, 36, 'Hyderabad', 'wfo', 'https://docs.google.com/document/d/1xQey5WlcQLResAanK0OoxwarZfCSoRol/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.497421');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('2868', 'Software Engineer', 'lead', true, 48, 'Hyderabad', 'wfh', 'https://docs.google.com/document/d/1u_br8lS_KNEef0Ktib9XEON1mi6QHhf4/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.512745');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('9681', 'ETL Developer', 'project lead', true, 72, 'Hyderabad', 'wfh', 'https://docs.google.com/document/d/11Bx97D2-Ka8EKcLMPWJ4a-WTH-e0aZuM/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.527976');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('6017', 'Data Warehouse Architect', 'project manager', true, 60, 'Hyderabad', 'hybrid', 'https://docs.google.com/document/d/1DMl97IhbRLil-Z26Iwx9vGbicDMM4_ny/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.645997');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('8175', 'BI Developer', 'lead', true, 96, 'Bangalore', 'wfo', 'https://docs.google.com/document/d/11R4iguWU7q7medTKCPu-kzTu9t6mmoHM/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.665996');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('6681', 'Data Engineer', 'senior software engineer', true, 72, 'Bangalore', 'hybrid', 'https://docs.google.com/document/d/1mVx684poYpy15jSJozTJfoK2ylVwmTuI/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.683849');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('2748', 'SQL Developer', 'lead', true, 72, 'Bangalore', 'wfo', 'https://docs.google.com/document/d/1RALjRKFYbRjRtYm1YbBWvHyGq5zm1ng0/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.703826');
INSERT INTO public.team_member (team_member_id, designation, profile_type, is_active, experience_in_months, base_location, work_type, profile_url, created_at) VALUES ('8921', 'Reporting Analyst', 'senior software engineer', true, 72, 'Pune', 'wfo', 'https://docs.google.com/document/d/1fWIBtrsPp0M61rsQNG9jJX3DUkuWMRfG/edit?usp=drive_link&ouid=113977317040724991218&rtpof=true&sd=true', '2026-03-06 07:32:54.725561');


--
-- TOC entry 3829 (class 0 OID 24698)
-- Dependencies: 230
-- Data for Name: team_member_allocation; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('9413', '8199', 66.00, '2026-01-29', '2026-10-30', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('5536', '2457', 26.00, '2026-01-06', '2026-11-25', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('3090', '1964', 49.00, '2025-11-09', '2026-12-22', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('9963', '6342', 17.00, '2025-10-29', '2026-11-15', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('5974', '3684', 52.00, '2025-10-18', '2026-11-22', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('5597', '4287', 57.00, '2026-03-01', '2026-10-30', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('6248', '4531', 80.00, '2025-12-25', '2026-12-10', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('7701', '4839', 40.00, '2026-02-11', '2026-10-07', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('5537', '5445', 27.00, '2026-02-19', '2026-11-19', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('1370', '3483', 79.00, '2025-11-15', '2026-11-13', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('4974', '6437', 59.00, '2026-01-14', '2026-11-26', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('9744', '1943', 43.00, '2026-02-27', '2026-10-21', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('3757', '4042', 72.00, '2026-01-20', '2026-10-10', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('1989', '2513', 61.00, '2026-02-11', '2026-12-03', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('1237', '4033', 79.00, '2025-10-20', '2026-11-30', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('5716', '7417', 82.00, '2025-10-03', '2026-10-24', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('5392', '9494', 94.00, '2025-12-05', '2026-10-15', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('3780', '2202', 96.00, '2025-10-05', '2026-11-27', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('9567', '4479', 67.00, '2026-01-01', '2026-12-06', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('1458', '2961', 61.00, '2026-03-03', '2026-10-26', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('5700', '8532', 23.00, '2025-11-27', '2026-12-15', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('4399', '9714', 43.00, '2025-12-24', '2026-10-30', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('3061', '7444', 49.00, '2025-12-18', '2026-10-03', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('6679', '2594', 31.00, '2026-01-21', '2026-12-24', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('1276', '9766', 58.00, '2025-10-25', '2026-10-12', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('4870', '1154', 43.00, '2025-11-22', '2026-11-25', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('5981', '8634', 55.00, '2025-11-10', '2026-12-14', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('4205', '2833', 32.00, '2025-10-25', '2026-11-29', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('2868', '6967', 15.00, '2025-12-25', '2026-12-15', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('9681', '3489', 29.00, '2026-02-13', '2026-11-04', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('5678', '9881', 38.00, '2025-11-12', '2026-12-02', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('2549', '8955', 60.00, '2025-12-31', '2026-10-24', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('6047', '7799', 34.00, '2026-01-30', '2026-10-07', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('7268', '8046', 71.00, '2025-10-31', '2026-12-22', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('6017', '9751', 23.00, '2025-12-15', '2026-12-19', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('8175', '7803', 49.00, '2025-11-09', '2026-10-11', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('6681', '3012', 96.00, '2026-01-01', '2026-10-20', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('2748', '7034', 54.00, '2025-12-24', '2026-10-05', true, false);
INSERT INTO public.team_member_allocation (team_member_id, project_id, allocation_percentage, start_date, end_date, billable, is_deleted) VALUES ('8921', '5810', 71.00, '2025-11-06', '2026-11-04', true, false);


--
-- TOC entry 3838 (class 0 OID 25108)
-- Dependencies: 239
-- Data for Name: team_member_embeddings; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- TOC entry 3830 (class 0 OID 24709)
-- Dependencies: 231
-- Data for Name: team_member_skill; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5700', 'python-django', 4, 92, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5700', 'react-js', 4, 68, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5700', 'aws', 4, 86, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5700', 'ci-cd-unit-testing', 2, 101, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4399', 'python-django', 1, 94, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4399', 'react-js', 4, 82, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4399', 'azure', 3, 70, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4399', 'ci-cd-unit-testing', 5, 77, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3061', 'python-django', 1, 85, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3061', 'react-js', 3, 101, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3061', 'azure', 3, 104, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3061', 'ci-cd-unit-testing', 3, 107, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6679', 'python-django', 2, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6679', 'react-js', 3, 70, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6679', 'azure', 3, 119, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6679', 'ci-cd-unit-testing', 2, 67, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1276', 'scala-spark', 4, 27, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1276', 'mssql-nosql', 4, 22, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1276', 'aws-big-data-stack', 2, 26, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4870', 'scala-spark', 4, 41, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4870', 'mssql-nosql', 2, 32, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4870', 'aws-big-data-stack', 5, 29, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5981', 'scala-spark', 5, 58, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5981', 'mssql-nosql', 4, 35, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5981', 'aws-big-data-stack', 4, 60, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4205', 'scala-spark', 4, 30, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4205', 'mssql-nosql', 5, 19, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4205', 'aws-big-data-stack', 5, 24, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('2868', 'scala-spark', 3, 29, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('2868', 'mssql-nosql', 3, 26, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('2868', 'aws-big-data-stack', 4, 30, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9681', 'scala-spark', 4, 35, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5678', 'scala-spark', 1, 17, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5678', 'mssql-nosql', 2, 14, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5678', 'aws-big-data-stack', 2, 15, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('2549', 'scala-spark', 1, 29, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('2549', 'mssql-nosql', 3, 23, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('2549', 'aws-big-data-stack', 4, 23, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6047', 'scala-spark', 1, 31, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6047', 'mssql-nosql', 5, 70, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6047', 'aws-big-data-stack', 3, 67, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('7268', 'data-warehousing-etl', 4, 52, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('7268', 'vertica-mssql', 5, 64, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('7268', 'qlikview-tableau-power-bi', 4, 67, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6017', 'data-warehousing-etl', 4, 34, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6017', 'vertica-mssql', 4, 56, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6017', 'qlikview-tableau-power-bi', 2, 33, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('8175', 'data-warehousing-etl', 3, 76, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('8175', 'vertica-mssql', 3, 75, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('8175', 'qlikview-tableau-power-bi', 4, 49, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6681', 'data-warehousing-etl', 4, 47, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6681', 'vertica-mssql', 5, 40, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6681', 'qlikview-tableau-power-bi', 2, 41, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('2748', 'data-warehousing-etl', 2, 65, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('2748', 'vertica-mssql', 5, 50, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('2748', 'qlikview-tableau-power-bi', 3, 49, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('8921', 'data-warehousing-etl', 3, 51, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4974', 'prompt-engineering-openai-api-langchain-pinecone-c', 1, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4974', 'aws', 1, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('4974', 'mlops', 2, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9744', 'openai-api-langchain-basic-rag-advanced-machine-le', 2, 144, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9744', 'gcp', 4, 144, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9744', 'docker', 3, 144, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3757', 'machine-learning-nlp-limited-genai-exposure', 3, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3757', 'gcp', 3, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3757', 'kubernetes', 4, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1989', 'prompt-engineering-openai-api-langchain-pinecone-c', 3, 144, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1989', 'azure', 3, 144, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1989', 'docker', 4, 144, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1237', 'openai-api-langchain-basic-rag-advanced-machine-le', 1, 144, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1237', 'gcp', 3, 144, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1237', 'kubernetes', 3, 144, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5716', 'python-django', 5, 114, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5716', 'react-js', 5, 97, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5716', 'azure', 4, 113, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5716', 'ci-cd-unit-testing', 3, 62, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5392', 'python-django', 4, 105, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5392', 'react-js', 2, 119, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5392', 'aws', 5, 103, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5392', 'ci-cd-unit-testing', 5, 80, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3780', 'python-django', 5, 82, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3780', 'react-js', 5, 105, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3780', 'azure', 4, 80, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3780', 'ci-cd-unit-testing', 2, 92, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9567', 'python-django', 4, 88, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9567', 'react-js', 5, 103, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9681', 'mssql-nosql', 5, 38, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9413', 'prompt-engineering-openai-api-langchain-pinecone-c', 1, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9413', 'azure', 3, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9413', 'docker', 3, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5536', 'prompt-engineering-openai-api-langchain-pinecone-c', 5, 108, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5536', 'gcp', 4, 108, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5536', 'kubernetes', 5, 108, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3090', 'prompt-engineering-openai-api-langchain-pinecone-c', 3, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3090', 'gcp', 2, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('3090', 'mlops', 1, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9963', 'openai-api-langchain-basic-rag-advanced-machine-le', 2, 120, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9963', 'aws', 2, 120, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9963', 'kubernetes', 1, 120, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5974', 'openai-api-langchain-basic-rag-advanced-machine-le', 5, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5974', 'aws', 4, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5974', 'docker', 2, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5597', 'openai-api-langchain-basic-rag-advanced-machine-le', 4, 120, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5597', 'gcp', 5, 120, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5597', 'mlops', 2, 120, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6248', 'openai-api-langchain-basic-rag-advanced-machine-le', 4, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6248', 'aws', 4, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('6248', 'docker', 1, 132, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('7701', 'machine-learning-nlp-limited-genai-exposure', 4, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('7701', 'gcp', 4, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('7701', 'docker', 3, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5537', 'machine-learning-nlp-limited-genai-exposure', 3, 108, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5537', 'aws', 3, 108, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('5537', 'mlops', 5, 108, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1370', 'machine-learning-nlp-limited-genai-exposure', 4, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1370', 'gcp', 4, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1370', 'docker', 3, 96, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9567', 'aws', 3, 95, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9567', 'ci-cd-unit-testing', 3, 78, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1458', 'python-django', 4, 75, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1458', 'react-js', 3, 78, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1458', 'aws', 4, 81, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('1458', 'ci-cd-unit-testing', 2, 48, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('9681', 'aws-big-data-stack', 2, 28, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('8921', 'vertica-mssql', 4, 65, false);
INSERT INTO public.team_member_skill (team_member_id, skill_id, rating, experience_in_months, is_deleted) VALUES ('8921', 'qlikview-tableau-power-bi', 5, 41, false);


--
-- TOC entry 3832 (class 0 OID 24726)
-- Dependencies: 233
-- Data for Name: team_member_skill_certification; Type: TABLE DATA; Schema: public; Owner: user
--

INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (1, NULL, '5716', 'python-django', 'Microsoft Certified: Azure Developer Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (2, NULL, '5716', 'python-django', 'AWS Certified Developer – Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (3, NULL, '5716', 'azure', 'Azure Fundamentals', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (4, NULL, '5392', 'python-django', 'Microsoft Certified: Azure Developer Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (5, NULL, '5392', 'python-django', 'AWS Certified Developer – Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (6, NULL, '5392', 'aws', 'Azure Fundamentals', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (7, NULL, '3780', 'python-django', 'Microsoft Certified: Azure Developer Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (8, NULL, '3780', 'python-django', 'AWS Certified Developer – Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (9, NULL, '3780', 'azure', 'Azure Fundamentals', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (10, NULL, '1276', 'scala-spark', 'AWS Certified Data Analytics – Specialty', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (11, NULL, '4870', 'scala-spark', 'AWS Certified Data Analytics – Specialty', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (12, NULL, '5981', 'scala-spark', 'AWS Certified Data Analytics – Specialty', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (13, NULL, '7268', 'data-warehousing-etl', 'Qlik Certified Data Architect', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (14, NULL, '6017', 'data-warehousing-etl', 'Qlik Certified Data Architect', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (15, NULL, '5716', 'python-django', 'Microsoft Certified: Azure Developer Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (16, NULL, '5716', 'python-django', 'AWS Certified Developer – Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (17, NULL, '5716', 'azure', 'Azure Fundamentals', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (18, NULL, '5392', 'python-django', 'Microsoft Certified: Azure Developer Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (19, NULL, '5392', 'python-django', 'AWS Certified Developer – Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (20, NULL, '5392', 'aws', 'Azure Fundamentals', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (21, NULL, '3780', 'python-django', 'Microsoft Certified: Azure Developer Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (22, NULL, '3780', 'python-django', 'AWS Certified Developer – Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (23, NULL, '3780', 'azure', 'Azure Fundamentals', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (24, NULL, '1276', 'scala-spark', 'AWS Certified Data Analytics – Specialty', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (25, NULL, '4870', 'scala-spark', 'AWS Certified Data Analytics – Specialty', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (26, NULL, '5981', 'scala-spark', 'AWS Certified Data Analytics – Specialty', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (27, NULL, '7268', 'data-warehousing-etl', 'Qlik Certified Data Architect', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (28, NULL, '6017', 'data-warehousing-etl', 'Qlik Certified Data Architect', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (29, NULL, '5716', 'python-django', 'Microsoft Certified: Azure Developer Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (30, NULL, '5716', 'python-django', 'AWS Certified Developer – Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (31, NULL, '5716', 'azure', 'Azure Fundamentals', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (32, NULL, '5392', 'python-django', 'Microsoft Certified: Azure Developer Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (33, NULL, '5392', 'python-django', 'AWS Certified Developer – Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (34, NULL, '5392', 'aws', 'Azure Fundamentals', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (35, NULL, '3780', 'python-django', 'Microsoft Certified: Azure Developer Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (36, NULL, '3780', 'python-django', 'AWS Certified Developer – Associate', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (37, NULL, '3780', 'azure', 'Azure Fundamentals', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (38, NULL, '1276', 'scala-spark', 'AWS Certified Data Analytics – Specialty', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (39, NULL, '4870', 'scala-spark', 'AWS Certified Data Analytics – Specialty', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (40, NULL, '5981', 'scala-spark', 'AWS Certified Data Analytics – Specialty', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (41, NULL, '7268', 'data-warehousing-etl', 'Qlik Certified Data Architect', NULL, NULL, NULL);
INSERT INTO public.team_member_skill_certification (id, certification_id, team_member_id, skill_id, certificate, issuer, issued_date, valid_till) VALUES (42, NULL, '6017', 'data-warehousing-etl', 'Qlik Certified Data Architect', NULL, NULL, NULL);


--
-- TOC entry 3866 (class 0 OID 0)
-- Dependencies: 218
-- Name: auth_access_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.auth_access_tokens_id_seq', 1, false);


--
-- TOC entry 3867 (class 0 OID 0)
-- Dependencies: 216
-- Name: auth_clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.auth_clients_id_seq', 1, true);


--
-- TOC entry 3868 (class 0 OID 0)
-- Dependencies: 226
-- Name: category_master_category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.category_master_category_id_seq', 164, true);


--
-- TOC entry 3869 (class 0 OID 0)
-- Dependencies: 237
-- Name: ingestion_audit_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.ingestion_audit_log_id_seq', 78, true);


--
-- TOC entry 3870 (class 0 OID 0)
-- Dependencies: 246
-- Name: jd_certification_requirements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.jd_certification_requirements_id_seq', 1, false);


--
-- TOC entry 3871 (class 0 OID 0)
-- Dependencies: 234
-- Name: langgraph_checkpoints_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.langgraph_checkpoints_id_seq', 11, true);


--
-- TOC entry 3872 (class 0 OID 0)
-- Dependencies: 247
-- Name: pii_scrub_audit_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.pii_scrub_audit_id_seq', 1, false);


--
-- TOC entry 3873 (class 0 OID 0)
-- Dependencies: 224
-- Name: requisition_detail_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.requisition_detail_id_seq', 3, true);


--
-- TOC entry 3874 (class 0 OID 0)
-- Dependencies: 243
-- Name: requisition_match_team_member_feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.requisition_match_team_member_feedback_id_seq', 1, false);


--
-- TOC entry 3875 (class 0 OID 0)
-- Dependencies: 222
-- Name: requisition_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.requisition_requests_id_seq', 5, true);


--
-- TOC entry 3876 (class 0 OID 0)
-- Dependencies: 220
-- Name: requisition_status_master_status_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.requisition_status_master_status_id_seq', 1, false);


--
-- TOC entry 3877 (class 0 OID 0)
-- Dependencies: 232
-- Name: skill_certification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.skill_certification_id_seq', 42, true);


--
-- TOC entry 3878 (class 0 OID 0)
-- Dependencies: 245
-- Name: skill_ontology_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.skill_ontology_id_seq', 1, false);


--
-- TOC entry 3578 (class 2606 OID 24582)
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- TOC entry 3584 (class 2606 OID 24605)
-- Name: auth_access_tokens auth_access_tokens_access_token_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.auth_access_tokens
    ADD CONSTRAINT auth_access_tokens_access_token_key UNIQUE (access_token);


--
-- TOC entry 3586 (class 2606 OID 24603)
-- Name: auth_access_tokens auth_access_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.auth_access_tokens
    ADD CONSTRAINT auth_access_tokens_pkey PRIMARY KEY (id);


--
-- TOC entry 3580 (class 2606 OID 24594)
-- Name: auth_clients auth_clients_client_code_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.auth_clients
    ADD CONSTRAINT auth_clients_client_code_key UNIQUE (client_code);


--
-- TOC entry 3582 (class 2606 OID 24592)
-- Name: auth_clients auth_clients_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.auth_clients
    ADD CONSTRAINT auth_clients_pkey PRIMARY KEY (id);


--
-- TOC entry 3602 (class 2606 OID 24668)
-- Name: category_master category_master_category_name_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.category_master
    ADD CONSTRAINT category_master_category_name_key UNIQUE (category_name);


--
-- TOC entry 3604 (class 2606 OID 24666)
-- Name: category_master category_master_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.category_master
    ADD CONSTRAINT category_master_pkey PRIMARY KEY (category_id);


--
-- TOC entry 3624 (class 2606 OID 24771)
-- Name: ingestion_audit_log ingestion_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.ingestion_audit_log
    ADD CONSTRAINT ingestion_audit_log_pkey PRIMARY KEY (id);


--
-- TOC entry 3620 (class 2606 OID 24759)
-- Name: ingestion_batch_state ingestion_batch_state_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.ingestion_batch_state
    ADD CONSTRAINT ingestion_batch_state_pkey PRIMARY KEY (batch_id);


--
-- TOC entry 3644 (class 2606 OID 25200)
-- Name: jd_certification_requirements jd_certification_requirements_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.jd_certification_requirements
    ADD CONSTRAINT jd_certification_requirements_pkey PRIMARY KEY (id);


--
-- TOC entry 3618 (class 2606 OID 24746)
-- Name: langgraph_checkpoints langgraph_checkpoints_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.langgraph_checkpoints
    ADD CONSTRAINT langgraph_checkpoints_pkey PRIMARY KEY (id);


--
-- TOC entry 3636 (class 2606 OID 25132)
-- Name: llm_request_log llm_request_log_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.llm_request_log
    ADD CONSTRAINT llm_request_log_pkey PRIMARY KEY (id);


--
-- TOC entry 3657 (class 2606 OID 25213)
-- Name: pii_scrub_audit pii_scrub_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.pii_scrub_audit
    ADD CONSTRAINT pii_scrub_audit_pkey PRIMARY KEY (id, "timestamp");


--
-- TOC entry 3596 (class 2606 OID 24653)
-- Name: requisition_detail requisition_detail_payload_hash_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_detail
    ADD CONSTRAINT requisition_detail_payload_hash_key UNIQUE (payload_hash);


--
-- TOC entry 3598 (class 2606 OID 24649)
-- Name: requisition_detail requisition_detail_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_detail
    ADD CONSTRAINT requisition_detail_pkey PRIMARY KEY (id);


--
-- TOC entry 3600 (class 2606 OID 24651)
-- Name: requisition_detail requisition_detail_requisition_request_id_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_detail
    ADD CONSTRAINT requisition_detail_requisition_request_id_key UNIQUE (requisition_request_id);


--
-- TOC entry 3650 (class 2606 OID 25183)
-- Name: requisition_match_team_member_feedback requisition_match_team_member_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_match_team_member_feedback
    ADD CONSTRAINT requisition_match_team_member_feedback_pkey PRIMARY KEY (id);


--
-- TOC entry 3592 (class 2606 OID 24627)
-- Name: requisition_requests requisition_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_requests
    ADD CONSTRAINT requisition_requests_pkey PRIMARY KEY (id);


--
-- TOC entry 3594 (class 2606 OID 24629)
-- Name: requisition_requests requisition_requests_request_id_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_requests
    ADD CONSTRAINT requisition_requests_request_id_key UNIQUE (request_id);


--
-- TOC entry 3588 (class 2606 OID 24617)
-- Name: requisition_status_master requisition_status_master_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_status_master
    ADD CONSTRAINT requisition_status_master_pkey PRIMARY KEY (status_id);


--
-- TOC entry 3590 (class 2606 OID 24619)
-- Name: requisition_status_master requisition_status_master_status_key_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_status_master
    ADD CONSTRAINT requisition_status_master_status_key_key UNIQUE (status_key);


--
-- TOC entry 3616 (class 2606 OID 24731)
-- Name: team_member_skill_certification skill_certification_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_skill_certification
    ADD CONSTRAINT skill_certification_pkey PRIMARY KEY (id);


--
-- TOC entry 3606 (class 2606 OID 24674)
-- Name: skill_master skill_master_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.skill_master
    ADD CONSTRAINT skill_master_pkey PRIMARY KEY (skill_id);


--
-- TOC entry 3608 (class 2606 OID 24676)
-- Name: skill_master skill_master_skill_name_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.skill_master
    ADD CONSTRAINT skill_master_skill_name_key UNIQUE (skill_name);


--
-- TOC entry 3639 (class 2606 OID 25196)
-- Name: skill_ontology skill_ontology_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.skill_ontology
    ADD CONSTRAINT skill_ontology_pkey PRIMARY KEY (id);


--
-- TOC entry 3612 (class 2606 OID 24703)
-- Name: team_member_allocation team_member_allocation_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_allocation
    ADD CONSTRAINT team_member_allocation_pkey PRIMARY KEY (team_member_id, project_id);


--
-- TOC entry 3632 (class 2606 OID 25116)
-- Name: team_member_embeddings team_member_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_embeddings
    ADD CONSTRAINT team_member_embeddings_pkey PRIMARY KEY (id);


--
-- TOC entry 3610 (class 2606 OID 24697)
-- Name: team_member team_member_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member
    ADD CONSTRAINT team_member_pkey PRIMARY KEY (team_member_id);


--
-- TOC entry 3614 (class 2606 OID 24714)
-- Name: team_member_skill team_member_skill_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_skill
    ADD CONSTRAINT team_member_skill_pkey PRIMARY KEY (team_member_id, skill_id);


--
-- TOC entry 3652 (class 2606 OID 25185)
-- Name: requisition_match_team_member_feedback uq_feedback_reviewer_match; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_match_team_member_feedback
    ADD CONSTRAINT uq_feedback_reviewer_match UNIQUE (team_member_id, correlation_id, reviewer_email);


--
-- TOC entry 3646 (class 2606 OID 25202)
-- Name: jd_certification_requirements uq_jd_cert_combo; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.jd_certification_requirements
    ADD CONSTRAINT uq_jd_cert_combo UNIQUE (jd_type, certification);


--
-- TOC entry 3641 (class 2606 OID 25152)
-- Name: skill_ontology uq_skill_ontology_core_skill; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.skill_ontology
    ADD CONSTRAINT uq_skill_ontology_core_skill UNIQUE (core_skill);


--
-- TOC entry 3647 (class 1259 OID 25186)
-- Name: idx_feedback_correlation_id; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX idx_feedback_correlation_id ON public.requisition_match_team_member_feedback USING btree (correlation_id);


--
-- TOC entry 3648 (class 1259 OID 25187)
-- Name: idx_feedback_team_member_id; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX idx_feedback_team_member_id ON public.requisition_match_team_member_feedback USING btree (team_member_id);


--
-- TOC entry 3642 (class 1259 OID 25150)
-- Name: idx_jd_certification_jd_type; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX idx_jd_certification_jd_type ON public.jd_certification_requirements USING btree (jd_type);


--
-- TOC entry 3633 (class 1259 OID 25134)
-- Name: idx_llm_request_log_agent_name; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX idx_llm_request_log_agent_name ON public.llm_request_log USING btree (agent_name);


--
-- TOC entry 3634 (class 1259 OID 25155)
-- Name: idx_llm_request_log_request_id_created_at; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX idx_llm_request_log_request_id_created_at ON public.llm_request_log USING btree (request_id, created_at);


--
-- TOC entry 3637 (class 1259 OID 25142)
-- Name: idx_skill_ontology_core_skill; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX idx_skill_ontology_core_skill ON public.skill_ontology USING btree (core_skill);


--
-- TOC entry 3628 (class 1259 OID 25123)
-- Name: idx_team_member_embeddings_created_at; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX idx_team_member_embeddings_created_at ON public.team_member_embeddings USING btree (created_at);


--
-- TOC entry 3629 (class 1259 OID 25122)
-- Name: idx_team_member_embeddings_team_member_id; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX idx_team_member_embeddings_team_member_id ON public.team_member_embeddings USING btree (team_member_id);


--
-- TOC entry 3625 (class 1259 OID 24777)
-- Name: ix_ingestion_audit_log_batch_id; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_ingestion_audit_log_batch_id ON public.ingestion_audit_log USING btree (batch_id);


--
-- TOC entry 3626 (class 1259 OID 24778)
-- Name: ix_ingestion_audit_log_correlation_id; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_ingestion_audit_log_correlation_id ON public.ingestion_audit_log USING btree (correlation_id);


--
-- TOC entry 3627 (class 1259 OID 24779)
-- Name: ix_ingestion_audit_log_timestamp; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_ingestion_audit_log_timestamp ON public.ingestion_audit_log USING btree ("timestamp");


--
-- TOC entry 3621 (class 1259 OID 24760)
-- Name: ix_ingestion_batch_state_correlation_id; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_ingestion_batch_state_correlation_id ON public.ingestion_batch_state USING btree (correlation_id);


--
-- TOC entry 3622 (class 1259 OID 24761)
-- Name: ix_ingestion_batch_state_status; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_ingestion_batch_state_status ON public.ingestion_batch_state USING btree (status);


--
-- TOC entry 3653 (class 1259 OID 25215)
-- Name: ix_pii_scrub_audit_entity; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_pii_scrub_audit_entity ON ONLY public.pii_scrub_audit USING btree (entity_type, entity_id);


--
-- TOC entry 3654 (class 1259 OID 25216)
-- Name: ix_pii_scrub_audit_operation; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_pii_scrub_audit_operation ON ONLY public.pii_scrub_audit USING btree (operation, "timestamp");


--
-- TOC entry 3655 (class 1259 OID 25214)
-- Name: ix_pii_scrub_audit_timestamp; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_pii_scrub_audit_timestamp ON ONLY public.pii_scrub_audit USING btree ("timestamp");


--
-- TOC entry 3630 (class 1259 OID 25221)
-- Name: ix_team_member_embeddings_pii_scrubbed; Type: INDEX; Schema: public; Owner: user
--

CREATE INDEX ix_team_member_embeddings_pii_scrubbed ON public.team_member_embeddings USING btree (pii_scrubbed);


--
-- TOC entry 3671 (class 2620 OID 25218)
-- Name: pii_scrub_audit prevent_pii_audit_modification_trigger; Type: TRIGGER; Schema: public; Owner: user
--

CREATE TRIGGER prevent_pii_audit_modification_trigger BEFORE DELETE OR UPDATE ON public.pii_scrub_audit FOR EACH ROW EXECUTE FUNCTION public.prevent_pii_audit_modification();


--
-- TOC entry 3670 (class 2620 OID 25189)
-- Name: requisition_match_team_member_feedback update_feedback_updated_at; Type: TRIGGER; Schema: public; Owner: user
--

CREATE TRIGGER update_feedback_updated_at BEFORE UPDATE ON public.requisition_match_team_member_feedback FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3658 (class 2606 OID 24606)
-- Name: auth_access_tokens auth_access_tokens_auth_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.auth_access_tokens
    ADD CONSTRAINT auth_access_tokens_auth_client_id_fkey FOREIGN KEY (auth_client_id) REFERENCES public.auth_clients(id);


--
-- TOC entry 3668 (class 2606 OID 24772)
-- Name: ingestion_audit_log ingestion_audit_log_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.ingestion_audit_log
    ADD CONSTRAINT ingestion_audit_log_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.ingestion_batch_state(batch_id) ON DELETE CASCADE;


--
-- TOC entry 3667 (class 2606 OID 24747)
-- Name: langgraph_checkpoints langgraph_checkpoints_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.langgraph_checkpoints
    ADD CONSTRAINT langgraph_checkpoints_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.requisition_requests(request_id);


--
-- TOC entry 3661 (class 2606 OID 24654)
-- Name: requisition_detail requisition_detail_requisition_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_detail
    ADD CONSTRAINT requisition_detail_requisition_request_id_fkey FOREIGN KEY (requisition_request_id) REFERENCES public.requisition_requests(id);


--
-- TOC entry 3659 (class 2606 OID 24630)
-- Name: requisition_requests requisition_requests_auth_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_requests
    ADD CONSTRAINT requisition_requests_auth_client_id_fkey FOREIGN KEY (auth_client_id) REFERENCES public.auth_clients(id);


--
-- TOC entry 3660 (class 2606 OID 24635)
-- Name: requisition_requests requisition_requests_status_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.requisition_requests
    ADD CONSTRAINT requisition_requests_status_fkey FOREIGN KEY (status) REFERENCES public.requisition_status_master(status_id);


--
-- TOC entry 3666 (class 2606 OID 24732)
-- Name: team_member_skill_certification skill_certification_team_member_id_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_skill_certification
    ADD CONSTRAINT skill_certification_team_member_id_skill_id_fkey FOREIGN KEY (team_member_id, skill_id) REFERENCES public.team_member_skill(team_member_id, skill_id);


--
-- TOC entry 3662 (class 2606 OID 24677)
-- Name: skill_master skill_master_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.skill_master
    ADD CONSTRAINT skill_master_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.category_master(category_id);


--
-- TOC entry 3663 (class 2606 OID 24704)
-- Name: team_member_allocation team_member_allocation_team_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_allocation
    ADD CONSTRAINT team_member_allocation_team_member_id_fkey FOREIGN KEY (team_member_id) REFERENCES public.team_member(team_member_id);


--
-- TOC entry 3669 (class 2606 OID 25117)
-- Name: team_member_embeddings team_member_embeddings_team_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_embeddings
    ADD CONSTRAINT team_member_embeddings_team_member_id_fkey FOREIGN KEY (team_member_id) REFERENCES public.team_member(team_member_id);


--
-- TOC entry 3664 (class 2606 OID 24720)
-- Name: team_member_skill team_member_skill_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_skill
    ADD CONSTRAINT team_member_skill_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skill_master(skill_id);


--
-- TOC entry 3665 (class 2606 OID 24715)
-- Name: team_member_skill team_member_skill_team_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.team_member_skill
    ADD CONSTRAINT team_member_skill_team_member_id_fkey FOREIGN KEY (team_member_id) REFERENCES public.team_member(team_member_id);


-- Completed on 2026-03-09 12:12:06

--
-- PostgreSQL database dump complete
--

\unrestrict RXuJiDoQL5xh7u7XNfayzeWcBmDdmIVJwhuSehama9FYJF9R6zv1fbXz0q8Bl2O

