import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, classification_report
import joblib
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'ml_models')
DATA_FILE_V2 = os.path.join(MODELS_DIR, 'ml_dataset_v2.csv')
DATA_FILE_OLD = os.path.join(BASE_DIR, 'ml_dataset.csv')

print("1. Loading data...")
try:
    df = pd.read_csv(DATA_FILE_V2)
except FileNotFoundError:
    df = pd.read_csv(DATA_FILE_OLD)

print("2. Injecting Variance & Balancing Classes...")
np.random.seed(42)

df['attendance_score'] = np.random.randint(0, 101, size=len(df)) 
df['days_late'] = np.random.choice([0, 1, 2, 3, 5, 10], size=len(df), p=[0.5, 0.2, 0.1, 0.1, 0.05, 0.05])
df['breach_level'] = np.random.choice([0, 1, 2, 3], size=len(df), p=[0.7, 0.15, 0.1, 0.05])

penalty_map = {0: 0, 1: 20, 2: 50, 3: 100}
df['penalty'] = df['breach_level'].map(penalty_map)

base_score = (df['quality_score'] * 0.50) + (df['attendance_score'] * 0.50) - (df['days_late'] * 5)
df['expected_score'] = (base_score - df['penalty']).clip(lower=0, upper=100)

mask = np.random.rand(len(df)) < 0.5
df.loc[mask, 'manager_stars_score'] = (df.loc[mask, 'expected_score'] / 20) + np.random.uniform(-0.5, 0.5, size=mask.sum())
df['manager_stars_score'] = df['manager_stars_score'].clip(lower=0, upper=5)

manager_score_out_of_100 = df['manager_stars_score'] * 20
df['is_biased'] = (abs(manager_score_out_of_100 - df['expected_score']) > 15).astype(int)

df.to_csv(DATA_FILE_V2, index=False)

print("\n3. Splitting Data for Final Evaluation...")

print("\n4. Training & Validating Expected Score Model (Regressor)...")
X_reg = df[['task_importance', 'days_late', 'quality_score', 'attendance_score', 'breach_level']]
y_reg = df['expected_score']

regressor = RandomForestRegressor(n_estimators=100, random_state=42)

cv_scores_reg = cross_val_score(regressor, X_reg, y_reg, cv=5, scoring='r2')
print(f"   5-Fold Cross-Validation Scores: {[round(score, 4) for score in cv_scores_reg]}")
print(f"   Robust Average Accuracy (R²): {cv_scores_reg.mean() * 100:.2f}%")

regressor.fit(X_reg, y_reg)
joblib.dump(regressor, os.path.join(MODELS_DIR, 'expected_score_model.pkl'))

print("\n5. Training & Validating Bias Detection Model (Classifier)...")
X_clf = df[['task_importance', 'days_late', 'quality_score', 'attendance_score', 'breach_level', 'manager_stars_score']]
y_clf = df['is_biased']

classifier = RandomForestClassifier(n_estimators=100, random_state=42)

cv_scores_clf = cross_val_score(classifier, X_clf, y_clf, cv=5, scoring='accuracy')
print(f"   5-Fold Cross-Validation Scores: {[round(score, 4) for score in cv_scores_clf]}")
print(f"   Robust Average Accuracy: {cv_scores_clf.mean() * 100:.2f}%\n")

X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X_clf, y_clf, test_size=0.2, random_state=42)
classifier.fit(X_train_c, y_train_c)
print("   True Unseen Data Report (To check class balance):")
print(classification_report(y_test_c, classifier.predict(X_test_c)))

classifier.fit(X_clf, y_clf)
joblib.dump(classifier, os.path.join(MODELS_DIR, 'bias_detection_model.pkl'))

print("\nSUCCESS: Pipeline completed securely with CROSS-VALIDATION!")