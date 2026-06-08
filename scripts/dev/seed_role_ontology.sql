-- ============================================================================
-- Seed: role_ontology
-- ============================================================================
-- Each row maps one canonical_role to:
--   profile_type   — matches team_member.profile_type (internal short code)
--   aliases        — other names for the SAME role (not adjacent roles)
--   enriched_terms — domain concepts strictly scoped to that role
--
-- Discipline: aliases and enriched_terms must NOT bleed into adjacent domains.
--   Backend Engineer  → no AI/ML, no frontend, no DevOps terms
--   AI Engineer       → no generic backend web dev, no frontend terms
--   QA Engineer       → no architecture, no product management terms
--   etc.
-- ============================================================================

INSERT INTO role_ontology (canonical_role, profile_type, aliases, enriched_terms) VALUES

  -- ── Backend Engineer ────────────────────────────────────────────────────────
  (
    'Backend Engineer',
    'developer',
    ARRAY['Backend Developer', 'Python Developer', 'Java Developer', 'Node.js Developer',
          'Server-Side Engineer', 'API Developer', 'Software Engineer - Backend'],
    ARRAY['rest api', 'microservices', 'server-side', 'api development', 'python', 'java',
          'node.js', 'postgresql', 'spring boot', 'fastapi', 'django', 'flask', 'grpc',
          'message queues', 'database design', 'backend', 'sql']
  ),

  -- ── Frontend Engineer ───────────────────────────────────────────────────────
  (
    'Frontend Engineer',
    'developer',
    ARRAY['UI Developer', 'Frontend Developer', 'React Developer', 'Web Developer',
          'JavaScript Developer', 'Angular Developer', 'Vue Developer'],
    ARRAY['react', 'javascript', 'html', 'css', 'typescript', 'frontend', 'spa',
          'responsive design', 'angular', 'vue', 'webpack', 'vite', 'ui development',
          'cross-browser compatibility', 'accessibility', 'state management', 'redux']
  ),

  -- ── Full Stack Engineer ─────────────────────────────────────────────────────
  (
    'Full Stack Engineer',
    'developer',
    ARRAY['Full Stack Developer', 'Web Application Developer', 'MERN Developer',
          'MEAN Developer', 'Full-Stack Software Engineer'],
    ARRAY['react', 'node.js', 'javascript', 'typescript', 'python', 'rest api',
          'database', 'frontend', 'backend', 'full stack', 'html', 'css', 'sql',
          'docker', 'api integration']
  ),

  -- ── Software Engineer ───────────────────────────────────────────────────────
  -- Generic catch-all; used when the role is not further specialised
  (
    'Software Engineer',
    'developer',
    ARRAY['Software Developer', 'Application Developer', 'Programmer',
          'Associate Software Engineer', 'Trainee Software Engineer', 'On Job Trainee'],
    ARRAY['software development', 'programming', 'object-oriented', 'design patterns',
          'version control', 'agile', 'unit testing', 'code review', 'debugging',
          'sdlc', 'git', 'java', 'python', 'c#']
  ),

  -- ── Support Engineer ────────────────────────────────────────────────────────
  (
    'Support Engineer',
    'developer',
    ARRAY['Technical Support Engineer', 'Application Support Engineer',
          'L2 Support Engineer', 'Billing Support Engineer', 'Senior Support Engineer',
          'Systems Engineer', 'Application Support Analyst'],
    ARRAY['troubleshooting', 'incident management', 'support tickets', 'debugging',
          'root cause analysis', 'jira', 'customer support', 'escalation management',
          'sla', 'production support', 'monitoring', 'log analysis']
  ),

  -- ── AI Engineer ─────────────────────────────────────────────────────────────
  -- Strictly AI/ML domain — no generic backend web dev terms
  (
    'AI Engineer',
    'developer',
    ARRAY['ML Engineer', 'Machine Learning Engineer', 'AI/ML Engineer',
          'GenAI Engineer', 'LLM Engineer', 'Applied AI Engineer'],
    ARRAY['python', 'machine learning', 'large language models', 'llm', 'neural networks',
          'pytorch', 'tensorflow', 'mlops', 'model training', 'fine-tuning', 'rag',
          'vector databases', 'generative ai', 'transformers', 'hugging face',
          'ai pipelines', 'prompt engineering', 'embeddings', 'langchain']
  ),

  -- ── Data Engineer ───────────────────────────────────────────────────────────
  -- Data pipeline domain — no AI model training, no frontend
  (
    'Data Engineer',
    'developer',
    ARRAY['Data Pipeline Engineer', 'ETL Developer', 'Big Data Engineer',
          'Analytics Engineer', 'Data Platform Engineer'],
    ARRAY['python', 'apache spark', 'pyspark', 'kafka', 'airflow', 'dbt', 'sql',
          'data pipelines', 'etl', 'databricks', 'snowflake', 'hadoop', 'hive',
          'data warehousing', 'data lake', 'aws glue', 'orchestration', 'batch processing']
  ),

  -- ── Data Scientist ──────────────────────────────────────────────────────────
  -- Statistical modelling and analysis — distinct from Data Engineer and AI Engineer
  (
    'Data Scientist',
    'developer',
    ARRAY['ML Researcher', 'Applied Scientist', 'Data Science Engineer',
          'Quantitative Analyst'],
    ARRAY['python', 'statistics', 'machine learning', 'data analysis', 'pandas',
          'numpy', 'scikit-learn', 'r', 'jupyter', 'data visualisation', 'matplotlib',
          'seaborn', 'predictive modelling', 'hypothesis testing', 'a/b testing',
          'feature engineering', 'regression', 'classification']
  ),

  -- ── DevOps Engineer ─────────────────────────────────────────────────────────
  -- Infrastructure and CI/CD domain — no application development, no AI/ML
  (
    'DevOps Engineer',
    'developer',
    ARRAY['Platform Engineer', 'Site Reliability Engineer', 'SRE',
          'Cloud Engineer', 'Infrastructure Engineer'],
    ARRAY['docker', 'kubernetes', 'terraform', 'ci/cd', 'jenkins', 'github actions',
          'aws', 'azure', 'gcp', 'linux', 'infrastructure as code', 'monitoring',
          'helm', 'ansible', 'prometheus', 'grafana', 'devops', 'bash scripting',
          'networking', 'load balancing']
  ),

  -- ── Technical Lead ──────────────────────────────────────────────────────────
  (
    'Technical Lead',
    'lead',
    ARRAY['Tech Lead', 'Team Lead', 'Engineering Lead', 'Module Lead',
          'Senior Technical Lead', 'Engineering Leader', 'Lead - Frontend Engineering',
          'Senior Lead - Frontend Engineering', 'Project Lead', 'Senior Project Lead'],
    ARRAY['technical leadership', 'code review', 'architecture decisions', 'mentoring',
          'sprint planning', 'team guidance', 'delivery', 'design review',
          'technical roadmap', 'cross-team collaboration', 'estimation']
  ),

  -- ── QA Engineer ─────────────────────────────────────────────────────────────
  (
    'QA Engineer',
    'qa',
    ARRAY['Quality Assurance Engineer', 'Test Engineer', 'Software Test Engineer',
          'QA Analyst', 'Automation Engineer', 'Associate QA Engineer',
          'Trainee QA Engineer', 'QA Consultant', 'Lead QA Engineer'],
    ARRAY['test automation', 'manual testing', 'selenium', 'regression testing',
          'test cases', 'bug reporting', 'test planning', 'postman', 'jira',
          'quality assurance', 'acceptance testing', 'functional testing',
          'api testing', 'test scripts', 'defect management']
  ),

  -- ── QA Manager ──────────────────────────────────────────────────────────────
  -- Senior QA leadership — distinct from hands-on QA Engineer
  (
    'QA Manager',
    'qa',
    ARRAY['Senior QA Manager', 'Associate QA Manager', 'QA Lead', 'Senior QA Lead',
          'Module Lead - Quality Assurance', 'Lead - Quality Assurance'],
    ARRAY['test strategy', 'qa governance', 'test management', 'team leadership',
          'quality metrics', 'release sign-off', 'test planning', 'risk-based testing',
          'process improvement', 'sla', 'defect triage', 'vendor management']
  ),

  -- ── UX Designer ─────────────────────────────────────────────────────────────
  (
    'UX Designer',
    'designer',
    ARRAY['User Experience Designer', 'Product Designer', 'UI/UX Designer',
          'Senior UX Designer', 'Associate UX Designer', 'Senior Product Designer',
          'Lead - UX Design', 'Delivery Manager - UX'],
    ARRAY['figma', 'wireframing', 'prototyping', 'user research', 'usability testing',
          'design thinking', 'personas', 'user flows', 'information architecture',
          'interaction design', 'sketch', 'invision', 'ux writing', 'accessibility']
  ),

  -- ── UI Designer ─────────────────────────────────────────────────────────────
  (
    'UI Designer',
    'designer',
    ARRAY['User Interface Designer', 'Visual Designer', 'Graphic Designer',
          'Senior UI Designer', 'Instructional Designer', 'Lead - Product Design'],
    ARRAY['visual design', 'adobe xd', 'figma', 'typography', 'color theory',
          'ui components', 'design system', 'branding', 'adobe photoshop',
          'adobe illustrator', 'motion design', 'style guides', 'iconography']
  ),

  -- ── Business Analyst ────────────────────────────────────────────────────────
  (
    'Business Analyst',
    'ba',
    ARRAY['BA', 'Business Systems Analyst', 'Requirements Analyst',
          'Functional Analyst', 'Associate Business Analyst', 'Lead Business Analyst'],
    ARRAY['requirements gathering', 'user stories', 'process mapping',
          'stakeholder management', 'brd', 'functional specifications', 'gap analysis',
          'use cases', 'as-is to-be', 'business process', 'workshops', 'fit gap',
          'jira', 'confluence', 'data flow diagrams']
  ),

  -- ── Consultant ──────────────────────────────────────────────────────────────
  (
    'Consultant',
    'consultant',
    ARRAY['Technology Consultant', 'IT Consultant', 'Implementation Consultant',
          'Associate Consultant', 'Digital Consultant'],
    ARRAY['consulting', 'client engagement', 'solution design', 'implementation',
          'advisory', 'change management', 'stakeholder communication',
          'requirements analysis', 'process improvement', 'workshop facilitation']
  ),

  -- ── Senior Consultant ───────────────────────────────────────────────────────
  (
    'Senior Consultant',
    'senior consultant',
    ARRAY['Principal Consultant', 'Senior Technology Consultant', 'Senior Lead Consultant'],
    ARRAY['senior consulting', 'solution architecture', 'client management',
          'pre-sales', 'proposal writing', 'delivery oversight', 'practice development',
          'escalation handling', 'account management']
  ),

  -- ── Lead Consultant ─────────────────────────────────────────────────────────
  (
    'Lead Consultant',
    'lead consultant',
    ARRAY['Consulting Lead', 'Principal Lead Consultant'],
    ARRAY['consulting leadership', 'practice leadership', 'client strategy',
          'solution governance', 'team mentoring', 'business development',
          'architecture review', 'delivery governance']
  ),

  -- ── Technical Architect ─────────────────────────────────────────────────────
  (
    'Technical Architect',
    'technical architect',
    ARRAY['Application Architect', 'Enterprise Architect', 'Software Architect',
          'Associate Technical Architect'],
    ARRAY['solution architecture', 'system design', 'cloud architecture',
          'microservices', 'integration patterns', 'non-functional requirements',
          'design principles', 'technical strategy', 'architecture review board',
          'reference architecture', 'technology selection', 'api design']
  ),

  -- ── Senior Technical Architect ──────────────────────────────────────────────
  (
    'Senior Technical Architect',
    'senior technical architect',
    ARRAY['Principal Architect', 'Chief Architect', 'Enterprise Technical Architect'],
    ARRAY['enterprise architecture', 'solution governance', 'technology strategy',
          'cloud architecture', 'microservices', 'integration architecture',
          'architecture roadmap', 'reference architecture', 'security architecture',
          'togaf', 'design authority']
  ),

  -- ── Solution Architect ──────────────────────────────────────────────────────
  (
    'Solution Architect',
    'solution architect',
    ARRAY['Solutions Architect', 'Enterprise Solutions Architect',
          'Associate Architect'],
    ARRAY['solution design', 'rfp', 'pre-sales architecture', 'cloud', 'integration',
          'enterprise architecture', 'stakeholder presentation', 'bid support',
          'architecture diagrams', 'technical scoping', 'sow preparation']
  ),

  -- ── Project Manager ─────────────────────────────────────────────────────────
  (
    'Project Manager',
    'project manager',
    ARRAY['PM', 'IT Project Manager', 'Software Project Manager',
          'Associate Project Manager'],
    ARRAY['project planning', 'delivery', 'stakeholder management', 'agile',
          'waterfall', 'risk management', 'milestones', 'resource planning',
          'budgeting', 'status reporting', 'project charter', 'change control',
          'ms project', 'jira', 'gantt chart']
  ),

  -- ── Technical Project Manager ───────────────────────────────────────────────
  (
    'Technical Project Manager',
    'technical project manager',
    ARRAY['TPM', 'Associate Technical Project Manager',
          'Senior Technical Project Manager'],
    ARRAY['technical project management', 'engineering delivery', 'sprint planning',
          'technical risk', 'release management', 'agile', 'stakeholder management',
          'cross-functional coordination', 'dependency management', 'sdlc', 'jira']
  ),

  -- ── Product Manager ─────────────────────────────────────────────────────────
  (
    'Product Manager',
    'product manager',
    ARRAY['Digital Product Manager', 'Product Lead', 'Senior Product Manager'],
    ARRAY['product roadmap', 'user stories', 'backlog', 'product strategy',
          'go-to-market', 'kpis', 'product discovery', 'competitive analysis',
          'customer interviews', 'mvp', 'prioritisation', 'product metrics']
  ),

  -- ── Product Owner ───────────────────────────────────────────────────────────
  (
    'Product Owner',
    'product owner',
    ARRAY['PO', 'Scrum Product Owner', 'Agile Product Owner'],
    ARRAY['backlog management', 'user stories', 'sprint planning', 'scrum',
          'product vision', 'acceptance criteria', 'stakeholder coordination',
          'mvp', 'definition of done', 'refinement', 'sprint review']
  ),

  -- ── Delivery Manager ────────────────────────────────────────────────────────
  (
    'Delivery Manager',
    'delivery manager',
    ARRAY['Engagement Manager', 'Service Delivery Manager', 'Client Delivery Manager',
          'Delivery Manager - UX'],
    ARRAY['delivery management', 'client management', 'agile delivery',
          'project oversight', 'resource management', 'sla', 'escalation management',
          'reporting', 'team performance', 'continuous improvement']
  ),

  -- ── Senior Delivery Manager ─────────────────────────────────────────────────
  (
    'Senior Delivery Manager',
    'senior delivery manager',
    ARRAY['Senior Engagement Manager', 'Senior Service Delivery Manager',
          'Senior Delivery Manager - UX'],
    ARRAY['senior delivery management', 'portfolio delivery', 'p&l oversight',
          'client strategy', 'account growth', 'escalation governance',
          'delivery excellence', 'risk management', 'sla governance']
  ),

  -- ── Scrum Master ────────────────────────────────────────────────────────────
  (
    'Senior Scrum Master',
    'senior scrum master',
    ARRAY['Scrum Master', 'Agile Coach', 'Agile Delivery Lead'],
    ARRAY['scrum', 'agile ceremonies', 'sprint planning', 'retrospectives',
          'impediment removal', 'team coaching', 'safe', 'kanban', 'velocity',
          'burndown', 'agile transformation', 'jira', 'confluence']
  ),

  -- ── Manager ─────────────────────────────────────────────────────────────────
  (
    'Manager',
    'manager',
    ARRAY['Associate Manager', 'Assistant Manager', 'Support Manager',
          'Manager - Delivery Office'],
    ARRAY['people management', 'team leadership', 'performance management',
          'stakeholder communication', 'resource allocation', 'goal setting',
          'appraisals', 'reporting', 'process management']
  ),

  -- ── Technical Manager ───────────────────────────────────────────────────────
  (
    'Technical Manager',
    'technical manager',
    ARRAY['Associate Technical Manager', 'Senior Technical Manager',
          'Engineering Manager'],
    ARRAY['engineering management', 'technical oversight', 'delivery management',
          'team building', 'sprint planning', 'architecture review', 'mentoring',
          'hiring', 'performance management', 'technical roadmap']
  ),

  -- ── Director ────────────────────────────────────────────────────────────────
  (
    'Director',
    'director',
    ARRAY['Technology Director', 'IT Director', 'Engineering Director',
          'Director of Engineering', 'Director - Sales', 'Director, Delivery',
          'Associate Director', 'Associate Director, Engineering'],
    ARRAY['leadership', 'strategy', 'team building', 'stakeholder management',
          'organisational design', 'talent development', 'p&l', 'business growth',
          'client relationships', 'budget management']
  ),

  -- ── Senior Director ─────────────────────────────────────────────────────────
  (
    'Senior Director',
    'senior director',
    ARRAY['Senior Technology Director', 'Senior Engineering Director'],
    ARRAY['senior leadership', 'strategic planning', 'portfolio management',
          'executive stakeholder management', 'organisational transformation',
          'revenue growth', 'talent strategy', 'governance']
  ),

  -- ── Project Coordinator ─────────────────────────────────────────────────────
  (
    'Project Coordinator',
    'project coordinator',
    ARRAY['PMO Coordinator', 'Programme Coordinator', 'Associate - Projects Administration'],
    ARRAY['project coordination', 'scheduling', 'meeting minutes', 'action tracking',
          'status reporting', 'resource booking', 'document management', 'ms office',
          'jira', 'confluence', 'risk log', 'issue log']
  ),

  -- ── IT Operations Manager ───────────────────────────────────────────────────
  (
    'Manager - IT Operations',
    'manager - it operations',
    ARRAY['IT Operations Manager', 'Infrastructure Manager', 'Operations Manager'],
    ARRAY['itil', 'incident management', 'service desk', 'infrastructure operations',
          'monitoring', 'sla', 'vendor management', 'change management',
          'patch management', 'capacity planning', 'disaster recovery']
  ),

  -- ── Digital Adoption Consultant ─────────────────────────────────────────────
  (
    'Digital Adoption Consultant',
    'digital adoption consultant',
    ARRAY['DAP Consultant', 'Change Adoption Specialist'],
    ARRAY['digital adoption', 'walkme', 'pendo', 'change management', 'user onboarding',
          'training content', 'user engagement', 'in-app guidance', 'adoption metrics',
          'stakeholder enablement', 'salesforce adoption']
  )

ON CONFLICT (canonical_role) DO UPDATE
  SET profile_type    = EXCLUDED.profile_type,
      aliases         = EXCLUDED.aliases,
      enriched_terms  = EXCLUDED.enriched_terms;

-- Verification
SELECT canonical_role, profile_type, array_length(aliases, 1) AS alias_count,
       array_length(enriched_terms, 1) AS term_count
FROM role_ontology
ORDER BY profile_type, canonical_role;
