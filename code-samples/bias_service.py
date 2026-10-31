import os
import joblib
import pandas as pd
from django.conf import settings

# Load both models
BIAS_MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'bias_detection_model.pkl')
REGRESSOR_MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'expected_score_model.pkl')

bias_model = joblib.load(BIAS_MODEL_PATH)
regressor_model = joblib.load(REGRESSOR_MODEL_PATH)

def analyze_evaluation(task_importance, days_late, quality_score, attendance_score, breach_level, manager_stars_score):
    
    # 1. Predict the Expected Score (Regressor)
    regressor_input = pd.DataFrame([[
        task_importance, days_late, quality_score, attendance_score, breach_level
    ]], columns=[
        'task_importance', 'days_late', 'quality_score', 'attendance_score', 'breach_level'
    ])
    expected_score = round(regressor_model.predict(regressor_input)[0])

    # Calculate Suggested Range
    min_score = max(0, expected_score - 4)
    max_score = min(100, expected_score + 4)
    suggested_range = f"{min_score}-{max_score}"

    # 2. Get AI Prediction for Bias (Classifier)
    bias_input = pd.DataFrame([[
        task_importance, days_late, quality_score, attendance_score, breach_level, manager_stars_score
    ]], columns=[
        'task_importance', 'days_late', 'quality_score', 'attendance_score', 'breach_level', 'manager_stars_score'
    ])
    model_prediction = bool(bias_model.predict(bias_input)[0])

    # 3. Calculate Score Difference
    normalized_manager_score = manager_stars_score * 20 if manager_stars_score <= 5 else manager_stars_score
    score_difference = abs(expected_score - normalized_manager_score)
    
    # 4. The Smart Business Logic:
    # Flag as biased ONLY IF both conditions are met: the model predicts bias AND the gap is > 15
    if score_difference > 15 or model_prediction:
        is_biased = True
    else:
        is_biased = False

    # 5. Set Recommendation
    if is_biased:
        recommendation = f"Please justify or revise the evaluation. Suggested range: {suggested_range}."
    else:
        recommendation = "Evaluation is fair. Employee shows matching performance."

    return {
        "is_biased": is_biased,
        "expected_score": expected_score,
        "suggested_range": suggested_range,
        "recommendation": recommendation
    }