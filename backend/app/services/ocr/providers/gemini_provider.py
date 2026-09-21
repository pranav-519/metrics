import os
import time
from typing import Optional, List, Dict, Any
from app.services.ocr.base import BaseOCREngine, OCRResult, OCRBoxResult
from app.core.config import settings

class GeminiVisionOCREngine(BaseOCREngine):
    """
    Optional Cloud Vision Fallback provider using Google Gemini Vision API.
    Enabled ONLY when GEMINI_API_KEY is configured in backend environment.
    Never mandatory for local offline operation.
    """

    def __init__(self):
        self.engine_name = "GeminiVision-Cloud"

    def is_available(self) -> bool:
        return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    def extract_text(
        self,
        image_path: str,
        image_id: Optional[int] = None,
        image_type: Optional[str] = "FRONT",
        **kwargs
    ) -> OCRResult:
        if not self.is_available():
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message="GEMINI_API_KEY is not configured in backend environment."
            )

        start_time = time.time()
        # Optional cloud fallback logic via httpx if API key provided
        try:
            import httpx
            import base64

            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            prompt = (
                "Extract all visible text declarations printed on this packaged commodity. "
                "Output each line of text with its approximate bounding box."
            )
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                    ]
                }]
            }

            resp = httpx.post(url, json=payload, timeout=20.0)
            if resp.status_code == 200:
                data = resp.json()
                text_content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                lines = [l.strip() for l in text_content.split("\n") if l.strip()]
                boxes = [
                    OCRBoxResult(
                        text=l,
                        confidence=0.90,
                        bounding_box={"x1": 0, "y1": idx * 25, "x2": 400, "y2": (idx + 1) * 25, "x": 0, "y": idx * 25, "w": 400, "h": 25},
                        line_number=idx + 1,
                        image_id=image_id,
                        image_type=image_type
                    )
                    for idx, l in enumerate(lines)
                ]
                elapsed = round((time.time() - start_time) * 1000.0, 2)
                return OCRResult(
                    image_id=image_id,
                    image_type=image_type,
                    full_text=text_content,
                    boxes=boxes,
                    total_detections=len(boxes),
                    average_confidence=0.90,
                    engine_name=self.engine_name,
                    processing_time_ms=elapsed,
                    status="COMPLETED"
                )
            else:
                return OCRResult(
                    image_id=image_id,
                    image_type=image_type,
                    full_text="",
                    boxes=[],
                    engine_name=self.engine_name,
                    status="FAILED",
                    error_message=f"Gemini API returned status {resp.status_code}: {resp.text[:200]}"
                )
        except Exception as e:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"Gemini Vision API execution error: {str(e)}"
            )
