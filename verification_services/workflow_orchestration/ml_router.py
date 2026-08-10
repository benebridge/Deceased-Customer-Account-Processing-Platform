"""
ML-Based Case Router
Implements Chapter 5 intelligent case routing using machine learning

Routes cases to appropriate workflows and predicts processing complexity
"""

import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MLCaseRouter:
    """
    Machine learning-based case router

    Per Chapter 5:
    - Predicts case complexity and processing time
    - Routes cases to appropriate verification workflows
    - Identifies cases requiring manual review
    - Optimizes resource allocation
    - Uses XGBoost/Random Forest for routing decisions
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize ML case router

        Args:
            model_path: Path to pre-trained routing model
        """
        self.model_loaded = False

        # In production, load pre-trained XGBoost model
        # from xgboost import XGBClassifier
        # import joblib
        # self.model = joblib.load(model_path) if model_path else None

        self.model = None  # Placeholder

        # Feature names for routing model
        self.feature_names = [
            'account_balance',
            'account_age_days',
            'beneficiary_age',
            'num_beneficiaries',
            'account_type_encoded',
            'state_encoded',
            'has_blockchain_cert',
            'relationship_score',
            'submission_completeness_score',
            'geographic_distance',
            'days_since_death',
            'submission_hour',
            'submission_day_of_week'
        ]

        # Routing categories
        self.routing_categories = {
            'FAST_TRACK': 'Fast track - automated processing',
            'STANDARD': 'Standard workflow',
            'ENHANCED': 'Enhanced verification required',
            'MANUAL_REVIEW': 'Manual review required',
            'URGENT': 'Urgent processing needed'
        }

    def route_case(self, case_data: Dict) -> Dict:
        """
        Route case to appropriate workflow

        Args:
            case_data: Case information dictionary

        Returns:
            Routing decision with workflow recommendation
        """
        start_time = time.time()

        # Step 1: Engineer features from case data
        features = self._engineer_features(case_data)

        # Step 2: Predict routing category
        if self.model_loaded:
            routing_category = self._ml_routing(features)
        else:
            routing_category = self._rule_based_routing(case_data, features)

        # Step 3: Predict processing time
        estimated_time = self._predict_processing_time(case_data, features)

        # Step 4: Predict complexity score
        complexity_score = self._predict_complexity(case_data, features)

        # Step 5: Determine workflow template
        workflow_template = self._select_workflow_template(
            routing_category,
            case_data.get('account_type'),
            case_data.get('account_balance', 0)
        )

        # Step 6: Identify risk factors
        risk_factors = self._identify_risk_factors(case_data, features)

        # Step 7: Resource allocation recommendation
        resource_allocation = self._recommend_resources(
            routing_category,
            complexity_score,
            estimated_time
        )

        processing_time = (time.time() - start_time) * 1000

        return {
            'routing_category': routing_category,
            'workflow_template': workflow_template,
            'estimated_processing_minutes': estimated_time,
            'complexity_score': complexity_score,
            'risk_factors': risk_factors,
            'resource_allocation': resource_allocation,
            'confidence': self._calculate_routing_confidence(features),
            'features': features,
            'processing_time_ms': processing_time,
            'timestamp': datetime.now().isoformat(),
            'router_version': '1.0.0' if self.model_loaded else 'rule_based'
        }

    def predict_batch_capacity(
        self,
        current_queue: List[Dict],
        available_resources: Dict
    ) -> Dict:
        """
        Predict batch processing capacity

        Helps resource planning and SLA management

        Args:
            current_queue: List of cases in queue
            available_resources: Available processing resources

        Returns:
            Capacity prediction and recommendations
        """
        # Route all cases in queue
        routing_results = []
        for case in current_queue:
            result = self.route_case(case)
            routing_results.append(result)

        # Calculate aggregate statistics
        total_estimated_time = sum(r['estimated_processing_minutes'] for r in routing_results)
        avg_complexity = np.mean([r['complexity_score'] for r in routing_results])

        # Count by routing category
        category_counts = defaultdict(int)
        for result in routing_results:
            category_counts[result['routing_category']] += 1

        # Calculate capacity based on resources
        num_automated_workers = available_resources.get('automated_workers', 5)
        num_manual_reviewers = available_resources.get('manual_reviewers', 3)

        # Estimate throughput
        automated_capacity = category_counts['FAST_TRACK'] + category_counts['STANDARD']
        manual_capacity = category_counts['MANUAL_REVIEW'] + category_counts['ENHANCED']

        # Time estimates
        automated_completion_hours = automated_capacity / (num_automated_workers * 4)  # 4 cases/hour/worker
        manual_completion_hours = manual_capacity / (num_manual_reviewers * 2)  # 2 cases/hour/reviewer

        max_completion_hours = max(automated_completion_hours, manual_completion_hours)

        return {
            'queue_size': len(current_queue),
            'total_estimated_minutes': total_estimated_time,
            'average_complexity': avg_complexity,
            'category_distribution': dict(category_counts),
            'estimated_completion_hours': max_completion_hours,
            'bottleneck': 'manual_review' if manual_completion_hours > automated_completion_hours else 'automated',
            'recommendations': self._generate_capacity_recommendations(
                category_counts,
                automated_completion_hours,
                manual_completion_hours,
                available_resources
            )
        }

    def _engineer_features(self, case_data: Dict) -> Dict[str, float]:
        """Engineer features for routing model"""
        features = {}

        # Account balance (log scale)
        balance = case_data.get('account_balance', 0)
        features['account_balance'] = np.log1p(balance)

        # Account age
        account_open_date = case_data.get('account_open_date')
        if account_open_date:
            try:
                open_date = datetime.fromisoformat(account_open_date)
                features['account_age_days'] = (datetime.now() - open_date).days
            except:
                features['account_age_days'] = 365

        # Beneficiary age
        beneficiary_dob = case_data.get('beneficiary_dob')
        if beneficiary_dob:
            try:
                dob = datetime.fromisoformat(beneficiary_dob)
                features['beneficiary_age'] = (datetime.now() - dob).days / 365.25
            except:
                features['beneficiary_age'] = 45

        # Number of beneficiaries
        features['num_beneficiaries'] = case_data.get('num_beneficiaries', 1)

        # Account type (encoded)
        account_type_encoding = {
            'checking': 1,
            'savings': 2,
            'ira': 3,
            '401k': 4,
            'pension': 5,
            'life_insurance': 6,
            'trust': 7,
            'estate': 8,
            'brokerage': 9
        }
        account_type = case_data.get('account_type', 'checking').lower()
        features['account_type_encoded'] = account_type_encoding.get(account_type, 0)

        # State (encoded - simplified, would use proper encoding in production)
        state_encoding = {
            'CA': 1, 'NY': 2, 'TX': 3, 'FL': 4, 'IL': 5,
            'PA': 6, 'OH': 7, 'MI': 8, 'GA': 9, 'NC': 10
        }
        state = case_data.get('state', 'CA')
        features['state_encoded'] = state_encoding.get(state, 0)

        # Has blockchain certificate
        features['has_blockchain_cert'] = 1.0 if case_data.get('has_blockchain_cert') else 0.0

        # Relationship score
        relationship_scores = {
            'spouse': 1.0, 'child': 0.9, 'parent': 0.8,
            'sibling': 0.7, 'relative': 0.5, 'friend': 0.3, 'other': 0.1
        }
        relationship = case_data.get('beneficiary_relationship', 'other').lower()
        features['relationship_score'] = relationship_scores.get(relationship, 0.1)

        # Submission completeness score
        required_fields = ['death_certificate', 'id_document', 'claim_form', 'beneficiary_info']
        provided_fields = sum(1 for field in required_fields if case_data.get(field))
        features['submission_completeness_score'] = provided_fields / len(required_fields)

        # Geographic distance (beneficiary to deceased)
        features['geographic_distance'] = case_data.get('geographic_distance_km', 100.0)

        # Days since death
        date_of_death = case_data.get('date_of_death')
        if date_of_death:
            try:
                dod = datetime.fromisoformat(date_of_death)
                features['days_since_death'] = (datetime.now() - dod).days
            except:
                features['days_since_death'] = 30

        # Submission timing
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

    def _ml_routing(self, features: Dict[str, float]) -> str:
        """ML-based routing using trained model"""
        # TODO: Implement actual ML prediction
        # Example:
        # feature_vector = np.array([features[name] for name in self.feature_names])
        # prediction = self.model.predict(feature_vector.reshape(1, -1))[0]
        # return self.routing_categories[prediction]

        return 'STANDARD'

    def _rule_based_routing(self, case_data: Dict, features: Dict) -> str:
        """Rule-based routing (fallback when ML model not available)"""

        account_balance = case_data.get('account_balance', 0)
        account_type = case_data.get('account_type', 'checking').lower()
        has_blockchain = case_data.get('has_blockchain_cert', False)
        relationship_score = features.get('relationship_score', 0.5)
        completeness_score = features.get('submission_completeness_score', 1.0)

        # FAST_TRACK: Simple, low-risk cases
        if (
            has_blockchain and
            account_balance < 50000 and
            account_type in ['checking', 'savings'] and
            relationship_score >= 0.7 and
            completeness_score >= 0.9
        ):
            return 'FAST_TRACK'

        # MANUAL_REVIEW: High-risk or complex cases
        if (
            account_balance > 500000 or
            account_type in ['trust', 'estate'] or
            relationship_score < 0.3 or
            completeness_score < 0.5
        ):
            return 'MANUAL_REVIEW'

        # ENHANCED: Medium-high value or some risk factors
        if (
            account_balance > 100000 or
            account_type in ['ira', '401k', 'life_insurance'] or
            relationship_score < 0.5
        ):
            return 'ENHANCED'

        # URGENT: Time-sensitive cases
        days_since_death = features.get('days_since_death', 30)
        if days_since_death > 180:  # Long delay - might be time-sensitive
            return 'URGENT'

        # STANDARD: Default routing
        return 'STANDARD'

    def _predict_processing_time(self, case_data: Dict, features: Dict) -> float:
        """Predict estimated processing time in minutes"""

        # Base time by account type
        account_type_times = {
            'checking': 15,
            'savings': 15,
            'ira': 30,
            '401k': 30,
            'pension': 35,
            'life_insurance': 40,
            'trust': 60,
            'estate': 90,
            'brokerage': 25
        }

        account_type = case_data.get('account_type', 'checking').lower()
        base_time = account_type_times.get(account_type, 20)

        # Adjustments
        account_balance = case_data.get('account_balance', 0)
        has_blockchain = case_data.get('has_blockchain_cert', False)

        # Blockchain verification is faster
        if has_blockchain:
            base_time *= 0.5

        # High-value accounts take longer
        if account_balance > 500000:
            base_time *= 1.5
        elif account_balance > 100000:
            base_time *= 1.2

        # Incomplete submissions take longer
        completeness = features.get('submission_completeness_score', 1.0)
        if completeness < 1.0:
            base_time *= (1 + (1 - completeness) * 0.5)

        return round(base_time, 1)

    def _predict_complexity(self, case_data: Dict, features: Dict) -> float:
        """Predict case complexity score (0-100)"""

        complexity = 30.0  # Base complexity

        # Account type complexity
        type_complexity = {
            'checking': 10, 'savings': 10,
            'ira': 20, '401k': 20, 'pension': 25,
            'life_insurance': 30, 'trust': 50, 'estate': 60, 'brokerage': 25
        }
        account_type = case_data.get('account_type', 'checking').lower()
        complexity += type_complexity.get(account_type, 15)

        # High-value adds complexity
        account_balance = case_data.get('account_balance', 0)
        if account_balance > 500000:
            complexity += 20
        elif account_balance > 100000:
            complexity += 10

        # Multiple beneficiaries add complexity
        num_beneficiaries = case_data.get('num_beneficiaries', 1)
        if num_beneficiaries > 1:
            complexity += min(15, num_beneficiaries * 5)

        # Non-relative beneficiary adds complexity
        relationship_score = features.get('relationship_score', 0.5)
        if relationship_score < 0.5:
            complexity += 15

        # Incomplete submission adds complexity
        completeness = features.get('submission_completeness_score', 1.0)
        if completeness < 1.0:
            complexity += (1 - completeness) * 20

        return min(100, complexity)

    def _select_workflow_template(
        self,
        routing_category: str,
        account_type: str,
        account_balance: float
    ) -> str:
        """Select appropriate workflow template"""

        if routing_category == 'FAST_TRACK':
            return 'fast_track'
        elif routing_category == 'MANUAL_REVIEW':
            return 'manual_review'
        elif routing_category == 'URGENT':
            return 'urgent_processing'
        elif account_balance > 500000:
            return 'high_value'
        elif account_type in ['trust', 'estate']:
            return 'trust_estate'
        elif account_type in ['ira', '401k', 'pension']:
            return 'retirement'
        elif account_type == 'life_insurance':
            return 'life_insurance'
        else:
            return 'standard'

    def _identify_risk_factors(self, case_data: Dict, features: Dict) -> List[str]:
        """Identify risk factors requiring attention"""
        risk_factors = []

        account_balance = case_data.get('account_balance', 0)
        if account_balance > 500000:
            risk_factors.append('high_value_account')

        relationship_score = features.get('relationship_score', 0.5)
        if relationship_score < 0.5:
            risk_factors.append('non_relative_beneficiary')

        completeness = features.get('submission_completeness_score', 1.0)
        if completeness < 0.8:
            risk_factors.append('incomplete_documentation')

        days_since_death = features.get('days_since_death', 30)
        if days_since_death < 7:
            risk_factors.append('rapid_claim_filing')
        elif days_since_death > 365:
            risk_factors.append('delayed_claim_filing')

        num_beneficiaries = case_data.get('num_beneficiaries', 1)
        if num_beneficiaries > 3:
            risk_factors.append('multiple_beneficiaries')

        return risk_factors

    def _recommend_resources(
        self,
        routing_category: str,
        complexity_score: float,
        estimated_time: float
    ) -> Dict:
        """Recommend resource allocation for case"""

        if routing_category == 'FAST_TRACK':
            return {
                'processing_type': 'automated',
                'manual_review_required': False,
                'priority': 'normal',
                'recommended_agent': 'automated_workflow'
            }
        elif routing_category == 'MANUAL_REVIEW':
            return {
                'processing_type': 'manual',
                'manual_review_required': True,
                'priority': 'high',
                'recommended_agent': 'senior_reviewer',
                'estimated_reviewer_hours': estimated_time / 60
            }
        elif routing_category == 'URGENT':
            return {
                'processing_type': 'expedited',
                'manual_review_required': False,
                'priority': 'urgent',
                'recommended_agent': 'expedited_workflow'
            }
        elif complexity_score > 70:
            return {
                'processing_type': 'hybrid',
                'manual_review_required': True,
                'priority': 'high',
                'recommended_agent': 'specialist_reviewer'
            }
        else:
            return {
                'processing_type': 'automated',
                'manual_review_required': False,
                'priority': 'normal',
                'recommended_agent': 'standard_workflow'
            }

    def _calculate_routing_confidence(self, features: Dict) -> float:
        """Calculate confidence in routing decision"""

        # High confidence if all key features are present
        key_features = [
            'account_balance',
            'account_type_encoded',
            'relationship_score',
            'submission_completeness_score'
        ]

        present_count = sum(1 for f in key_features if features.get(f) is not None)
        base_confidence = (present_count / len(key_features)) * 100

        # Reduce confidence if using rule-based routing
        if not self.model_loaded:
            base_confidence *= 0.8

        return round(base_confidence, 2)

    def _generate_capacity_recommendations(
        self,
        category_counts: Dict,
        automated_hours: float,
        manual_hours: float,
        resources: Dict
    ) -> List[str]:
        """Generate recommendations for capacity planning"""

        recommendations = []

        # Check for bottlenecks
        if manual_hours > automated_hours * 1.5:
            recommendations.append(
                f"Manual review bottleneck detected. Consider adding {int((manual_hours - automated_hours) / 8)} more reviewers."
            )

        if automated_hours > manual_hours * 1.5:
            recommendations.append(
                "Automated processing bottleneck. Consider scaling up automated workers."
            )

        # Check for high manual review load
        manual_load = category_counts.get('MANUAL_REVIEW', 0) + category_counts.get('ENHANCED', 0)
        total_cases = sum(category_counts.values())

        if manual_load / total_cases > 0.4:
            recommendations.append(
                f"High manual review rate ({manual_load/total_cases*100:.1f}%). Review routing criteria to increase automation."
            )

        # Check resource utilization
        num_reviewers = resources.get('manual_reviewers', 3)
        if manual_hours / num_reviewers > 8:
            recommendations.append(
                f"Reviewers will work {manual_hours/num_reviewers:.1f} hours each. Consider overtime or additional staff."
            )

        if not recommendations:
            recommendations.append("Current resource allocation appears adequate for queue.")

        return recommendations
