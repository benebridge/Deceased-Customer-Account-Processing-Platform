"""
Common data models for verification services
Based on Chapter 5 specifications
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


class VerificationStatus(Enum):
    """Verification result status"""
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    PENDING = "pending"


class VerificationMethod(Enum):
    """Verification method used"""
    BLOCKCHAIN = "blockchain"
    TRADITIONAL = "traditional"
    BIOMETRIC = "biometric"
    SSDI_CROSSCHECK = "ssdi_crosscheck"
    COMPUTER_VISION = "computer_vision"
    TEXTRACT = "textract"
    PERSONA = "persona"
    OCR = "ocr"  # Generic OCR (Tesseract, etc.)


@dataclass
class VerificationResult:
    """
    Standard verification result structure
    Used across all verification services
    """
    status: VerificationStatus
    confidence_score: float  # 0-100
    method: VerificationMethod
    processing_time_ms: float
    timestamp: datetime
    details: Dict
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            'status': self.status.value,
            'confidence_score': round(self.confidence_score, 2),
            'method': self.method.value,
            'processing_time_ms': round(self.processing_time_ms, 2),
            'timestamp': self.timestamp.isoformat(),
            'details': self.details,
            'error_message': self.error_message
        }


@dataclass
class DeathCertificateData:
    """Extracted death certificate information"""
    deceased_name: str
    deceased_ssn: Optional[str]
    date_of_birth: Optional[str]
    date_of_death: str
    place_of_death: str
    certificate_number: str
    issuing_state: str
    blockchain_hash: Optional[str] = None


@dataclass
class IDDocumentData:
    """Extracted ID document information"""
    name: str
    date_of_birth: str
    document_number: str
    issue_date: str
    expiration_date: str
    issuing_state: str
    address: Optional[str] = None
    photo_data: Optional[bytes] = None


@dataclass
class FraudIndicator:
    """Individual fraud detection signal"""
    indicator_type: str
    severity: str  # low, medium, high
    description: str
    confidence: float  # 0-100


@dataclass
class DocumentQualityMetrics:
    """Document image quality assessment"""
    resolution_dpi: int
    clarity_score: float  # 0-100
    completeness_score: float  # 0-100
    has_security_features: bool
    detected_tampering: bool
    overall_quality_score: float  # 0-100
