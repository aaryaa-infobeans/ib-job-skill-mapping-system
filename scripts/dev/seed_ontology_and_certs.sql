-- Seed skill_ontology table with comprehensive skill mapping
INSERT INTO skill_ontology (core_skill, enriched_terms) VALUES
  ('.net', ARRAY['windows development', 'c#', 'asp.net', 'microsoft stack', 'mvc']),
  ('python', ARRAY['backend', 'scripting', 'data engineering', 'ai foundation', 'django', 'flask']),
  ('fastapi', ARRAY['api development', 'asyncio', 'rest', 'backend', 'async programming']),
  ('langchain', ARRAY['llm orchestration', 'agentic ai', 'prompt engineering', 'rag', 'chains']),
  ('wordpress', ARRAY['cms', 'php', 'web development', 'content management', 'plugins']),
  ('react', ARRAY['frontend', 'javascript', 'ui development', 'jsx', 'spa']),
  ('aws', ARRAY['cloud computing', 'serverless', 'infrastructure', 'ec2', 'lambda']),
  ('java', ARRAY['enterprise', 'spring boot', 'backend', 'jvm', 'microservices']),
  ('openai', ARRAY['llm', 'generative ai', 'gpt', 'ai development', 'embeddings']),
  ('vector databases', ARRAY['pinecone', 'milvus', 'qdrant', 'weaviate', 'rag', 'similarity search']),
  ('docker', ARRAY['containerization', 'devops', 'kubernetes', 'ci/cd', 'containers'])
ON CONFLICT (core_skill) DO NOTHING;

-- Seed jd_certification_requirements table
INSERT INTO jd_certification_requirements (jd_type, certification) VALUES
  ('AI Engineer', 'AWS ML'),
  ('AI Engineer', 'Azure AI'),
  ('AI Engineer', 'GCP ML'),
  ('Cloud Engineer', 'AWS SA'),
  ('Cloud Engineer', 'Azure Admin'),
  ('Cloud Engineer', 'AWS DevOps'),
  ('Backend Engineer', 'Oracle Java'),
  ('Backend Engineer', 'Spring Certification'),
  ('Backend Engineer', 'AWS Developer'),
  ('Full Stack Engineer', 'AWS SA'),
  ('Full Stack Engineer', 'Azure Developer'),
  ('DevOps Engineer', 'AWS DevOps'),
  ('DevOps Engineer', 'Kubernetes CKA'),
  ('Data Engineer', 'AWS Data Analytics'),
  ('Data Engineer', 'GCP Data Engineering')
ON CONFLICT (jd_type, certification) DO NOTHING;

-- Verify inserts
SELECT COUNT(*) as ontology_count FROM skill_ontology;
SELECT COUNT(*) as cert_requirement_count FROM jd_certification_requirements;
