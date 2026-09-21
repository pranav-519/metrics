from typing import Dict, Any, Optional
from pydantic import BaseModel

class CalibrationResult(BaseModel):
    is_calibrated: bool
    calibration_method: str  # "reference_object", "dpi_metadata", "user_specified", "uncalibrated_heuristic"
    pixels_per_mm: float
    confidence_rating: str  # "VERIFIED", "HIGH", "ESTIMATED", "UNCALIBRATED"
    notes: str

class PhysicalMeasurementService:
    """
    Handles physical font and bounding box dimension calculations under Legal Metrology rules.
    CRITICAL: Never equates raw pixels directly to millimeters.
    Requires or derives a pixel-to-millimeter ratio and marks results as
    ESTIMATED vs VERIFIED.
    """

    # Reference object real physical dimensions (in mm)
    REFERENCE_STANDARDS = {
        "rupee_coin_5": 23.0,       # 5 Rupee coin diameter = 23 mm
        "rupee_coin_10": 27.0,      # 10 Rupee coin diameter = 27 mm
        "id_card_width": 85.6,      # Standard ISO/IEC 7810 ID-1 (Aadhaar/Credit Card) width = 85.6 mm
        "id_card_height": 53.98,    # Standard ISO/IEC 7810 ID-1 height = 53.98 mm
    }

    # Default heuristic pixel density for smartphone photography at ~25cm distance
    DEFAULT_HEURISTIC_PIXELS_PER_MM = 11.8 # approx 300 DPI (300 / 25.4)

    @classmethod
    def calibrate_from_reference(
        cls,
        reference_type: str,
        detected_pixel_dimension: float
    ) -> CalibrationResult:
        """Calibrates pixel-to-mm ratio using a known physical reference object in the image."""
        if reference_type not in cls.REFERENCE_STANDARDS or detected_pixel_dimension <= 0:
            return CalibrationResult(
                is_calibrated=False,
                calibration_method="uncalibrated_heuristic",
                pixels_per_mm=cls.DEFAULT_HEURISTIC_PIXELS_PER_MM,
                confidence_rating="UNCALIBRATED",
                notes="Standard reference object not detected. Using camera heuristic baseline."
            )

        real_mm = cls.REFERENCE_STANDARDS[reference_type]
        px_per_mm = detected_pixel_dimension / real_mm

        return CalibrationResult(
            is_calibrated=True,
            calibration_method=f"reference_{reference_type}",
            pixels_per_mm=round(px_per_mm, 3),
            confidence_rating="VERIFIED",
            notes=f"Calibrated against known standard '{reference_type}' ({real_mm} mm). Highly reliable."
        )

    @classmethod
    def estimate_font_height_mm(
        cls,
        bbox_height_px: float,
        pixels_per_mm: Optional[float] = None,
        is_calibrated: bool = False
    ) -> Dict[str, Any]:
        """
        Converts bounding box height in pixels to physical height in millimeters.
        Capital letters (x-height to cap-height) typically occupy ~70-75% of text bounding box height.
        """
        ratio = pixels_per_mm if (pixels_per_mm and pixels_per_mm > 0) else cls.DEFAULT_HEURISTIC_PIXELS_PER_MM
        
        # Approximate cap-height of numeral/letter inside OCR box
        approx_letter_height_px = bbox_height_px * 0.72
        height_mm = approx_letter_height_px / ratio

        confidence = "VERIFIED" if is_calibrated else "ESTIMATED"

        return {
            "height_mm": round(height_mm, 2),
            "confidence": confidence,
            "pixels_per_mm_used": round(ratio, 2),
            "is_calibrated": is_calibrated,
            "disclaimer": "Statutory compliance inspection measurement. Calibration reference required for legal proceedings."
        }

    @classmethod
    def evaluate_font_statutory_threshold(
        cls,
        estimated_height_mm: float,
        required_height_mm: float,
        is_calibrated: bool
    ) -> Dict[str, Any]:
        """Checks if estimated font height satisfies the statutory minimum."""
        is_compliant = estimated_height_mm >= required_height_mm
        margin = estimated_height_mm - required_height_mm

        if not is_calibrated:
            verdict = "LIKELY_COMPLIANT" if is_compliant else "POTENTIAL_NON_COMPLIANCE"
            note = f"Estimated font height is ~{estimated_height_mm:.1f}mm (Statutory min: {required_height_mm:.1f}mm). Note: Uncalibrated estimate."
        else:
            verdict = "VERIFIED_COMPLIANT" if is_compliant else "POTENTIAL_NON_COMPLIANCE"
            note = f"Calibrated font height is {estimated_height_mm:.1f}mm (Statutory min: {required_height_mm:.1f}mm)."

        return {
            "verdict": verdict,
            "is_compliant": is_compliant,
            "margin_mm": round(margin, 2),
            "note": note
        }
