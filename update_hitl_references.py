import os
import re

# Mapping for specific filenames to their new names within the same CR folder
filename_replacements = [
    (r"hitl-feedback-plan\.md", "plan.md"),
    (r"hitl-feedback-constitution\.md", "constitution.md"),
    (r"fr-7-hitl-feedback-api\.md", "spec.md"),
]

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    # Only apply these to files within the same CR folder or prompts
    for pattern, replacement in filename_replacements:
        new_content = re.sub(pattern, replacement, new_content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

# Target only the HITL folder for these specific filename changes
hitl_folder = 'specs/change-request/CR_HITL_feedback'
for root, dirs, files in os.walk(hitl_folder):
    for file in files:
        if file.endswith('.md'):
            update_file(os.path.join(root, file))
