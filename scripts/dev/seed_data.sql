-- Insert categories
INSERT INTO category_master (category_name) VALUES
  ('Backend Development'),
  ('Cloud & Infrastructure'),
  ('AI & ML'),
  ('Frontend Development'),
  ('DevOps & Tools'),
  ('Data & Analytics')
ON CONFLICT (category_name) DO NOTHING;

-- Insert skills
INSERT INTO skill_master (skill_id, skill_name, category_id) VALUES
  ('python', 'Python', (SELECT category_id FROM category_master WHERE category_name = 'Backend Development')),
  ('dotnet', '.NET', (SELECT category_id FROM category_master WHERE category_name = 'Backend Development')),
  ('fastapi', 'FastAPI', (SELECT category_id FROM category_master WHERE category_name = 'Backend Development')),
  ('postgresql', 'PostgreSQL', (SELECT category_id FROM category_master WHERE category_name = 'Data & Analytics')),
  ('azure', 'Azure', (SELECT category_id FROM category_master WHERE category_name = 'Cloud & Infrastructure')),
  ('aws', 'AWS', (SELECT category_id FROM category_master WHERE category_name = 'Cloud & Infrastructure')),
  ('kubernetes', 'Kubernetes', (SELECT category_id FROM category_master WHERE category_name = 'DevOps & Tools')),
  ('langchain', 'LangChain', (SELECT category_id FROM category_master WHERE category_name = 'AI & ML')),
  ('langgraph', 'LangGraph', (SELECT category_id FROM category_master WHERE category_name = 'AI & ML')),
  ('react', 'React', (SELECT category_id FROM category_master WHERE category_name = 'Frontend Development'))
ON CONFLICT (skill_name) DO NOTHING;

-- Insert requisition status values
INSERT INTO requisition_status_master (status_id, status_key, status_message) VALUES
  (1, 'RECEIVED', 'Requisition received and queued for processing'),
  (2, 'PROCESSING', 'Requisition is being processed'),
  (3, 'MATCHING', 'Finding skill matches'),
  (4, 'COMPLETED', 'Requisition processing completed'),
  (5, 'FAILED', 'Requisition processing failed')
ON CONFLICT (status_key) DO NOTHING;

-- Insert skill certification requirements
INSERT INTO skill_certification (role_name, required_skills, desired_skills, years_of_experience) VALUES
  ('Backend Engineer', '["python", "postgresql"]', '["fastapi", "aws"]', 3),
  ('Cloud Engineer', '["azure", "kubernetes"]', '["aws", "postgresql"]', 4),
  ('AI Engineer', '["python", "langchain", "langgraph"]', '["azure", "aws"]', 2),
  ('Full Stack Engineer', '["react", "python", "postgresql"]', '["aws", "kubernetes"]', 3),
  ('DevOps Engineer', '["kubernetes", "azure"]', '["aws", "dotnet"]', 4),
  ('Data Engineer', '["python", "postgresql"]', '["aws", "azure"]', 3)
ON CONFLICT (role_name) DO NOTHING;

-- Display inserted data
SELECT 'Categories:' as section;
SELECT * FROM category_master;
SELECT 'Skills:' as section;
SELECT * FROM skill_master;
SELECT 'Status:' as section;
SELECT * FROM requisition_status_master;
SELECT 'Certifications:' as section;
SELECT * FROM skill_certification;
