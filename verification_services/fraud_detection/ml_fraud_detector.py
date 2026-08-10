"""
Machine Learning Fraud Detection
Implements Chapter 5 ML-based fraud detection using anomaly detection

Uses unsupervised learning to detect unusual patterns not captured by rules
"""

import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import FraudIndicator


class MLFraudDetector:
    """
    Machine learning-based fraud detector

    Per Chapter 5:
    - Anomaly detection using Isolation Forest
    - Feature engineering from case data
    - Ensemble models for robust detection
    - Continuous learning from new data
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize ML fraud detector

        Args:
            model_path: Path to pre-trained model (if available)
        """
        self.model_loaded = False
        self.feature_names = [
            'account_balance',
            'account_age_days',
            'beneficiary_age',
            'deceased_age_at_death',
            'days_since_death',
            'num_beneficiaries',
            'relationship_score',
            'account_activity_score',
            'document_quality_score',
            'verification_confidence',
            'geographic_distance',
            'submission_hour',
            'submission_day_of_week'
        ]

        # In production, load pre-trained scikit-learn model
        # from joblib import load
        # self.model = load(model_path) if model_path else None

        self.model = None  # Placeholder

        # Thresholds for anomaly scores
        self.high_risk_threshold = 0.8
        self.medium_risk_threshold = 0.6

    def detect_fraud_ml(self, case_data: Dict) -> Dict:
        """
        Run ML-based fraud detection

        Args:
            case_data: Case information dictionary

        Returns:
            Dictionary with ML fraud assessment
        """
        start_time = time.time()

        # Step 1: Feature engineering
        features = self._engineer_features(case_data)

        # Step 2: Run anomaly detection
        anomaly_score, anomaly_details = self._detect_anomalies(features)

        # Step 3: Run ensemble models (if available)
        ensemble_score = self._ensemble_prediction(features) if self.model_loaded else None

        # Step 4: Combine scores
        final_score = self._combine_scores(anomaly_score, ensemble_score)

        # Step 5: Generate explanations
        explanations = self._generate_explanations(features, anomaly_details)

        # Step 6: Determine risk level
        if final_score >= self.high_risk_threshold:
            risk_level = 'high'
            recommendation = 'MANUAL_REVIEW_REQUIRED'
        elif final_score >= self.medium_risk_threshold:
            risk_level = 'medium'
            recommendation = 'ENHANCED_VERIFICATION'
        else:
            risk_level = 'low'
            recommendation = 'PROCEED'

        processing_time = (time.time() - start_time) * 1000

        return {
            'ml_fraud_detected': final_score >= self.medium_risk_threshold,
            'anomaly_score': round(final_score * 100, 2),
            'risk_level': risk_level,
            'recommendation': recommendation,
            'feature_importance': self._get_feature_importance(features, anomaly_details),
            'explanations': explanations,
            'processing_time_ms': processing_time,
            'timestamp': datetime.now().isoformat(),
            'model_version': '1.0.0' if self.model_loaded else 'rule_based_fallback'
        }

    def _engineer_features(self, case_data: Dict) -> Dict[str, float]:
        """
        Engineer features from raw case data

        Features:
        - Numerical: amounts, dates, counts
        - Derived: ratios, differences, scores
        - Categorical: encoded as numeric
        """
        features = {}

        # Account balance (normalize to log scale)
        balance = case_data.get('account_balance', 0)
        features['account_balance'] = np.log1p(balance)  # log(1 + x) to handle 0

        # Account age (days since account opened)
        account_open_date = case_data.get('account_open_date')
        if account_open_date:
            try:
                open_date = datetime.fromisoformat(account_open_date)
                features['account_age_days'] = (datetime.now() - open_date).days
            except:
                features['account_age_days'] = 365  # Default 1 year

        # Beneficiary age
        beneficiary_dob = case_data.get('beneficiary_dob')
        if beneficiary_dob:
            try:
                dob = datetime.fromisoformat(beneficiary_dob)
                features['beneficiary_age'] = (datetime.now() - dob).days / 365.25
            except:
                features['beneficiary_age'] = 45  # Default middle age

        # Deceased age at death
        deceased_dob = case_data.get('deceased_dob')
        date_of_death = case_data.get('date_of_death')
        if deceased_dob and date_of_death:
            try:
                dob = datetime.fromisoformat(deceased_dob)
                dod = datetime.fromisoformat(date_of_death)
                features['deceased_age_at_death'] = (dod - dob).days / 365.25
            except:
                features['deceased_age_at_death'] = 75  # Default elderly

        # Days since death
        if date_of_death:
            try:
                dod = datetime.fromisoformat(date_of_death)
                features['days_since_death'] = (datetime.now() - dod).days
            except:
                features['days_since_death'] = 30

        # Number of beneficiaries
        features['num_beneficiaries'] = case_data.get('num_beneficiaries', 1)

        # Relationship score (encode relationship type)
        relationship_scores = {
            'spouse': 1.0,
            'child': 0.9,
            'parent': 0.8,
            'sibling': 0.7,
            'relative': 0.5,
            'friend': 0.3,
            'other': 0.1
        }
        relationship = case_data.get('beneficiary_relationship', 'other').lower()
        features['relationship_score'] = relationship_scores.get(relationship, 0.1)

        # Account activity score (recent transactions)
        features['account_activity_score'] = case_data.get('account_activity_score', 0.5)

        # Document quality score (from verification)
        features['document_quality_score'] = case_data.get('document_quality_score', 75.0) / 100.0

        # Verification confidence (from other verifications)
        features['verification_confidence'] = case_data.get('verification_confidence', 85.0) / 100.0

        # Geographic distance (beneficiary to deceased)
        features['geographic_distance'] = case_data.get('geographic_distance_km', 100.0)

        # Submission timing features
        submission_date = case_data.get('submission_date')
        if submission_date:
            try:
                sub = datetime.fromisoformat(submission_date)
                features['submission_hour'] = sub.hour
                features['submission_day_of_week'] = sub.weekday()
            except:
                features['submission_hour'] = 12
                features['submission_day_of_week'] = 3

        return features

    def _detect_anomalies(self, features: Dict[str, float]) -> Tuple[float, Dict]:
        """
        Detect anomalies using statistical methods

        In production:
        - Use Isolation Forest (sklearn.ensemble.IsolationForest)
        - One-Class SVM
        - Autoencoder reconstruction error

        For now, uses statistical z-score based detection
        """
        anomaly_details = {}
        anomaly_scores = []

        # Define expected ranges for features (learned from historical data)
        expected_ranges = {
            'account_balance': (10.0, 14.0),  # log scale: $22k - $1.2M
            'account_age_days': (365, 7300),  # 1-20 years
            'beneficiary_age': (18, 80),
            'deceased_age_at_death': (50, 95),
            'days_since_death': (7, 180),
            'num_beneficiaries': (1, 3),
            'relationship_score': (0.3, 1.0),
            'document_quality_score': (0.7, 1.0),
            'verification_confidence': (0.75, 1.0)
        }

        # Check each feature for anomalies
        for feature_name, value in features.items():
            if feature_name in expected_ranges:
                min_val, max_val = expected_ranges[feature_name]

                # Compute how far outside normal range
                if value < min_val:
                    deviation = (min_val - value) / (max_val - min_val)
                    anomaly_scores.append(min(1.0, deviation))
                    anomaly_details[feature_name] = {
                        'value': value,
                        'expected_min': min_val,
                        'status': 'below_expected'
                    }
                elif value > max_val:
                    deviation = (value - max_val) / (max_val - min_val)
                    anomaly_scores.append(min(1.0, deviation))
                    anomaly_details[feature_name] = {
                        'value': value,
                        'expected_max': max_val,
                        'status': 'above_expected'
                    }

        # Overall anomaly score (average of anomalies found)
        overall_score = np.mean(anomaly_scores) if anomaly_scores else 0.0

        return overall_score, anomaly_details

    def _ensemble_prediction(self, features: Dict[str, float]) -> Optional[float]:
        """
        Run ensemble of models for robust prediction

        In production:
        - Gradient Boosting (XGBoost, LightGBM)
        - Random Forest
        - Neural Network
        - Vote/average predictions

        Returns fraud probability 0-1
        """
        if not self.model_loaded:
            return None

        # TODO: Implement ensemble prediction
        # Example:
        # feature_vector = np.array([features[name] for name in self.feature_names])
        # predictions = []
        # predictions.append(self.xgboost_model.predict_proba(feature_vector)[0][1])
        # predictions.append(self.random_forest.predict_proba(feature_vector)[0][1])
        # predictions.append(self.neural_net.predict(feature_vector)[0])
        # return np.mean(predictions)

        return None

    def _combine_scores(
        self,
        anomaly_score: float,
        ensemble_score: Optional[float]
    ) -> float:
        """
        Combine anomaly and ensemble scores

        Weighting:
        - If ensemble available: 60% ensemble, 40% anomaly
        - If only anomaly: 100% anomaly
        """
        if ensemble_score is not None:
            combined = 0.6 * ensemble_score + 0.4 * anomaly_score
        else:
            combined = anomaly_score

        return combined

    def _generate_explanations(
        self,
        features: Dict[str, float],
        anomaly_details: Dict
    ) -> List[str]:
        """
        Generate human-readable explanations for ML decisions

        Uses SHAP values or feature importance in production
        """
        explanations = []

        for feature_name, details in anomaly_details.items():
            if details['status'] == 'below_expected':
                explanations.append(
                    f"{feature_name}: {details['value']:.2f} is below expected minimum {details['expected_min']:.2f}"
                )
            elif details['status'] == 'above_expected':
                explanations.append(
                    f"{feature_name}: {details['value']:.2f} exceeds expected maximum {details['expected_max']:.2f}"
                )

        if not explanations:
            explanations.append("No significant anomalies detected")

        return explanations

    def _get_feature_importance(
        self,
        features: Dict[str, float],
        anomaly_details: Dict
    ) -> List[Dict]:
        """
        Get feature importance scores

        In production, use SHAP values or model-specific importance
        """
        importance = []

        for feature_name in anomaly_details:
            importance.append({
                'feature': feature_name,
                'value': features.get(feature_name, 0),
                'importance': 0.8  # Would be actual SHAP value
            })

        # Sort by importance
        importance.sort(key=lambda x: x['importance'], reverse=True)

        return importance[:5]  # Top 5 features

    def train_model(self, training_data: List[Dict], labels: List[int]):
        """
        Train fraud detection models

        Args:
            training_data: List of historical cases
            labels: Binary labels (0=legitimate, 1=fraud)
        """
        # TODO: Implement model training
        # Example:
        # from sklearn.ensemble import RandomForestClassifier, IsolationForest
        # import xgboost as xgb
        #
        # # Engineer features for all training samples
        # X = np.array([self._engineer_features(case) for case in training_data])
        # y = np.array(labels)
        #
        # # Train ensemble
        # self.random_forest = RandomForestClassifier(n_estimators=100)
        # self.random_forest.fit(X, y)
        #
        # self.xgboost = xgb.XGBClassifier()
        # self.xgboost.fit(X, y)
        #
        # # Train anomaly detector on legitimate cases only
        # X_legit = X[y == 0]
        # self.isolation_forest = IsolationForest()
        # self.isolation_forest.fit(X_legit)
        #
        # self.model_loaded = True

        pass

    def update_model(self, new_data: List[Dict], new_labels: List[int]):
        """
        Incremental learning - update models with new cases

        For continuous improvement
        """
        # TODO: Implement incremental learning
        # Online learning or periodic retraining
        pass
