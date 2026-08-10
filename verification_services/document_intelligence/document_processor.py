"""
Advanced Document Processor
Implements Chapter 5 intelligent document processing

Handles multi-page documents, image enhancement, classification, and extraction
"""

import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from io import BytesIO

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import DocumentQualityMetrics


class DocumentType:
    """Document type classifications"""
    DEATH_CERTIFICATE = "death_certificate"
    DRIVERS_LICENSE = "drivers_license"
    STATE_ID = "state_id"
    PASSPORT = "passport"
    CLAIM_FORM = "claim_form"
    BANK_STATEMENT = "bank_statement"
    TRUST_DOCUMENT = "trust_document"
    WILL = "will"
    COURT_ORDER = "court_order"
    POWER_OF_ATTORNEY = "power_of_attorney"
    UNKNOWN = "unknown"


class DocumentProcessor:
    """
    Advanced document processing service

    Per Chapter 5:
    - Multi-page document handling
    - Image quality enhancement
    - Document classification
    - Intelligent data extraction
    - Format conversion
    - Metadata extraction
    """

    def __init__(self):
        """Initialize document processor"""
        self.supported_formats = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif']

        # In production, load deep learning models:
        # - Document classifier (CNN)
        # - Layout analyzer (LayoutLM)
        # - Text detector (CRAFT, EAST)
        # - OCR engine (Tesseract, EasyOCR)

    def process_document(self, document_path: str) -> Dict:
        """
        Process document with full pipeline

        Args:
            document_path: Path to document file

        Returns:
            Complete processing results
        """
        start_time = time.time()

        try:
            # Step 1: Load and validate document
            doc_info = self._load_document(document_path)

            if not doc_info['valid']:
                return {
                    'success': False,
                    'error': doc_info['error'],
                    'processing_time_ms': (time.time() - start_time) * 1000
                }

            # Step 2: Classify document type
            doc_type = self._classify_document(doc_info)

            # Step 3: Quality assessment
            quality_metrics = self._assess_quality(doc_info)

            # Step 4: Image enhancement (if quality is poor)
            if quality_metrics.overall_score < 75:
                enhanced_images = self._enhance_images(doc_info['images'])
                doc_info['images'] = enhanced_images
                doc_info['enhanced'] = True

            # Step 5: Extract metadata
            metadata = self._extract_metadata(doc_info, document_path)

            # Step 6: Page segmentation and layout analysis
            layout_analysis = self._analyze_layout(doc_info)

            # Step 7: Text extraction with OCR
            extracted_text = self._extract_text(doc_info, layout_analysis)

            # Step 8: Document-specific field extraction
            structured_data = self._extract_structured_data(
                doc_type,
                extracted_text,
                layout_analysis
            )

            # Step 9: Security feature detection
            security_features = self._detect_security_features(doc_info, doc_type)

            processing_time = (time.time() - start_time) * 1000

            return {
                'success': True,
                'document_type': doc_type,
                'num_pages': doc_info['num_pages'],
                'quality_metrics': quality_metrics.to_dict(),
                'enhanced': doc_info.get('enhanced', False),
                'metadata': metadata,
                'layout_analysis': layout_analysis,
                'extracted_text': extracted_text,
                'structured_data': structured_data,
                'security_features': security_features,
                'processing_time_ms': processing_time,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_time_ms': (time.time() - start_time) * 1000
            }

    def _load_document(self, document_path: str) -> Dict:
        """Load and validate document"""
        try:
            file_ext = os.path.splitext(document_path)[1].lower()

            if file_ext not in self.supported_formats:
                return {
                    'valid': False,
                    'error': f'Unsupported format: {file_ext}'
                }

            # Load based on format
            if file_ext == '.pdf':
                return self._load_pdf(document_path)
            else:
                return self._load_image(document_path)

        except Exception as e:
            return {
                'valid': False,
                'error': f'Failed to load document: {str(e)}'
            }

    def _load_pdf(self, pdf_path: str) -> Dict:
        """Load PDF document"""
        # In production, use pdf2image
        # from pdf2image import convert_from_path
        # images = convert_from_path(pdf_path, dpi=300)

        # Simulate loading
        return {
            'valid': True,
            'num_pages': 1,  # Simulated
            'images': [],  # Would contain PIL Image objects
            'format': 'pdf',
            'file_size': os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
        }

    def _load_image(self, image_path: str) -> Dict:
        """Load image document"""
        try:
            image = Image.open(image_path)

            return {
                'valid': True,
                'num_pages': 1,
                'images': [image],
                'format': image.format,
                'file_size': os.path.getsize(image_path)
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f'Failed to load image: {str(e)}'
            }

    def _classify_document(self, doc_info: Dict) -> str:
        """
        Classify document type using ML

        In production:
        - Use CNN-based document classifier
        - Train on labeled dataset of document types
        - Return confidence scores for each type

        Returns:
            Document type classification
        """
        # TODO: Implement ML-based classification
        # Example approach:
        # 1. Resize first page to standard size
        # 2. Pass through CNN classifier
        # 3. Return highest confidence class

        # For now, use simple heuristics based on filename
        # In real implementation, would analyze image content

        return DocumentType.UNKNOWN

    def _assess_quality(self, doc_info: Dict) -> DocumentQualityMetrics:
        """Assess document image quality"""

        if not doc_info['images']:
            # For PDFs or when images not loaded
            return DocumentQualityMetrics(
                resolution_dpi=300,  # Assumed
                clarity_score=80,
                brightness_score=75,
                contrast_score=75,
                completeness_score=100,
                overall_score=80
            )

        # Analyze first page (most important)
        image = doc_info['images'][0]
        width, height = image.size

        # Resolution estimation
        # Assume 8.5x11 inch page
        dpi_width = width / 8.5
        dpi_height = height / 11
        estimated_dpi = (dpi_width + dpi_height) / 2

        # Convert to grayscale for analysis
        gray_image = image.convert('L')
        img_array = np.array(gray_image)

        # Clarity (sharpness) - using Laplacian variance
        laplacian_var = self._compute_laplacian_variance(img_array)
        clarity_score = min(100, (laplacian_var / 100) * 100)

        # Brightness
        mean_brightness = np.mean(img_array)
        # Ideal brightness around 128 (mid-gray)
        brightness_deviation = abs(128 - mean_brightness)
        brightness_score = max(0, 100 - (brightness_deviation / 128 * 100))

        # Contrast
        contrast = np.std(img_array)
        # Good contrast should have std around 50-70
        if 50 <= contrast <= 70:
            contrast_score = 100
        else:
            contrast_score = max(0, 100 - abs(contrast - 60) * 2)

        # Completeness (check for black borders or cropping)
        completeness_score = self._check_completeness(img_array)

        # Overall score (weighted average)
        overall_score = (
            clarity_score * 0.35 +
            brightness_score * 0.25 +
            contrast_score * 0.25 +
            completeness_score * 0.15
        )

        return DocumentQualityMetrics(
            resolution_dpi=estimated_dpi,
            clarity_score=clarity_score,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            completeness_score=completeness_score,
            overall_score=overall_score
        )

    def _enhance_images(self, images: List[Image.Image]) -> List[Image.Image]:
        """
        Enhance image quality for better OCR

        Techniques:
        - Brightness/contrast adjustment
        - Sharpening
        - Noise reduction
        - Deskewing
        - Binarization
        """
        enhanced = []

        for image in images:
            # Convert to grayscale
            gray = image.convert('L')

            # Adjust brightness
            enhancer = ImageEnhance.Brightness(gray)
            gray = enhancer.enhance(1.2)

            # Adjust contrast
            enhancer = ImageEnhance.Contrast(gray)
            gray = enhancer.enhance(1.3)

            # Sharpen
            enhancer = ImageEnhance.Sharpness(gray)
            gray = enhancer.enhance(1.5)

            # Noise reduction
            gray = gray.filter(ImageFilter.MedianFilter(size=3))

            # TODO: Implement deskewing
            # TODO: Implement adaptive binarization

            enhanced.append(gray)

        return enhanced

    def _extract_metadata(self, doc_info: Dict, file_path: str) -> Dict:
        """Extract document metadata"""
        metadata = {
            'file_name': os.path.basename(file_path),
            'file_size_bytes': doc_info.get('file_size', 0),
            'format': doc_info.get('format', 'unknown'),
            'num_pages': doc_info.get('num_pages', 1)
        }

        # For PDFs, extract PDF metadata
        if doc_info.get('format') == 'pdf':
            # In production:
            # from PyPDF2 import PdfReader
            # reader = PdfReader(file_path)
            # metadata['pdf_info'] = reader.metadata
            # metadata['creation_date'] = reader.metadata.get('/CreationDate')
            # metadata['producer'] = reader.metadata.get('/Producer')
            pass

        # For images, extract EXIF data
        if doc_info.get('images'):
            image = doc_info['images'][0]
            if hasattr(image, '_getexif') and image._getexif():
                exif = image._getexif()
                metadata['exif'] = {
                    'date_taken': exif.get(36867),  # DateTimeOriginal
                    'camera_make': exif.get(271),  # Make
                    'camera_model': exif.get(272)  # Model
                }

        return metadata

    def _analyze_layout(self, doc_info: Dict) -> Dict:
        """
        Analyze document layout structure

        In production:
        - Use LayoutLM or similar model
        - Detect regions: header, body, footer, tables, images
        - Identify reading order

        Returns:
            Layout analysis results
        """
        # TODO: Implement real layout analysis
        # Example using layout detection model:
        # - Detect text regions
        # - Detect tables
        # - Detect images/logos
        # - Determine reading order

        return {
            'regions': [
                {
                    'type': 'header',
                    'bbox': {'x': 0, 'y': 0, 'width': 100, 'height': 10},
                    'confidence': 0.95
                },
                {
                    'type': 'body',
                    'bbox': {'x': 0, 'y': 10, 'width': 100, 'height': 80},
                    'confidence': 0.98
                }
            ],
            'reading_order': ['header', 'body'],
            'has_tables': False,
            'has_images': False
        }

    def _extract_text(self, doc_info: Dict, layout_analysis: Dict) -> Dict:
        """
        Extract text from document using OCR

        In production:
        - Use Tesseract, EasyOCR, or cloud OCR (Google Vision, AWS Textract)
        - Process each layout region separately
        - Maintain spatial relationships
        """
        # TODO: Implement real OCR
        # Example using Tesseract:
        # import pytesseract
        # text = pytesseract.image_to_string(image, config='--psm 6')
        # detailed = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        return {
            'full_text': '',  # Complete extracted text
            'regions': {},  # Text by region
            'confidence': 0.85,  # Average OCR confidence
            'word_count': 0
        }

    def _extract_structured_data(
        self,
        doc_type: str,
        extracted_text: Dict,
        layout_analysis: Dict
    ) -> Dict:
        """
        Extract structured data based on document type

        Uses document-specific templates and field extraction
        """
        if doc_type == DocumentType.DEATH_CERTIFICATE:
            return self._extract_death_certificate_fields(extracted_text)
        elif doc_type in [DocumentType.DRIVERS_LICENSE, DocumentType.STATE_ID]:
            return self._extract_id_fields(extracted_text)
        elif doc_type == DocumentType.BANK_STATEMENT:
            return self._extract_bank_statement_fields(extracted_text)
        else:
            return {}

    def _extract_death_certificate_fields(self, text_data: Dict) -> Dict:
        """Extract specific fields from death certificate"""
        # TODO: Implement field extraction using regex patterns or NER
        # Example fields:
        # - Deceased name
        # - Date of death
        # - Place of death
        # - Cause of death
        # - Certificate number
        # - Date filed

        return {
            'deceased_name': None,
            'date_of_death': None,
            'place_of_death': None,
            'certificate_number': None,
            'date_filed': None
        }

    def _extract_id_fields(self, text_data: Dict) -> Dict:
        """Extract fields from ID document"""
        # TODO: Implement field extraction
        # Example fields:
        # - Full name
        # - Date of birth
        # - License/ID number
        # - Address
        # - Expiration date

        return {
            'name': None,
            'date_of_birth': None,
            'id_number': None,
            'address': None,
            'expiration_date': None
        }

    def _extract_bank_statement_fields(self, text_data: Dict) -> Dict:
        """Extract fields from bank statement"""
        return {
            'account_number': None,
            'statement_period': None,
            'account_holder': None,
            'balance': None
        }

    def _detect_security_features(self, doc_info: Dict, doc_type: str) -> Dict:
        """
        Detect security features in document

        Features to detect:
        - Watermarks
        - Holograms
        - UV elements
        - Microprinting
        - Security threads
        - Guilloché patterns
        """
        # TODO: Implement security feature detection
        # Techniques:
        # - Frequency domain analysis for watermarks
        # - Color channel analysis for UV elements
        # - Texture analysis for microprinting
        # - Pattern recognition for guilloché

        return {
            'watermark_detected': False,
            'hologram_detected': False,
            'security_thread_detected': False,
            'microprint_detected': False,
            'overall_security_score': 0
        }

    def _compute_laplacian_variance(self, image_array: np.ndarray) -> float:
        """Compute Laplacian variance for sharpness detection"""
        # Simple approximation using numpy
        # In production, use cv2.Laplacian
        laplacian = np.abs(
            np.diff(image_array, axis=0)[:-1, :] +
            np.diff(image_array, axis=1)[:, :-1]
        )
        return np.var(laplacian)

    def _check_completeness(self, image_array: np.ndarray) -> float:
        """Check if document is complete (not cropped)"""
        height, width = image_array.shape

        # Check borders for black regions (common in scans)
        border_size = min(20, height // 20)

        top_border = image_array[:border_size, :]
        bottom_border = image_array[-border_size:, :]
        left_border = image_array[:, :border_size]
        right_border = image_array[:, -border_size:]

        # Count dark pixels in borders
        dark_threshold = 50
        dark_pixels = (
            np.sum(top_border < dark_threshold) +
            np.sum(bottom_border < dark_threshold) +
            np.sum(left_border < dark_threshold) +
            np.sum(right_border < dark_threshold)
        )

        total_border_pixels = (
            top_border.size + bottom_border.size +
            left_border.size + right_border.size
        )

        # If less than 30% of border is dark, assume complete
        dark_ratio = dark_pixels / total_border_pixels
        completeness_score = max(0, 100 - (dark_ratio * 200))

        return completeness_score

    def convert_document(
        self,
        input_path: str,
        output_format: str,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Convert document to different format

        Args:
            input_path: Input document path
            output_format: Target format (pdf, png, jpg, tiff)
            output_path: Optional output path

        Returns:
            Conversion result
        """
        # TODO: Implement document conversion
        # Use PIL for image conversions
        # Use pdf2image and img2pdf for PDF conversions

        return {
            'success': False,
            'error': 'Not implemented'
        }

    def merge_documents(self, document_paths: List[str], output_path: str) -> Dict:
        """
        Merge multiple documents into single PDF

        Args:
            document_paths: List of document paths to merge
            output_path: Output PDF path

        Returns:
            Merge result
        """
        # TODO: Implement document merging
        # Use PyPDF2 or img2pdf

        return {
            'success': False,
            'error': 'Not implemented'
        }
