import os
import time
import cv2
import numpy as np
from PIL import Image
from typing import Optional, List, Dict, Any

from app.services.ocr.base import BaseOCREngine, OCRResult, OCRBoxResult
from app.core.config import settings

class RapidOCREngine(BaseOCREngine):
    """
    Primary Local Pre-Trained OCR Engine powered by RapidOCR ONNX Runtime.
    Performs real inference on package imagery to extract text tokens,
    bounding box coordinates, and detection confidences without GPU dependencies.
    """

    def __init__(self):
        self.engine_name = "RapidOCR-ONNX"
        self._engine = None
        self._init_error = None
        self._init_engine()

    def _init_engine(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
            self._init_error = None
        except Exception as e:
            self._engine = None
            self._init_error = str(e)

    def is_available(self) -> bool:
        return self._engine is not None

    def extract_text(
        self,
        image_path: str,
        image_id: Optional[int] = None,
        image_type: Optional[str] = "FRONT",
        confidence_threshold: Optional[float] = None,
        **kwargs
    ) -> OCRResult:
        start_time = time.time()
        threshold = confidence_threshold if confidence_threshold is not None else settings.OCR_CONFIDENCE_THRESHOLD

        if not os.path.exists(image_path):
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"Image file not found at path: {image_path}",
                processing_time_ms=0.0
            )

        if not self.is_available():
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"RapidOCR engine initialization failed: {self._init_error}",
                processing_time_ms=0.0
            )

        # Read image
        try:
            img = cv2.imread(image_path)
            if img is None:
                pil_img = Image.open(image_path)
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            img_h, img_w = img.shape[:2]
        except Exception as e:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"Could not read image file: {str(e)}",
                processing_time_ms=round((time.time() - start_time) * 1000.0, 2)
            )

        # Execute RapidOCR inference
        try:
            results, elapse = self._engine(img)
        except Exception as e:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=self.engine_name,
                status="FAILED",
                error_message=f"RapidOCR inference error: {str(e)}",
                processing_time_ms=round((time.time() - start_time) * 1000.0, 2)
            )

        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)

        # Handle empty detection cleanly (no text on image)
        if not results:
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                total_detections=0,
                average_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                high_confidence_count=0,
                engine_name=self.engine_name,
                processing_time_ms=elapsed_ms,
                status="NO_TEXT_DETECTED"
            )

        boxes: List[OCRBoxResult] = []
        confidences: List[float] = []
        text_lines: List[str] = []
        high_conf_count = 0

        for idx, item in enumerate(results):
            # item structure: [dt_box, text, confidence]
            dt_box, text, score = item
            if not text or not text.strip():
                continue

            cleaned_text = text.strip()
            conf = float(score)
            confidences.append(conf)
            text_lines.append(cleaned_text)

            if conf >= threshold:
                high_conf_count += 1

            # Convert 4-point polygon into pixel and normalized relative coordinates
            xs = [float(p[0]) for p in dt_box]
            ys = [float(p[1]) for p in dt_box]
            x1 = int(round(min(xs)))
            y1 = int(round(min(ys)))
            x2 = int(round(max(xs)))
            y2 = int(round(max(ys)))
            x = max(0, x1)
            y = max(0, y1)
            w = max(0, x2 - x1)
            h = max(0, y2 - y1)

            bbox_dict = {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "x_rel": round(x / max(img_w, 1), 4),
                "y_rel": round(y / max(img_h, 1), 4),
                "w_rel": round(w / max(img_w, 1), 4),
                "h_rel": round(h / max(img_h, 1), 4),
                "polygon": [[round(float(p[0]), 1), round(float(p[1]), 1)] for p in dt_box]
            }

            boxes.append(OCRBoxResult(
                text=cleaned_text,
                confidence=round(conf, 4),
                bounding_box=bbox_dict,
                line_number=idx + 1,
                image_id=image_id,
                image_type=image_type
            ))

        avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        min_conf = round(min(confidences), 4) if confidences else 0.0
        max_conf = round(max(confidences), 4) if confidences else 0.0

        return OCRResult(
            image_id=image_id,
            image_type=image_type,
            full_text="\n".join(text_lines),
            boxes=boxes,
            total_detections=len(boxes),
            average_confidence=avg_conf,
            min_confidence=min_conf,
            max_confidence=max_conf,
            high_confidence_count=high_conf_count,
            engine_name=self.engine_name,
            processing_time_ms=elapsed_ms,
            status="COMPLETED"
        )
