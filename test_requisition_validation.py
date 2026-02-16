"""Test script to validate requisition validation logic."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.ai.agents.requisition_validation import validate_requisition_input


def test_valid_requisition():
    """Test a valid requisition passes validation."""
    print("\n" + "="*60)
    print("TEST 1: Valid Requisition")
    print("="*60)
    
    job_description = {
        "client_name": "Acme Corp",
        "title": "Senior Python Developer",
        "role": "Backend Developer",
        "jd_text": "We are looking for an experienced Python developer with strong FastAPI skills. The ideal candidate will have 3-5 years of experience building scalable REST APIs and working with PostgreSQL databases.",
        "mandatory_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "Kubernetes"],
        "experience": {"min_months": 36, "max_months": 60},
        "location": ["Bangalore", "Remote"],
        "work_mode": ["Hybrid"],
        "priority": "HIGH"
    }
    
    is_valid, reasons = validate_requisition_input(job_description)
    
    print(f"Result: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if not is_valid:
        print(f"Reasons: {reasons}")
    
    assert is_valid, f"Expected valid, got invalid with reasons: {reasons}"
    print("✅ Test passed!")


def test_invalid_empty_jd_text():
    """Test requisition with empty JD text fails."""
    print("\n" + "="*60)
    print("TEST 2: Invalid - Empty JD Text")
    print("="*60)
    
    job_description = {
        "client_name": "Test Corp",
        "title": "Developer",
        "role": "Developer",
        "jd_text": "",  # Empty JD text
        "mandatory_skills": ["Python"],
        "location": ["Mumbai"],
        "work_mode": ["On-site"],
        "priority": "MEDIUM"
    }
    
    is_valid, reasons = validate_requisition_input(job_description)
    
    print(f"Result: {'✅ PASS' if not is_valid else '❌ FAIL'}")
    print(f"Validation Reasons: {reasons}")
    
    assert not is_valid, "Expected invalid, got valid"
    assert any("too short or empty" in r for r in reasons), "Expected JD text error"
    print("✅ Test passed!")


def test_invalid_no_skills_short_jd():
    """Test requisition with no skills and short JD fails."""
    print("\n" + "="*60)
    print("TEST 3: Invalid - No Skills + Short JD")
    print("="*60)
    
    job_description = {
        "client_name": "Test Corp",
        "title": "Developer",
        "role": "Developer",
        "jd_text": "Looking for a developer.",  # Too short
        "mandatory_skills": [],  # No skills
        "location": ["Mumbai"],
        "work_mode": ["On-site"],
        "priority": "MEDIUM"
    }
    
    is_valid, reasons = validate_requisition_input(job_description)
    
    print(f"Result: {'✅ PASS' if not is_valid else '❌ FAIL'}")
    print(f"Validation Reasons: {reasons}")
    
    assert not is_valid, "Expected invalid, got valid"
    assert any("mandatory skills" in r.lower() for r in reasons), "Expected skills/JD error"
    print("✅ Test passed!")


def test_invalid_unrealistic_experience():
    """Test requisition with unrealistic experience fails."""
    print("\n" + "="*60)
    print("TEST 4: Invalid - Unrealistic Experience (50 years)")
    print("="*60)
    
    job_description = {
        "client_name": "Test Corp",
        "title": "Senior Developer",
        "role": "Developer",
        "jd_text": "We are looking for an experienced developer with extensive background in software engineering and architecture.",
        "mandatory_skills": ["Python"],
        "experience": {"min_months": 600, "max_months": 720},  # 50-60 years!
        "location": ["Mumbai"],
        "work_mode": ["On-site"],
        "priority": "MEDIUM"
    }
    
    is_valid, reasons = validate_requisition_input(job_description)
    
    print(f"Result: {'✅ PASS' if not is_valid else '❌ FAIL'}")
    print(f"Validation Reasons: {reasons}")
    
    assert not is_valid, "Expected invalid, got valid"
    assert any("unrealistic" in r.lower() for r in reasons), "Expected experience error"
    print("✅ Test passed!")


def test_invalid_too_many_skills():
    """Test requisition with too many mandatory skills."""
    print("\n" + "="*60)
    print("TEST 5: Invalid - Too Many Mandatory Skills (20)")
    print("="*60)
    
    job_description = {
        "client_name": "Test Corp",
        "title": "Full Stack Developer",
        "role": "Developer",
        "jd_text": "We are looking for a unicorn developer who knows everything in the tech world.",
        "mandatory_skills": [
            "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
            "React", "Angular", "Vue", "Django", "FastAPI", "Spring Boot",
            "PostgreSQL", "MongoDB", "Redis", "Kafka", "Docker", "Kubernetes"
        ],  # 20 skills!
        "location": ["Mumbai"],
        "work_mode": ["On-site"],
        "priority": "MEDIUM"
    }
    
    is_valid, reasons = validate_requisition_input(job_description)
    
    print(f"Result: {'✅ PASS' if not is_valid else '❌ FAIL'}")
    print(f"Validation Reasons: {reasons}")
    
    assert not is_valid, "Expected invalid, got valid"
    assert any("unrealistic number" in r.lower() for r in reasons), "Expected skills count error"
    print("✅ Test passed!")


def test_invalid_missing_location():
    """Test requisition with missing location fails."""
    print("\n" + "="*60)
    print("TEST 6: Invalid - Missing Location")
    print("="*60)
    
    job_description = {
        "client_name": "Test Corp",
        "title": "Developer",
        "role": "Developer",
        "jd_text": "We are looking for a developer with Python skills and experience in building web applications.",
        "mandatory_skills": ["Python"],
        "location": [],  # Empty location
        "work_mode": ["Remote"],
        "priority": "MEDIUM"
    }
    
    is_valid, reasons = validate_requisition_input(job_description)
    
    print(f"Result: {'✅ PASS' if not is_valid else '❌ FAIL'}")
    print(f"Validation Reasons: {reasons}")
    
    assert not is_valid, "Expected invalid, got valid"
    assert any("location" in r.lower() for r in reasons), "Expected location error"
    print("✅ Test passed!")


if __name__ == "__main__":
    print("\n" + "🧪 RUNNING REQUISITION VALIDATION TESTS ".center(60, "="))
    
    try:
        test_valid_requisition()
        test_invalid_empty_jd_text()
        test_invalid_no_skills_short_jd()
        test_invalid_unrealistic_experience()
        test_invalid_too_many_skills()
        test_invalid_missing_location()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except AssertionError as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60)
        sys.exit(1)
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ ERROR: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        sys.exit(1)
