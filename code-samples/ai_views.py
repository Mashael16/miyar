# Excerpt from backend/core/views.py (the AI endpoints only).
# Full source is in a private repository.

import json
import logging

from django.conf import settings
from groq import Groq
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.bias_service import analyze_evaluation

logger = logging.getLogger(__name__)


class GenerateInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        employee_name = data.get("employee_name", "the employee")
        radar_metrics = data.get("metrics", [])
        completion_rate = data.get("completion_rate", "N/A")

        prompt = f"""
        You are an expert HR Manager. Analyze the following performance metrics for {employee_name}:
        - Task Completion Rate: {completion_rate}%
        - Radar Metrics (out of 100): {radar_metrics}
        
        Return EXACTLY a JSON object with these three keys. NO markdown, NO formatting, ONLY raw JSON:
        {{
            "summary": "Short summary...",
            "strengths": ["Strength 1"],
            "areas_for_improvement": ["Area 1"]
        }}
        """

        try:
            client = Groq(api_key=settings.GROQ_API_KEY)

            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.2,
            )

            raw_text = chat_completion.choices[0].message.content.strip()

            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "").strip()

            ai_data = json.loads(raw_text)
            return Response({"insights": ai_data}, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response({"insights": raw_text}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("GROQ ERROR: %s", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckEvaluationBiasView(APIView):
    """
    API endpoint that uses Random Forest models to detect potential
    manager bias, predict expected fair scores, and provide actionable recommendations.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        logger.debug("DATA RECEIVED FROM REACT: %s", data)

        def safe_float(val, default_val):
            try:
                if val is None or str(val).strip() == '' or str(val) == 'NaN':
                    return float(default_val)
                return float(val)
            except (ValueError, TypeError):
                return float(default_val)

        try:
            task_importance = safe_float(data.get('task_importance'), 2.0)
            days_late = safe_float(data.get('days_late'), 0.0)
            quality_score = safe_float(data.get('quality_score'), 100.0)
            attendance_score = safe_float(data.get('attendance_score'), 100.0)
            manager_stars_score = safe_float(data.get('manager_stars_score'), 5.0)
            breach_level = safe_float(data.get('breach_level'), 0.0)

            ai_result = analyze_evaluation(
                task_importance,
                days_late,
                quality_score,
                attendance_score,
                breach_level,
                manager_stars_score
            )

            logger.debug("AI ADVISOR RESULT: %s", ai_result)

            return Response(ai_result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("ML MODEL ERROR: %s", str(e))
            return Response(
                {"error": "An internal error occurred during bias detection."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
