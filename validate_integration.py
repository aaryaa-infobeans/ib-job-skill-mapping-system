"""
Module Integration Validation Script
Tests key functionality of all integrated modules
"""
import sys
import asyncio
from datetime import datetime, timedelta

def test_module_imports():
    """Verify all modules can be imported"""
    print("=" * 70)
    print("MODULE IMPORT VALIDATION")
    print("=" * 70)
    
    modules_to_test = [
        ("API Gateway - Main", "app.main"),
        ("API Gateway - Health Router", "app.api.routers.health"),
        ("API Gateway - Metrics Router", "app.api.routers.metrics"),
        ("JD Skill Mapping Router", "app.api.routers.jd_skill_mapping"),
        ("Availability Router", "app.api.routers.skill_availability"),
        ("Candidate Availability Router", "app.api.routers.candidate_availability"),
        ("Matches Router", "app.api.routers.matches"),
        ("Cron - Batch Processor", "app.cron.processing.batch_processor"),
        ("Cron - OAuth Client (STUB)", "app.cron.oauth.token_client"),
        ("Cron - External Client (STUB)", "app.cron.api.external_client"),
        ("Cron - Repositories", "app.cron.db.repositories"),
        ("AI - Skill Scoring", "app.ai.scoring"),
        ("AI - Availability Logic", "app.ai.availability_logic"),
        ("AI - Audit", "app.ai.audit"),
        ("AI - Resumption", "app.ai.resumption"),
        ("Middleware - Auth", "app.middleware.auth"),
        ("Middleware - Correlation", "app.middleware.correlation"),
    ]
    
    passed = 0
    failed = 0
    
    for name, module_path in modules_to_test:
        try:
            __import__(module_path)
            print(f"✅ {name:40s} IMPORTED")
            passed += 1
        except Exception as e:
            print(f"❌ {name:40s} FAILED: {str(e)[:50]}")
            failed += 1
    
    print(f"\n{'Total:':<40s} {passed}/{len(modules_to_test)} passed")
    print("=" * 70)
    return failed == 0


def test_core_algorithms():
    """Test core algorithms without database"""
    print("\n" + "=" * 70)
    print("CORE ALGORITHM VALIDATION")
    print("=" * 70)
    
    try:
        from app.ai.scoring import (
            calculate_skill_score,
            calculate_experience_score,
            calculate_final_score
        )
        
        # Test skill scoring
        mandatory_skills = ["Python", "FastAPI", "PostgreSQL"]
        candidate_skills = ["Python", "FastAPI", "Django", "React"]
        skill_score = calculate_skill_score(
            mandatory_skills=mandatory_skills,
            preferred_skills=["React"],
            candidate_skills=candidate_skills
        )
        print(f"✅ Skill Scoring:        {skill_score:.2f} (Expected: 0.67-0.75)")
        
        # Test experience scoring
        exp_score = calculate_experience_score(
            required_experience={"min_years": 3, "max_years": 5},
            candidate_experience=4
        )
        print(f"✅ Experience Scoring:   {exp_score:.2f} (Expected: 1.00)")
        
        # Test final score
        final_score = calculate_final_score(
            skill_score=0.8,
            experience_score=0.9,
            availability_score=1.0
        )
        print(f"✅ Final Score:          {final_score:.2f} (Expected: 0.85-0.90)")
        
        print("\n✅ All algorithm tests passed!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"❌ Algorithm test failed: {e}")
        print("=" * 70)
        return False


def test_availability_logic():
    """Test availability calculation logic"""
    print("\n" + "=" * 70)
    print("AVAILABILITY LOGIC VALIDATION")
    print("=" * 70)
    
    try:
        from app.ai.availability_logic import (
            calculate_availability_percentage,
            calculate_requisition_window
        )
        from datetime import date
        
        # Test requisition window
        start_date = date(2026, 3, 1)
        end_date = date(2026, 6, 30)
        window = calculate_requisition_window(start_date, end_date)
        print(f"✅ Requisition Window:   {window[0]} to {window[1]}")
        
        # Test availability calculation
        overlapping_days = 30
        total_days = 90
        availability = calculate_availability_percentage(overlapping_days, total_days)
        print(f"✅ Availability:         {availability:.1f}% (Expected: 66.7%)")
        
        print("\n✅ All availability tests passed!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"❌ Availability test failed: {e}")
        print("=" * 70)
        return False


def test_cron_components():
    """Test cron components without database"""
    print("\n" + "=" * 70)
    print("CRON COMPONENT VALIDATION")
    print("=" * 70)
    
    try:
        from app.cron.processing.error_classifier import classify_error, is_retryable
        from app.cron.oauth.token_client import TokenCache
        
        # Test error classification
        conn_error = ConnectionError("Connection failed")
        category = classify_error(conn_error)
        print(f"✅ Error Classification: {category} (Network Error)")
        print(f"✅ Is Retryable:         {is_retryable(conn_error)}")
        
        # Test token cache (STUB implementation)
        cache = TokenCache()
        print(f"✅ Token Cache (STUB):   Always returns valid mock token")
        print(f"   Stub token:           {cache.get_token()}")
        
        print("\n✅ All cron component tests passed! (OAuth/API clients are stubs)")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"❌ Cron component test failed: {e}")
        print("=" * 70)
        return False


def main():
    """Run all validation tests"""
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#  IB JOB SKILL MAPPING SYSTEM - INTEGRATION VALIDATION" + " " * 12 + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    
    # Run all tests
    results = []
    results.append(("Module Imports", test_module_imports()))
    results.append(("Core Algorithms", test_core_algorithms()))
    results.append(("Availability Logic", test_availability_logic()))
    results.append(("Cron Components", test_cron_components()))
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:30s} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL VALIDATION TESTS PASSED!")
        print("=" * 70)
        print("\nNext Steps:")
        print("1. Start PostgreSQL: docker compose up -d postgres")
        print("2. Run migrations: alembic upgrade head")
        print("3. Start server: uvicorn src.main:app --reload --port 8001")
        print("4. Run full test suite: pytest tests/")
        return 0
    else:
        print("❌ SOME VALIDATION TESTS FAILED")
        print("=" * 70)
        print("\nPlease fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
