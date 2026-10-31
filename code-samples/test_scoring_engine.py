# Excerpt from backend/core/tests.py: unit tests for the scoring engine.
# Full test suite (71 tests) is in a private repository.

"""
=============================================================
  Miyar Platform — Comprehensive Test Suite
=============================================================
  Coverage:
    1. Unit Tests         — Models, Scoring Engine, Services
    2. Integration Tests  — API Endpoints (Frontend ↔ Backend ↔ DB)
    3. Security Tests     — Auth, Authorization, Data Isolation
    4. Non-Functional     — Performance (response time)
=============================================================
  Run:
    docker exec -it django_server python manage.py test core --verbosity=2
=============================================================
"""

import time as time_module
from datetime import datetime, timedelta, time
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Task, Evaluation, Attendance, Breach
from .services.scoring import ruleBase
from .services.dashboard_service import get_dashboard_summary
from .services.performance_summary_service import (
    get_monthly_performance,
    get_annual_performance,
    get_performance_trend,
)


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════

def make_user(username, role="employee", gender="male"):
    return User.objects.create_user(
        username=username,
        password="TestPass123!",
        role=role,
        gender=gender,
        email=f"{username}@miyar.test",
    )


def make_task(assigned_to, title="Test Task", importance=2,
              days_until_deadline=7, status="pending"):
    return Task.objects.create(
        title=title,
        assigned_to=assigned_to,
        importance_degree=importance,
        deadline=timezone.now() + timedelta(days=days_until_deadline),
        status=status,
    )


def auth_header(user):
    """Return JWT Authorization header for a given user."""
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"}


# ═══════════════════════════════════════════════════════════
#  1. UNIT TESTS
# ═══════════════════════════════════════════════════════════


class ScoringEngineTest(TestCase):
    """Unit — ruleBase scoring engine."""

    def _make_data(self, days_late=0, completion=1.0, importance=2,
                   breach=None, arrival=None):
        deadline = timezone.now()
        submission = deadline + timedelta(days=days_late)
        return {
            "submissionTime": submission,
            "deadline": deadline,
            "taskNum": 1,
            "taskComplateAVR": completion,
            "startWork": time(8, 0),
            "endWork": time(16, 0),
            "arrivalTime": arrival or time(8, 0),
            "startMeeting": time(10, 0),
            "endMeeting": time(11, 0),
            "arrivalMeeting": time(9, 55),
            "breachLevel": breach,
            "importanceDegree": importance,
        }

    def test_on_time_submission_scores_100(self):
        data = self._make_data(days_late=0)
        rule = ruleBase(data)
        self.assertEqual(rule.submissionTimeRule(), 100)

    def test_one_day_late_scores_90(self):
        data = self._make_data(days_late=1)
        rule = ruleBase(data)
        self.assertEqual(rule.submissionTimeRule(), 90)

    def test_five_days_late_scores_0(self):
        data = self._make_data(days_late=5)
        rule = ruleBase(data)
        self.assertEqual(rule.submissionTimeRule(), 0)

    def test_full_completion_scores_100(self):
        data = self._make_data(completion=1.0)
        rule = ruleBase(data)
        self.assertEqual(rule.taskComplate(), 100)

    def test_half_completion_scores_50(self):
        data = self._make_data(completion=0.5)
        rule = ruleBase(data)
        self.assertEqual(rule.taskComplate(), 50)

    def test_no_breach_scores_100(self):
        data = self._make_data(breach=None)
        rule = ruleBase(data)
        self.assertEqual(rule.Breaches(), 100)

    def test_high_breach_scores_0(self):
        data = self._make_data(breach=1)
        rule = ruleBase(data)
        self.assertEqual(rule.Breaches(), 0)

    def test_moderate_breach_scores_50(self):
        data = self._make_data(breach=2)
        rule = ruleBase(data)
        self.assertEqual(rule.Breaches(), 50)

    def test_result_score_within_0_to_5(self):
        data = self._make_data()
        rule = ruleBase(data)
        score = rule.resultScore()
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 5)

    def test_high_importance_penalizes_late_task(self):
        low_imp = ruleBase(self._make_data(days_late=2, importance=3)).importance()
        high_imp = ruleBase(self._make_data(days_late=2, importance=1)).importance()
        self.assertGreater(low_imp, high_imp)

    def test_manual_attendance_overrides_arrival_time(self):
        data = self._make_data()
        data["attendance_manual_score"] = 80
        rule = ruleBase(data)
        self.assertEqual(rule.workTime(), 80)
