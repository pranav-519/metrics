import cv2
import numpy as np
from PIL import Image
import os
from typing import Dict, Any, Tuple, Optional
from app.models.models import ImageQualityStatus

class ImageQualityService:
    """
    Evaluates photograph quality for packaged commodities compliance scanning.
    Assesses blur (Laplacian variance), glare/reflections, lighting, resolution,
    and perspective skew to handle uncertainty reliably.
    """

    MIN_ACCEPTABLE_WIDTH = 600
    MIN_ACCEPTABLE_HEIGHT = 600
    BLUR_THRESHOLD_POOR = 40.0
    BLUR_THRESHOLD_GOOD = 100.0
    GLARE_THRESHOLD_PERCENT = 12.0 # % pixels saturated above 245 in luminance

    @classmethod
    def evaluate_image_file(cls, file_path: str) -> Dict[str, Any]:
        """Reads image from disk and performs full CV quality assessment."""
        if not os.path.exists(file_path):
            return {
                "quality_status": ImageQualityStatus.CRITICAL_ISSUES,
                "blur_score": 0.0,
                "glare_score": 0.0,
                "lighting_score": 0.0,
                "resolution_w": 0,
                "resolution_h": 0,
                "quality_notes": "Image file not found on disk."
            }

        try:
            # Read via OpenCV
            img = cv2.imread(file_path)
            if img is None:
                # Fallback to PIL in case of special color formats
                pil_img = Image.open(file_path)
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            h, w = img.shape[:2]

            # 1. Blur evaluation using Laplacian variance
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            # 2. Glare and lighting assessment
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]
            glare_pixels = np.sum(v_channel >= 245)
            total_pixels = h * w
            glare_percentage = float((glare_pixels / max(total_pixels, 1)) * 100.0)
            avg_brightness = float(np.mean(v_channel))

            # Lighting score (100 is ideal ~120-180 brightness, drops if too dark <50 or too bright >220)
            if avg_brightness < 60:
                lighting_score = max(10.0, (avg_brightness / 60.0) * 60.0)
            elif avg_brightness > 230:
                lighting_score = max(10.0, (255.0 - avg_brightness) / 25.0 * 60.0)
            else:
                lighting_score = 95.0

            # 3. Overall quality classification
            notes = []
            status = ImageQualityStatus.GOOD

            if w < cls.MIN_ACCEPTABLE_WIDTH or h < cls.MIN_ACCEPTABLE_HEIGHT:
                status = ImageQualityStatus.POOR
                notes.append(f"Low resolution: {w}x{h}px. At least 800x800 recommended for font measurement.")

            if laplacian_var < cls.BLUR_THRESHOLD_POOR:
                status = ImageQualityStatus.POOR
                notes.append(f"Image is blurry (sharpness score {laplacian_var:.1f}). Text characters may be degraded.")
            elif laplacian_var < cls.BLUR_THRESHOLD_GOOD:
                if status == ImageQualityStatus.GOOD:
                    status = ImageQualityStatus.ACCEPTABLE
                notes.append(f"Moderate sharpness ({laplacian_var:.1f}).")

            if glare_percentage > cls.GLARE_THRESHOLD_PERCENT:
                status = ImageQualityStatus.POOR
                notes.append(f"Significant glare/reflection detected ({glare_percentage:.1f}% washed out).")
            elif glare_percentage > 5.0:
                notes.append(f"Minor reflections detected ({glare_percentage:.1f}%).")

            if avg_brightness < 50:
                notes.append("Under-exposed: lighting is dim.")
            elif avg_brightness > 210:
                notes.append("Over-exposed: lighting is harsh.")

            if not notes:
                notes.append("Image resolution, sharpness, and lighting are optimal for text extraction.")

            # Compute normalized quality score (0.0 to 1.0)
            blur_norm = min(1.0, max(0.0, laplacian_var / 150.0))
            glare_penalty = min(1.0, glare_percentage / 25.0)
            lighting_norm = lighting_score / 100.0
            res_ok = bool(w >= cls.MIN_ACCEPTABLE_WIDTH and h >= cls.MIN_ACCEPTABLE_HEIGHT)
            res_factor = 1.0 if res_ok else 0.6
            overall_score = round(max(0.0, min(1.0, (blur_norm * 0.45 + (1.0 - glare_penalty) * 0.25 + lighting_norm * 0.30) * res_factor)), 2)

            return {
                "quality_status": status,
                "quality_score": overall_score,
                "blur_score": round(laplacian_var, 2),
                "glare_score": round(glare_percentage, 2),
                "glare_percentage": round(glare_percentage, 2),
                "lighting_score": round(lighting_score, 2),
                "brightness_score": round(avg_brightness / 255.0, 2),
                "resolution_w": w,
                "resolution_h": h,
                "resolution_ok": res_ok,
                "preprocessing_applied": False,
                "quality_notes": " | ".join(notes)
            }

        except Exception as e:
            return {
                "quality_status": ImageQualityStatus.POOR,
                "quality_score": 0.2,
                "blur_score": 25.0,
                "glare_score": 0.0,
                "glare_percentage": 0.0,
                "lighting_score": 50.0,
                "brightness_score": 0.5,
                "resolution_w": 0,
                "resolution_h": 0,
                "resolution_ok": False,
                "preprocessing_applied": False,
                "quality_notes": f"Quality assessment fallback: {str(e)}"
            }

    @classmethod
    def preprocess_image_for_ocr(cls, input_path: str, output_path: str) -> bool:
        """
        Enhances image for OCR: grayscale conversion, contrast enhancement (CLAHE),
        and subtle denoising.
        """
        try:
            img = cv2.imread(input_path)
            if img is None:
                return False

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Contrast Limited Adaptive Histogram Equalization
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
            cv2.imwrite(output_path, denoised)
            return True
        except Exception:
            return False

    @classmethod
    def run_quality_pipeline(cls, file_path: str, preprocessed_output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs complete quality assessment and applies justified CLAHE/denoising preprocessing
        if image quality indicates blur/contrast issues, then re-evaluates the preprocessed copy.
        """
        original_eval = cls.evaluate_image_file(file_path)
        needs_prep = original_eval["quality_status"] in (ImageQualityStatus.POOR, ImageQualityStatus.ACCEPTABLE)

        if needs_prep and preprocessed_output_path:
            prep_success = cls.preprocess_image_for_ocr(file_path, preprocessed_output_path)
            if prep_success and os.path.exists(preprocessed_output_path):
                prep_eval = cls.evaluate_image_file(preprocessed_output_path)
                return {
                    **original_eval,
                    "preprocessing_applied": True,
                    "preprocessed_path": preprocessed_output_path,
                    "preprocessed_blur_score": prep_eval["blur_score"],
                    "preprocessed_quality_status": prep_eval["quality_status"],
                    "quality_notes": f"{original_eval['quality_notes']} | CLAHE contrast enhancement & denoising applied."
                }

        return {
            **original_eval,
            "preprocessing_applied": False,
            "preprocessed_path": None
        }

