-- ============================================================================
-- Seed: jd_certification_requirements
-- ============================================================================
-- jd_type values cover two layers:
--   1. profile_type codes (team_member.profile_type) — short normalised keys
--      used for broad category matching: developer, lead, qa, designer, ba …
--   2. Specific designation strings — for roles whose cert track differs from
--      the generic category (e.g. Senior Database Administrator, Network Engineer)
--
-- Certification names use the most widely-recognised canonical form.
-- Certs are calibrated to be realistic for each seniority level — not aspirational.
-- Interns and trainees have no entries; certifications are not expected at that stage.
-- Add rows freely; the UNIQUE constraint (jd_type, certification) blocks dups.
-- ============================================================================

INSERT INTO jd_certification_requirements (jd_type, certification) VALUES

  -- ── developer ──────────────────────────────────────────────────────────────
  -- Covers: Software Engineer, Senior Software Engineer, Senior Frontend
  -- Engineer, Associate Software Engineer, Support Engineer, Systems Engineer,
  -- Billing Support Engineer, Senior Support Engineer
  -- Note: Terraform removed (DevOps/infra cert, not a developer cert)
  ('developer', 'AWS Certified Developer – Associate'),
  ('developer', 'Oracle Certified Professional: Java SE 17'),
  ('developer', 'Spring Professional Certification'),
  ('developer', 'Microsoft Certified: Azure Developer Associate'),
  ('developer', 'MongoDB Associate Developer'),
  ('developer', 'Meta Front-End Developer Certificate'),
  ('developer', 'Google Associate Android Developer'),

  -- ── lead ───────────────────────────────────────────────────────────────────
  -- Covers: Technical Lead, Senior Technical Lead, Engineering Lead, Team Lead,
  -- Module Lead, Project Lead, Lead Support Analyst, Engineering Leader,
  -- Senior Project Lead, Senior Lead - Frontend Engineering
  -- Note: PMP removed (PM cert, not for technical leads); ISTQB Test Manager
  --       removed (QA-specific, not for general tech leads)
  ('lead', 'Certified ScrumMaster (CSM)'),
  ('lead', 'AWS Certified Solutions Architect – Associate'),
  ('lead', 'SAFe Advanced Scrum Master (SASM)'),
  ('lead', 'Microsoft Certified: Azure Developer Associate'),

  -- ── qa ─────────────────────────────────────────────────────────────────────
  -- Covers: QA Engineer, Senior QA Engineer, Associate QA Engineer, Trainee QA
  -- Engineer, QA Manager, Senior QA Manager, Associate QA Manager, QA Lead,
  -- Senior QA Lead, QA Consultant, Senior QA Consultant, Lead QA Engineer,
  -- Module Lead - Quality Assurance
  -- Note: ISTQB Expert Level removed — extremely rare, unrealistic expectation
  ('qa', 'ISTQB Certified Tester – Foundation Level (CTFL)'),
  ('qa', 'ISTQB Certified Tester – Advanced Level Test Analyst'),
  ('qa', 'ISTQB Certified Tester – Advanced Level Test Manager'),
  ('qa', 'Certified Agile Tester (CAT)'),
  ('qa', 'Selenium WebDriver with Java – Test Automation University'),
  ('qa', 'Postman API Fundamentals Student Expert'),
  ('qa', 'TOSCA Automation Specialist Level 1'),

  -- ── designer ───────────────────────────────────────────────────────────────
  -- Covers: UX Designer, Senior UX Designer, Associate UX Designer,
  -- Senior UI Designer, Product Designer, Senior Product Designer,
  -- Instructional Designer, Graphic Designer
  -- Note: SAP Fiori System Administration removed — admin cert, wrong domain
  ('designer', 'Google UX Design Certificate (Coursera)'),
  ('designer', 'Nielsen Norman Group UX Certification'),
  ('designer', 'Interaction Design Foundation – UX Design Certification'),
  ('designer', 'Adobe Certified Professional – Visual Design'),
  ('designer', 'Certified Usability Analyst (CUA) – HFI'),

  -- ── ba ─────────────────────────────────────────────────────────────────────
  -- Covers: Business Analyst, Senior Business Analyst, Associate Business
  -- Analyst, Lead Business Analyst
  -- Note: CBAP requires 7500 hrs (senior BAs); CCBA requires 3750 hrs (mid-level)
  --       Power Platform Fundamentals removed — too tech-specific for general BAs
  ('ba', 'IIBA CCBA – Certification of Capability in Business Analysis'),
  ('ba', 'IIBA CBAP – Certified Business Analysis Professional'),
  ('ba', 'PMI-PBA – Professional in Business Analysis'),
  ('ba', 'Agile Analysis Certification (IIBA-AAC)'),
  ('ba', 'Certified Scrum Product Owner (CSPO)'),

  -- ── consultant ─────────────────────────────────────────────────────────────
  ('consultant', 'Salesforce Certified Administrator'),
  ('consultant', 'SAP Certified Associate – Business Process Integration'),
  ('consultant', 'ServiceNow Certified System Administrator (CSA)'),
  ('consultant', 'ITIL 4 Foundation'),
  ('consultant', 'AWS Certified Cloud Practitioner'),

  -- ── senior consultant ──────────────────────────────────────────────────────
  -- Note: Salesforce Application Architect replaced with Platform App Builder
  --       (Application Architect is too advanced for this level);
  --       SAP Certified Professional replaced with Associate-level (Professional
  --       is very demanding and uncommon at this seniority)
  ('senior consultant', 'Salesforce Certified Platform App Builder'),
  ('senior consultant', 'SAP Certified Associate – SAP S/4HANA Cloud'),
  ('senior consultant', 'ServiceNow Certified Implementation Specialist'),
  ('senior consultant', 'ITIL 4 Managing Professional'),
  ('senior consultant', 'AWS Certified Solutions Architect – Associate'),
  ('senior consultant', 'TOGAF 9 Foundation'),

  -- ── lead consultant ────────────────────────────────────────────────────────
  -- Note: SAP Certified Professional replaced with Associate-level
  ('lead consultant', 'Salesforce Certified Application Architect'),
  ('lead consultant', 'TOGAF 9 Certified'),
  ('lead consultant', 'SAP Certified Associate – SAP S/4HANA Cloud'),
  ('lead consultant', 'PMP – Project Management Professional'),
  ('lead consultant', 'AWS Certified Solutions Architect – Professional'),

  -- ── associate consultant ───────────────────────────────────────────────────
  ('associate consultant', 'Salesforce Certified Administrator'),
  ('associate consultant', 'ITIL 4 Foundation'),
  ('associate consultant', 'AWS Certified Cloud Practitioner'),
  ('associate consultant', 'SAP Certified Associate – Business Process Integration'),

  -- ── technical architect ────────────────────────────────────────────────────
  -- Note: Zachman Enterprise Architect removed — very niche, rarely held
  ('technical architect', 'TOGAF 9 Certified'),
  ('technical architect', 'AWS Certified Solutions Architect – Professional'),
  ('technical architect', 'Google Professional Cloud Architect'),
  ('technical architect', 'Microsoft Certified: Azure Solutions Architect Expert'),

  -- ── senior technical architect ─────────────────────────────────────────────
  ('senior technical architect', 'TOGAF 9 Certified'),
  ('senior technical architect', 'AWS Certified Solutions Architect – Professional'),
  ('senior technical architect', 'Google Professional Cloud Architect'),
  ('senior technical architect', 'Microsoft Certified: Azure Solutions Architect Expert'),
  ('senior technical architect', 'Kubernetes CKA – Certified Kubernetes Administrator'),

  -- ── associate technical architect ─────────────────────────────────────────
  ('associate technical architect', 'TOGAF 9 Foundation'),
  ('associate technical architect', 'AWS Certified Solutions Architect – Associate'),
  ('associate technical architect', 'Microsoft Certified: Azure Developer Associate'),

  -- ── associate architect ────────────────────────────────────────────────────
  -- Note: OTM and Salesforce-specific certs removed — too domain-specific for
  --       a generic associate architect role (kept only in specific designations)
  ('associate architect', 'TOGAF 9 Foundation'),
  ('associate architect', 'AWS Certified Solutions Architect – Associate'),
  ('associate architect', 'Microsoft Certified: Azure Developer Associate'),

  -- ── solution architect ─────────────────────────────────────────────────────
  -- Note: Salesforce Application Architect removed — too domain-specific for
  --       a general solution architect role
  ('solution architect', 'TOGAF 9 Certified'),
  ('solution architect', 'AWS Certified Solutions Architect – Professional'),
  ('solution architect', 'Google Professional Cloud Architect'),
  ('solution architect', 'Microsoft Certified: Azure Solutions Architect Expert'),

  -- ── project manager ────────────────────────────────────────────────────────
  -- Note: CAPM removed — entry-level cert, more appropriate for associate PMs
  ('project manager', 'PMP – Project Management Professional'),
  ('project manager', 'PRINCE2 Practitioner'),
  ('project manager', 'Certified ScrumMaster (CSM)'),
  ('project manager', 'PMI Agile Certified Practitioner (PMI-ACP)'),

  -- ── senior project manager ────────────────────────────────────────────────
  ('senior project manager', 'PMP – Project Management Professional'),
  ('senior project manager', 'PRINCE2 Practitioner'),
  ('senior project manager', 'SAFe Program Consultant (SPC)'),
  ('senior project manager', 'PMI Agile Certified Practitioner (PMI-ACP)'),

  -- ── technical project manager ─────────────────────────────────────────────
  ('technical project manager', 'PMP – Project Management Professional'),
  ('technical project manager', 'PRINCE2 Practitioner'),
  ('technical project manager', 'Certified ScrumMaster (CSM)'),
  ('technical project manager', 'AWS Certified Cloud Practitioner'),
  ('technical project manager', 'ITIL 4 Foundation'),

  -- ── senior technical project manager ─────────────────────────────────────
  ('senior technical project manager', 'PMP – Project Management Professional'),
  ('senior technical project manager', 'SAFe Program Consultant (SPC)'),
  ('senior technical project manager', 'TOGAF 9 Foundation'),
  ('senior technical project manager', 'AWS Certified Solutions Architect – Associate'),

  -- ── associate project manager ─────────────────────────────────────────────
  ('associate project manager', 'CAPM – Certified Associate in Project Management'),
  ('associate project manager', 'Certified ScrumMaster (CSM)'),
  ('associate project manager', 'PRINCE2 Foundation'),

  -- ── associate technical project manager ──────────────────────────────────
  ('associate technical project manager', 'CAPM – Certified Associate in Project Management'),
  ('associate technical project manager', 'Certified ScrumMaster (CSM)'),
  ('associate technical project manager', 'AWS Certified Cloud Practitioner'),

  -- ── product manager ───────────────────────────────────────────────────────
  -- Note: Google Project Management Certificate removed — beginner Coursera cert,
  --       not appropriate for a Product Manager
  ('product manager', 'Certified Scrum Product Owner (CSPO)'),
  ('product manager', 'PMI Agile Certified Practitioner (PMI-ACP)'),
  ('product manager', 'SAFe Product Owner / Product Manager (POPM)'),
  ('product manager', 'AIPMM Certified Product Manager (CPM)'),

  -- ── product owner ─────────────────────────────────────────────────────────
  ('product owner', 'Certified Scrum Product Owner (CSPO)'),
  ('product owner', 'Advanced Certified Scrum Product Owner (A-CSPO)'),
  ('product owner', 'SAFe Product Owner / Product Manager (POPM)'),
  ('product owner', 'PMI Agile Certified Practitioner (PMI-ACP)'),

  -- ── delivery manager ──────────────────────────────────────────────────────
  -- Covers: Delivery Manager, Delivery Manager - UX
  ('delivery manager', 'PMP – Project Management Professional'),
  ('delivery manager', 'PRINCE2 Practitioner'),
  ('delivery manager', 'Certified ScrumMaster (CSM)'),
  ('delivery manager', 'SAFe Program Consultant (SPC)'),
  ('delivery manager', 'ITIL 4 Foundation'),

  -- ── senior delivery manager ───────────────────────────────────────────────
  -- Covers: Senior Delivery Manager, Senior Delivery Manager - UX
  ('senior delivery manager', 'PMP – Project Management Professional'),
  ('senior delivery manager', 'SAFe Program Consultant (SPC)'),
  ('senior delivery manager', 'PRINCE2 Practitioner'),
  ('senior delivery manager', 'ITIL 4 Managing Professional'),

  -- ── senior scrum master ───────────────────────────────────────────────────
  ('senior scrum master', 'Certified ScrumMaster (CSM)'),
  ('senior scrum master', 'Advanced Certified ScrumMaster (A-CSM)'),
  ('senior scrum master', 'SAFe Advanced Scrum Master (SASM)'),
  ('senior scrum master', 'Professional Scrum Master II (PSM II)'),
  ('senior scrum master', 'SAFe Program Consultant (SPC)'),

  -- ── manager ───────────────────────────────────────────────────────────────
  -- Covers: Manager, Associate Manager, Assistant Manager
  ('manager', 'PMP – Project Management Professional'),
  ('manager', 'Certified ScrumMaster (CSM)'),
  ('manager', 'ITIL 4 Foundation'),
  ('manager', 'Six Sigma Green Belt'),

  -- ── senior manager ────────────────────────────────────────────────────────
  ('senior manager', 'PMP – Project Management Professional'),
  ('senior manager', 'SAFe Program Consultant (SPC)'),
  ('senior manager', 'ITIL 4 Managing Professional'),
  ('senior manager', 'Six Sigma Black Belt'),
  ('senior manager', 'TOGAF 9 Foundation'),

  -- ── technical manager ─────────────────────────────────────────────────────
  ('technical manager', 'PMP – Project Management Professional'),
  ('technical manager', 'AWS Certified Solutions Architect – Associate'),
  ('technical manager', 'ITIL 4 Foundation'),
  ('technical manager', 'Certified ScrumMaster (CSM)'),

  -- ── senior technical manager ──────────────────────────────────────────────
  ('senior technical manager', 'PMP – Project Management Professional'),
  ('senior technical manager', 'AWS Certified Solutions Architect – Associate'),
  ('senior technical manager', 'TOGAF 9 Certified'),
  ('senior technical manager', 'SAFe Program Consultant (SPC)'),

  -- ── associate technical manager ───────────────────────────────────────────
  ('associate technical manager', 'Certified ScrumMaster (CSM)'),
  ('associate technical manager', 'CAPM – Certified Associate in Project Management'),
  ('associate technical manager', 'AWS Certified Cloud Practitioner'),

  -- ── director ──────────────────────────────────────────────────────────────
  -- Covers: Director, Director Business Development, Director – Digital
  -- Business Solutions, Director – Sales, Director, Delivery
  -- Note: SAFe SPC removed — practitioner/coach cert, not an exec-level cert
  ('director', 'PMP – Project Management Professional'),
  ('director', 'TOGAF 9 Certified'),
  ('director', 'Six Sigma Black Belt'),

  -- ── senior director ───────────────────────────────────────────────────────
  -- Note: SAFe SPC removed — same reasoning as director
  ('senior director', 'PMP – Project Management Professional'),
  ('senior director', 'TOGAF 9 Certified'),

  -- ── associate director ────────────────────────────────────────────────────
  -- Covers: Associate Director, Associate Director People,
  -- Associate Director Engineering
  ('associate director', 'PMP – Project Management Professional'),
  ('associate director', 'TOGAF 9 Foundation'),
  ('associate director', 'Certified ScrumMaster (CSM)'),

  -- ── senior vice president ─────────────────────────────────────────────────
  -- Covers: Senior Vice President, Senior VP Digital Transformation,
  -- Senior VP Transformation & Technology Excellence
  -- Note: SAFe SPC removed — hands-on practitioner cert, not exec-appropriate
  ('senior vice president', 'PMP – Project Management Professional'),
  ('senior vice president', 'TOGAF 9 Certified'),

  -- ── project coordinator ───────────────────────────────────────────────────
  ('project coordinator', 'CAPM – Certified Associate in Project Management'),
  ('project coordinator', 'Google Project Management Certificate'),
  ('project coordinator', 'Certified ScrumMaster (CSM)'),

  -- ── manager - it operations ───────────────────────────────────────────────
  ('manager - it operations', 'ITIL 4 Foundation'),
  ('manager - it operations', 'ITIL 4 Managing Professional'),
  ('manager - it operations', 'CompTIA Network+'),
  ('manager - it operations', 'AWS Certified SysOps Administrator – Associate'),
  ('manager - it operations', 'Microsoft Certified: Azure Administrator Associate'),

  -- ── support manager ───────────────────────────────────────────────────────
  ('support manager', 'ITIL 4 Foundation'),
  ('support manager', 'HDI Support Center Manager (HDI-SCM)'),
  ('support manager', 'Certified Customer Service Professional (CCSP)'),

  -- ── manager - client success ──────────────────────────────────────────────
  ('manager - client success', 'ITIL 4 Foundation'),
  ('manager - client success', 'Gainsight Certified Customer Success Manager'),
  ('manager - client success', 'Salesforce Certified Administrator'),

  -- ── digital adoption consultant ───────────────────────────────────────────
  ('digital adoption consultant', 'WalkMe Certified Digital Adoption Manager'),
  ('digital adoption consultant', 'Pendo Certified Expert'),
  ('digital adoption consultant', 'Salesforce Certified Administrator'),
  ('digital adoption consultant', 'ITIL 4 Foundation'),

  -- ── Specific designations with distinct cert tracks ───────────────────────

  -- Senior Database Administrator
  ('Senior Database Administrator', 'Oracle Database 19c: Administration Certified Professional'),
  ('Senior Database Administrator', 'AWS Certified Database – Specialty'),
  ('Senior Database Administrator', 'Microsoft Certified: Azure Database Administrator Associate'),
  ('Senior Database Administrator', 'PostgreSQL Associate Certification'),
  ('Senior Database Administrator', 'MongoDB Certified DBA Associate'),

  -- Network Engineer
  ('Network Engineer', 'Cisco CCNA – Cisco Certified Network Associate'),
  ('Network Engineer', 'Cisco CCNP Enterprise'),
  ('Network Engineer', 'CompTIA Network+'),
  ('Network Engineer', 'AWS Advanced Networking – Specialty'),
  ('Network Engineer', 'Juniper Networks Certified Associate (JNCIA)'),

  -- Associate Director – Salesforce Solutioning
  -- Note: Salesforce Technical Architect removed — only ~400 people worldwide
  --       hold this cert; unrealistic expectation for this role
  ('Associate Director - Salesforce Solutioning', 'Salesforce Certified Application Architect'),
  ('Associate Director - Salesforce Solutioning', 'Salesforce Certified System Architect'),
  ('Associate Director - Salesforce Solutioning', 'TOGAF 9 Certified'),

  -- Senior UI Consultant
  -- Note: Salesforce Platform Developer I removed — developer cert, wrong domain
  ('Senior UI Consultant', 'Google UX Design Certificate (Coursera)'),
  ('Senior UI Consultant', 'Nielsen Norman Group UX Certification'),
  ('Senior UI Consultant', 'Interaction Design Foundation – UX Design Certification'),
  ('Senior UI Consultant', 'Adobe Certified Professional – Visual Design'),

  -- Associate Architect – OTM (Oracle Transportation Management)
  ('Associate Architect- OTM', 'Oracle Transportation Management (OTM) Implementation Specialist'),
  ('Associate Architect- OTM', 'TOGAF 9 Foundation'),
  ('Associate Architect- OTM', 'Oracle Cloud Infrastructure Architect Associate')

ON CONFLICT (jd_type, certification) DO NOTHING;

-- ── Verification query ────────────────────────────────────────────────────────
SELECT jd_type, COUNT(*) AS cert_count
FROM jd_certification_requirements
GROUP BY jd_type
ORDER BY jd_type;
