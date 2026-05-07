import os
import re

replacements = [
    # Full paths with Optional leading slash
    (r"/?specs/change-request/CR_SCORE_003_spec\.md", "/specs/change-request/CR_SCORE_003/spec.md"),
    (r"/?specs/change-request/CR_SCORE_003_plan\.md", "/specs/change-request/CR_SCORE_003/plan.md"),
    (r"/?specs/change-request/CR_SCORE_003_tasks\.md", "/specs/change-request/CR_SCORE_003/tasks.md"),
    
    (r"/?specs/change-request/CR_PII_scrubber\.md", "/specs/change-request/CR_PII_scrubber/spec.md"),
    (r"/?specs/change-request//CR_PII_scrubber\.md", "/specs/change-request/CR_PII_scrubber/spec.md"),
    (r"/?specs/CR_PII_scrubber\.md", "/specs/change-request/CR_PII_scrubber/spec.md"),
    (r"/?specs/change-request/CR_PII_SCRUBBER_IMPLEMENTATION_PLAN\.md", "/specs/change-request/CR_PII_scrubber/plan.md"),
    (r"/?specs/change-request/CR_PII_scrubber-tasks\.md", "/specs/change-request/CR_PII_scrubber/tasks.md"),
    (r"/?specs/change-request/CR_PII_scrubber_IMPACT_SUMMARY\.md", "/specs/change-request/CR_PII_scrubber/impact_summary.md"),
    (r"/?specs/CR_PII_scrubber_IMPACT_SUMMARY\.md", "/specs/change-request/CR_PII_scrubber/impact_summary.md"),
    
    (r"/?specs/change-request/CR_resume_embedding_pipeline\.md", "/specs/change-request/CR_EMB_002/spec.md"),
    (r"/?specs/change-request/CR_EMB_002_plan\.md", "/specs/change-request/CR_EMB_002/plan.md"),
    (r"/?specs/change-request/CR_EMB_002_tasks\.md", "/specs/change-request/CR_EMB_002/tasks.md"),

    (r"/?specs/hitl-feedback-constitution\.md", "/specs/change-request/CR_HITL_feedback/constitution.md"),
    (r"/?specs/hitl-feedback-plan\.md", "/specs/change-request/CR_HITL_feedback/plan.md"),
    (r"/?specs/functional/fr-7-hitl-feedback-api\.md", "/specs/change-request/CR_HITL_feedback/spec.md"),
    
    # Relative paths
    (r"\./CR_PII_scrubber\.md", "./spec.md"),
    (r"\./CR_PII_scrubber_IMPACT_SUMMARY\.md", "./impact_summary.md"),
    
    # Labels
    (r"\[CR_PII_scrubber\.md\]", "[spec.md]"),
    (r"\[CR_PII_scrubber_IMPACT_SUMMARY\.md\]", "[impact_summary.md]"),
]

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, new_content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk('specs'):
    for file in files:
        if file.endswith('.md'):
            update_file(os.path.join(root, file))
