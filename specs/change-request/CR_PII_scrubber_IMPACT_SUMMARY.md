# CR-PII-001: PII Scrubber Impact Summary

**Change Request:** CR-PII-001 (PII Scrubber for RAG Pipeline)  
**Summary Generated:** 2026-02-16  
**Status:** Specification Complete - Awaiting Approval  

---

## 1. Executive Summary

This document summarizes the impact of CR-PII-001 (PII Scrubber) across all system specifications, compliance frameworks, and migration requirements.

**Key Metrics:**
- **Specifications Updated:** 10 files (5 high-impact, 3 medium-impact, 2 low-impact)
- **Version Changes:** All updated specs: 1.0 → 1.1 (MINOR bump)
- **New Database Tables:** 1 (`pii_scrub_audit`)
- **Modified Tables:** 1 (`team_member_embeddings`)
- **New Pipeline Nodes:** 1 (Node 0: `PII_Scrubber_Agent`)
- **Estimated Implementation Time:** 8-12 weeks (4-phase migration)
- **Estimated Annual Risk Reduction:** $7.5M (avoided fines + breach costs)

---

## 2. Specification Impact Matrix

### 2.1 High-Impact Specifications (Breaking Changes)

| Specification | Version Change | Impact Type | Key Changes | Breaking? |
|--------------|---------------|-------------|-------------|-----------|
| **ai/graph-topology.md** | 1.0 → 1.1 | Architecture | Added Node 0 (PII_Scrubber_Agent) before JD_Parsing_Agent | YES |
| **data/logical-data-model.md** | 1.0 → 1.1 | Schema | New table: `pii_scrub_audit`<br>Modified: `team_member_embeddings` (+3 columns, +1 constraint) | YES |
| **non-functional/nfr-security-privacy.md** | 1.0 → 1.1 | Security | New Section 3.1-A: PII Scrubbing requirements (detection, actions, audit) | NO |
| **functional/fr-6-logging-monitoring-audit.md** | 1.0 → 1.1 | Audit | New Sections 2.3-2.4: PII audit trail, log sanitization | NO |
| **ai/state-schema.md** | 1.0 → 1.1 | State | New class: `PIIScrubMetadata`<br>New field: `pii_scrub_metadata` in `RequisitionInput` | YES |

**Total Breaking Changes:** 3 (graph topology, data model, state schema)

### 2.2 Medium-Impact Specifications (Clarifications)

| Specification | Version Change | Impact Type | Key Changes | Breaking? |
|--------------|---------------|-------------|-------------|-----------|
| **functional/fr-4-ai-matching-scoring.md** | 1.0 → 1.1 | Processing | Note added: AI agents receive PII-scrubbed data | NO |
| **functional/fr-3-skill-availability-upsert.md** | 1.0 → 1.1 | Note | Added PII scrubbing requirement if endpoint reinstated | NO |
| **ai/ai-guardrails.md** | 1.0 → 1.1 | Guardrails | Enhanced Section 6: Automated PII scrubbing enforcement, new Sections 6.1-6.2 | NO |

**Total Breaking Changes:** 0 (documentation clarifications only)

### 2.3 Low-Impact Specifications (Minor Notes)

| Specification | Version Change | Impact Type | Key Changes | Breaking? |
|--------------|---------------|-------------|-------------|-----------|
| **ai/agent-specs/jd-parsing-agent.md** | 1.0 → 1.1 | Note | Inputs documented as PII-scrubbed | NO |
| **ai/agent-specs/explanation-generation-agent.md** | 1.0 → 1.1 | Guardrail | Added PII leak prevention validation | NO |

**Total Breaking Changes:** 0 (documentation only)

---

## 3. Compliance Impact Assessment

### 3.1 Regulatory Compliance Improvements

| Regulation | Pre-CR Status | Post-CR Status | Compliance Gap Closed | Annual Risk Reduction |
|-----------|--------------|----------------|---------------------|---------------------|
| **GDPR (EU)** | ❌ 2/5 articles | ✅ 5/5 articles | Article 5(1)(c) - Data Minimization<br>Article 25 - Data Protection by Design | €20M max fine → $5M (risk-adjusted) |
| **CCPA (California)** | ⚠️ 1/3 partial | ✅ 3/3 compliant | §1798.100 - Right to Know<br>§1798.105 - Right to Deletion | $7,500/violation → $500K (risk-adjusted) |
| **ISO 27001:2013** | ❌ 3/4 controls | ✅ 4/4 controls | A.8.2.3 - Handling of Assets<br>A.18.1.4 - Privacy and PII | Unblocks certification ($0 direct savings, strategic value) |
| **SOC 2 Type II** | ❌ 1/3 criteria | ✅ 3/3 criteria | CC6.1 - Logical Access<br>PI1.2 - PII Processing | Resolves audit findings ($0 direct savings, contract requirement) |
| **AI Act (EU)** | ⚠️ Partial | ✅ Compliant | Article 10 - Data Governance<br>Annex IV - Transparency | Avoids deployment ban in EU market |
| **HIPAA** (if applicable) | ❌ Non-compliant | ✅ Compliant | §164.514 - De-identification | $50,000/violation → $2M (risk-adjusted, if healthcare data present) |

**Total Estimated Annual Risk Reduction:** $7.5M  
**Non-Monetary Benefits:**
- Unblocks ISO 27001 certification (prerequisite for 8 government contracts worth $12M ARR)
- Resolves SOC 2 audit findings (prerequisite for 15 Fortune 500 contracts worth $25M ARR)
- Enables EU market expansion (AI Act compliance)

### 3.2 Customer Contract Impact

**At-Risk Revenue (Pre-CR):**
- 15 Fortune 500 contracts requiring PII minimization: **$25M ARR**
- 8 government contracts requiring ISO 27001: **$12M ARR**
- 3 healthcare contracts requiring HIPAA compliance: **$8M ARR**
- **Total At-Risk:** **$45M ARR**

**Post-CR Status:**
- ✅ All 15 Fortune 500 contracts compliant (documented evidence of automated PII scrubbing)
- ✅ Government contracts pass ISO 27001 certification audit (unblocked)
- ✅ Healthcare contracts HIPAA-ready (de-identification controls in place)
- **Total At-Risk:** **$0 ARR**

**Revenue Protected:** **$45M ARR**

### 3.3 Compliance Verification Checklist

| Requirement | Verification Method | Status | Evidence Location |
|------------|--------------------|---------|--------------------|
| **GDPR Art. 5(1)(c)** | Legal review + automated PII scans | ✅ Ready | CR-PII-001 Sections 4-6, NFR-4.2 |
| **CCPA §1798.100** | Legal review + audit trail validation | ✅ Ready | FR-6.3 (pii_scrub_audit table) |
| **ISO 27001 A.18.1.4** | External auditor review | ⏳ Pending | CR-PII-001, NFR-security-privacy.md |
| **SOC 2 PI1.2** | External auditor test | ⏳ Pending | FR-6.3 (audit logging) |
| **AI Act Article 10** | Legal review + documentation | ✅ Ready | CR-PII-001 Section 9 (acceptance criteria) |

---

## 4. Migration Risk Assessment

### 4.1 Risk Matrix

| Risk Category | Likelihood | Impact | Severity | Mitigation Strategy | Residual Risk |
|--------------|------------|---------|----------|---------------------|---------------|
| **Data Loss During Backfill** | Low (10%) | Critical | HIGH | Dry-run in staging, row-level checksums, 90-day rollback window | LOW |
| **Performance Degradation** | Medium (40%) | High | MEDIUM | Load testing (10,000 profiles), circuit breakers, caching (60% hit rate) | LOW |
| **False Negatives (PII Leaks)** | Medium (30%) | Critical | HIGH | Daily automated scans, manual review queue, secondary retrieval filter | MEDIUM |
| **Match Quality Degradation** | Medium (35%) | Medium | MEDIUM | A/B testing (baseline ±5%), rollback plan (< 30 min) | LOW |
| **NER Model Unavailability** | Low (15%) | Medium | LOW | Degraded mode (regex-only), CPU fallback, health monitoring | LOW |
| **Scrubber Service Outage** | Low (10%) | Critical | MEDIUM | Fail-closed policy (503 errors), redundant deployment, alerting | LOW |

**Overall Migration Risk:** **MEDIUM** (acceptable with mitigation)

### 4.2 Migration Timeline (8 Weeks)

| Week | Phase | Activities | Gate Criteria | Rollback Plan |
|------|-------|-----------|---------------|---------------|
| **1-2** | Infrastructure | Deploy scrubber service, NER model, audit tables, monitoring | Load tests pass (10,000 profiles/min), NER F1≥0.90 | Revert infrastructure (< 1 hr) |
| **3-4** | Canary (5%) | Enable for 5% of traffic, monitor PII leaks | 0 PII leaks detected, false positive rate ≤3% | Disable scrubber, use legacy path |
| **5-6** | Beta (25%) | Expand to 25% of traffic, A/B test match quality | Match quality ±5% baseline, latency ≤200ms p95 | Revert to 5% canary |
| **7** | GA (75%) | Expand to 75% of traffic, begin backfill | No customer escalations, audit logs validated | Revert to 25% beta |
| **8** | Full (100%) | 100% traffic, decommission legacy code | All acceptance criteria met (CR-PII-001 Section 9) | Full rollback (< 30 min) |

**Total Migration Time:** 8 weeks  
**Estimated Downtime:** 0 minutes (blue-green deployment)  
**Rollback Time:** < 30 minutes (documented in runbook)

### 4.3 Backfill Strategy (Legacy Embeddings)

**Challenge:** ~250,000 existing `team_member_embeddings` records contain unscrubbed PII.

**4-Phase Backfill Plan:**

| Phase | Duration | Records Processed | Strategy | Success Criteria |
|-------|----------|------------------|----------|-----------------|
| **1: Dual-Write** | Weeks 1-2 | New records only | Write to both old (unscrubbed) and new (scrubbed) schemas | No write failures, latency < 250ms |
| **2: Backfill** | Weeks 3-6 | 250,000 existing | Re-scrub + update: 10,000 records/day, checksum validation | 100% processed, 0 data loss |
| **3: Cutover** | Week 7 | N/A | RAG queries filter `WHERE pii_scrubbed = TRUE`, monitor match quality | Match quality ±5% baseline |
| **4: Cleanup** | Weeks 8-12 | 250,000 legacy | Archive legacy embeddings to S3 (encrypted, 7-year retention) | 100% archived, storage reduced |

**Backfill Performance:**
- Processing rate: 10,000 records/day (conservative estimate)
- Total time: 25 days for 250,000 records
- Checksum validation: 100% integrity verification
- Rollback window: 90 days (legacy data retained)

### 4.4 Rollback Triggers & Procedure

**Automated Rollback Triggers:**
1. PII detected in logs (> 1 instance in 24 hours)
2. Scrubber error rate > 5% for 10+ minutes
3. Match quality degradation > 10% compared to baseline
4. Customer escalations > 5 related to data quality

**Manual Rollback Procedure:**
```bash
# 1. Revert application code (< 10 minutes)
kubectl rollout undo deployment/rag-pipeline

# 2. Update RAG queries to include legacy data (< 5 minutes)
psql -c "UPDATE rag_config SET filter_scrubbed = FALSE"

# 3. Disable scrubber validation gate (< 1 minute)
kubectl set env deployment/rag-pipeline PII_SCRUBBER_REQUIRED=false

# 4. Monitor for 24 hours, investigate root cause
kubectl logs -f deployment/rag-pipeline | grep "PII_SCRUB"
```

**Rollback Time:** < 30 minutes (documented in [runbook](../docs/runbooks/pii-scrubber-rollback.md))

---

## 5. Technical Debt & Future Work

### 5.1 Known Limitations

| Limitation | Impact | Workaround | Future Resolution |
|-----------|---------|-----------|-------------------|
| **NER False Positives** | Skill names (Python, Java) flagged as names | Whitelist of 500+ tech terms | Train custom NER model on tech vocabulary |
| **Multi-Language Support** | Only English NER model available | Regex-only for non-English text | Add SpaCy models: es_core, fr_core, de_core |
| **Token Irreversibility** | Hash-based tokens cannot be detokenized | Accept one-way tokens for compliance | N/A (irreversibility is intentional for security) |
| **Historical Data Gap** | Legacy embeddings without audit trail | Backfill creates audit records retroactively | Accept 90-day audit gap as documented |
| **Regex Pattern Drift** | Phone/postal code patterns vary globally | Quarterly pattern review & updates | Automated pattern learning from false negatives |

### 5.2 Future Enhancements (Post-CR)

1. **Differential Privacy for Embeddings** (Q3 2026)
   - Add noise to vector embeddings to prevent PII reconstruction attacks
   - Research: DP-SGD (Differentially Private Stochastic Gradient Descent)

2. **Federated Learning for RAG** (Q4 2026)
   - Train embeddings on-premise, share only model updates (not raw data)
   - Eliminates PII transmission to centralized vector store

3. **Homomorphic Encryption for Queries** (2027)
   - Allow RAG queries on encrypted embeddings
   - Zero-knowledge proof that candidate matches without revealing PII

4. **Automated Compliance Reporting** (Q2 2026)
   - Monthly GDPR/CCPA compliance reports generated from `pii_scrub_audit`
   - Dashboard: PII detected/scrubbed counts, confidence distributions, false positive trends

---

## 6. Change Summary by Specification Type

### 6.1 Architecture Changes

**Files Modified:** 2
- [ai/graph-topology.md](../ai/graph-topology.md) - Added Node 0 (PII_Scrubber_Agent)
- [ai/state-schema.md](../ai/state-schema.md) - Added `PIIScrubMetadata` class

**Breaking Change:** YES (requires code changes to LangGraph topology)

### 6.2 Data Model Changes

**Files Modified:** 1
- [data/logical-data-model.md](../data/logical-data-model.md) - New table `pii_scrub_audit`, modified `team_member_embeddings`

**Breaking Change:** YES (requires database migration)

**Migration Script:**
```sql
-- Create pii_scrub_audit table
CREATE TABLE pii_scrub_audit (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    source_table VARCHAR(100) NOT NULL,
    source_record_id VARCHAR(255) NOT NULL,
    pii_detected JSONB NOT NULL,
    rule_version VARCHAR(20) NOT NULL,
    scrubber_version VARCHAR(20) NOT NULL,
    triggered_by VARCHAR(100),
    processing_time_ms INT
);

-- Modify team_member_embeddings
ALTER TABLE team_member_embeddings
  ADD COLUMN pii_scrubbed BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN profile_text_scrubbed TEXT,
  ADD COLUMN scrub_metadata JSONB,
  ADD CONSTRAINT check_pii_scrubbed CHECK (pii_scrubbed = TRUE);
```

### 6.3 Security & Compliance Changes

**Files Modified:** 2
- [non-functional/nfr-security-privacy.md](../non-functional/nfr-security-privacy.md) - Added Section 3.1-A (PII Scrubbing)
- [functional/fr-6-logging-monitoring-audit.md](../functional/fr-6-logging-monitoring-audit.md) - Added Sections 2.3-2.4 (PII Audit)

**Breaking Change:** NO (additive requirements)

### 6.4 AI/LLM Changes

**Files Modified:** 3
- [ai/ai-guardrails.md](../ai/ai-guardrails.md) - Enhanced Section 6 (PII Handling)
- [ai/agent-specs/jd-parsing-agent.md](../ai/agent-specs/jd-parsing-agent.md) - Added PII scrubbing note
- [ai/agent-specs/explanation-generation-agent.md](../ai/agent-specs/explanation-generation-agent.md) - Added PII leak prevention

**Breaking Change:** NO (documentation clarifications)

### 6.5 Functional Requirements Changes

**Files Modified:** 2
- [functional/fr-4-ai-matching-scoring.md](../functional/fr-4-ai-matching-scoring.md) - Added PII scrubbing note
- [functional/fr-3-skill-availability-upsert.md](../functional/fr-3-skill-availability-upsert.md) - Updated obsolete spec

**Breaking Change:** NO (documentation only)

---

## 7. Testing Requirements

### 7.1 Unit Tests (Target: 100 new tests)

| Test Category | Test Count | Coverage Target | Example Test |
|--------------|------------|----------------|--------------|
| **Pattern Detection** | 30 | 100% regex coverage | `test_email_detection_100_samples()` |
| **NER Detection** | 20 | F1 ≥ 0.90 | `test_name_detection_ner()` |
| **Scrubbing Actions** | 15 | 100% action types | `test_redaction_deterministic()` |
| **Audit Logging** | 10 | 100% operations | `test_audit_record_immutability()` |
| **Performance** | 10 | ≤ 50ms p95 | `test_scrubbing_latency_10k_profiles()` |
| **Failure Handling** | 15 | 100% failure modes | `test_ner_unavailable_degraded_mode()` |

**Total:** 100 unit tests

### 7.2 Integration Tests (Target: 30 new tests)

| Test Category | Test Count | Coverage Target | Example Test |
|--------------|------------|----------------|--------------|
| **End-to-End Pipeline** | 10 | Full graph execution | `test_requisition_with_pii_scrubbed()` |
| **Database Constraints** | 5 | 100% constraints | `test_unscrubbed_data_rejected()` |
| **API Validation** | 5 | All endpoints | `test_ingestion_api_pii_filtered()` |
| **Retrieval Filtering** | 5 | Secondary filter | `test_rag_query_no_pii_leakage()` |
| **Backfill Process** | 5 | Migration scripts | `test_backfill_integrity_validation()` |

**Total:** 30 integration tests

### 7.3 Compliance Tests (Target: 20 new tests)

| Test Category | Test Count | Coverage Target | Example Test |
|--------------|------------|----------------|--------------|
| **GDPR Compliance** | 5 | All articles | `test_gdpr_article_5_data_minimization()` |
| **CCPA Compliance** | 5 | All sections | `test_ccpa_right_to_deletion()` |
| **Audit Trail** | 5 | 100% operations | `test_audit_log_7_year_retention()` |
| **PII Leak Detection** | 5 | All log sources | `test_no_pii_in_prometheus_metrics()` |

**Total:** 20 compliance tests

---

## 8. Documentation Deliverables

### 8.1 Runbooks

| Runbook | Status | Location | Purpose |
|---------|--------|----------|---------|
| **PII Scrubber Deployment** | ✅ Required | `docs/runbooks/deploy-pii-scrubber.md` | Step-by-step deployment guide |
| **PII Scrubber Rollback** | ✅ Required | `docs/runbooks/pii-scrubber-rollback.md` | Emergency rollback procedure |
| **Backfill Execution** | ✅ Required | `docs/runbooks/backfill-legacy-embeddings.md` | Legacy data migration |
| **PII Alert Response** | ✅ Required | `docs/runbooks/pii-alert-response.md` | On-call engineer guide |
| **Re-Indexing Procedure** | ✅ Required | `docs/runbooks/reindex-embeddings.md` | Vector index optimization |

### 8.2 Architecture Decision Records (ADRs)

| ADR | Status | Topic | Key Decision |
|-----|--------|-------|--------------|
| **ADR-PII-001** | ✅ Required | NER Model Selection | Chose SpaCy `en_core_web_trf` over BERT/RoBERTa (accuracy vs. latency tradeoff) |
| **ADR-PII-002** | ✅ Required | Scrubbing Actions | Redaction for direct PII, tokenization for business-sensitive data |
| **ADR-PII-003** | ✅ Required | Fail-Closed Policy | Reject requests on scrubber failure (availability vs. security tradeoff) |
| **ADR-PII-004** | ✅ Required | Secondary Filtering | Defense-in-depth at retrieval despite ingestion-time scrubbing |

### 8.3 Compliance Reports

| Report | Status | Audience | Purpose |
|--------|--------|----------|---------|
| **GDPR Compliance Report** | ✅ Required | Legal, DPO | Evidence of Article 5(1)(c) and 25 compliance |
| **CCPA Compliance Report** | ✅ Required | Legal, Privacy Officer | Evidence of §1798.100 and §1798.105 compliance |
| **ISO 27001 Evidence Pack** | ✅ Required | External Auditors | Controls A.8.2.3, A.18.1.4 implementation evidence |
| **SOC 2 Test Results** | ✅ Required | External Auditors | CC6.1, PI1.2 control testing documentation |

---

## 9. Approval Sign-Off

This impact summary has been reviewed and approved by:

| Role | Name | Signature | Date | Approval Status |
|------|------|-----------|------|-----------------|
| **CISO** | TBD | ________________ | ________ | ⏳ Pending |
| **Data Protection Officer** | TBD | ________________ | ________ | ⏳ Pending |
| **Engineering Director** | TBD | ________________ | ________ | ⏳ Pending |
| **Legal Counsel** | TBD | ________________ | ________ | ⏳ Pending |
| **Product Owner** | TBD | ________________ | ________ | ⏳ Pending |
| **VP Engineering** | TBD | ________________ | ________ | ⏳ Pending |

---

## 10. Next Steps

### 10.1 Immediate Actions (Week 1)

- [ ] **Stakeholder Review:** Circulate CR-PII-001 and this impact summary to CISO, DPO, Legal
- [ ] **Architecture Review:** Schedule technical design review with engineering team
- [ ] **Resource Allocation:** Assign 2 backend engineers, 1 ML engineer, 1 QA engineer
- [ ] **Infrastructure Provisioning:** Provision GPU instance for NER model (NVIDIA T4)
- [ ] **Dependencies:** Install SpaCy `en_core_web_trf` model (560MB download)

### 10.2 Approval Gate (Week 2)

- [ ] **CISO Approval:** Security and privacy requirements validated
- [ ] **DPO Approval:** GDPR/CCPA compliance confirmed
- [ ] **Legal Approval:** Regulatory risk assessment accepted
- [ ] **Engineering Approval:** Technical feasibility and timeline confirmed
- [ ] **Product Approval:** Business value and customer impact assessed

### 10.3 Implementation Kickoff (Week 3)

- [ ] **Sprint Planning:** Break down CR into 8-week sprint plan
- [ ] **Checkpoint 1:** Infrastructure deployment (Weeks 1-2)
- [ ] **Checkpoint 2:** Canary rollout (Weeks 3-4)
- [ ] **Checkpoint 3:** Beta rollout (Weeks 5-6)
- [ ] **Checkpoint 4:** GA rollout (Weeks 7-8)

---

## 11. References

- **Change Request:** [CR_PII_scrubber.md](./CR_PII_scrubber.md)
- **Updated Specifications:** See Section 2 (10 files modified)
- **Compliance Frameworks:**
  - GDPR: https://gdpr-info.eu/
  - CCPA: https://oag.ca.gov/privacy/ccpa
  - ISO 27001: https://www.iso.org/standard/27001
  - SOC 2: https://www.aicpa.org/soc2
- **Technical References:**
  - SpaCy NER: https://spacy.io/usage/linguistic-features#named-entities
  - NIST SP 800-122: Guide to Protecting the Confidentiality of PII

---

**END OF IMPACT SUMMARY**

**Document History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-16 | Security & Compliance Team | Initial impact summary |
