"""
Text assembler unit tests (TASK-EMB-027).

All DB calls are mocked — no real DB required.
Run:  pytest tests/cron/test_text_assembler.py -v
"""

import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock


class _FakeMember:
    designation = "Software Engineer"
    base_location = "Bangalore"
    work_type = None
    experience_in_months = 36


class TestAssembleResumeText(unittest.TestCase):

    def test_assemble_resume_text_includes_designation_location(self):
        from app.cron.embedding.text_assembler import assemble_resume_text

        member = _FakeMember()
        result = assemble_resume_text(member, "Five years of Python experience.")
        self.assertIn("Designation:", result)
        self.assertIn("Software Engineer", result)
        self.assertIn("Location:", result)
        self.assertIn("Bangalore", result)
        self.assertIn("Resume:", result)
        self.assertIn("Five years of Python experience.", result)

    def test_assemble_resume_text_includes_experience(self):
        from app.cron.embedding.text_assembler import assemble_resume_text

        member = _FakeMember()
        result = assemble_resume_text(member, "content")
        self.assertIn("36 months", result)


class TestAssembleSkillsText(unittest.TestCase):

    def _mock_db(self, rows):
        """Build a mock DB that returns `rows` from the chained query."""
        db = MagicMock()
        db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = rows
        return db

    def test_assemble_skills_text_expert_label_for_rating_gte_8(self):
        from app.cron.embedding.text_assembler import assemble_skills_text

        rows = [("Python", "Programming", 9)]
        db = self._mock_db(rows)
        result = assemble_skills_text("member1", db)
        self.assertIn("Expert", result)
        self.assertIn("Python", result)

    def test_assemble_skills_text_intermediate_for_rating_5_to_7(self):
        from app.cron.embedding.text_assembler import assemble_skills_text

        rows = [("Docker", "DevOps", 6)]
        db = self._mock_db(rows)
        result = assemble_skills_text("member1", db)
        self.assertIn("Intermediate", result)

    def test_assemble_skills_text_beginner_for_rating_below_5(self):
        from app.cron.embedding.text_assembler import assemble_skills_text

        rows = [("Kubernetes", "DevOps", 3)]
        db = self._mock_db(rows)
        result = assemble_skills_text("member1", db)
        self.assertIn("Beginner", result)

    def test_assemble_skills_text_empty_skills_returns_empty_string(self):
        from app.cron.embedding.text_assembler import assemble_skills_text

        db = self._mock_db([])
        result = assemble_skills_text("member1", db)
        self.assertEqual(result, "")


class TestAssembleCertificationsText(unittest.TestCase):

    def _mock_db(self, rows):
        db = MagicMock()
        db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = rows
        return db

    def test_assemble_certifications_text_active_status_for_future_date(self):
        from app.cron.embedding.text_assembler import assemble_certifications_text

        future = date.today() + timedelta(days=365)
        rows = [("AWS Solutions Architect", "Amazon", future, "AWS")]
        db = self._mock_db(rows)
        result = assemble_certifications_text("member1", db)
        self.assertIn("Active", result)
        self.assertIn("AWS Solutions Architect", result)

    def test_assemble_certifications_text_expired_status_for_past_date(self):
        from app.cron.embedding.text_assembler import assemble_certifications_text

        past = date.today() - timedelta(days=100)
        rows = [("CKA", "CNCF", past, "Kubernetes")]
        db = self._mock_db(rows)
        result = assemble_certifications_text("member1", db)
        self.assertIn("Expired", result)

    def test_assemble_certifications_text_none_valid_till_is_active(self):
        from app.cron.embedding.text_assembler import assemble_certifications_text

        rows = [("PMP", "PMI", None, "Project Management")]
        db = self._mock_db(rows)
        result = assemble_certifications_text("member1", db)
        self.assertIn("Active", result)

    def test_assemble_certifications_text_no_certs_returns_empty_string(self):
        from app.cron.embedding.text_assembler import assemble_certifications_text

        db = self._mock_db([])
        result = assemble_certifications_text("member1", db)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
