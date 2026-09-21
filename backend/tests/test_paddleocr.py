import os
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image, ImageDraw
import numpy as np

from app.services.ocr.providers.paddleocr_provider import PaddleOCRProvider
from app.services.ocr.engine import PretrainedOCREngine
from app.services.ocr.base import OCRResult, OCRBoxResult
from app.services.extraction.declarations import DeclarationExtractorService


def create_package_label_image(text: str = "MRP Rs 249.00 INCL OF ALL TAXES", size=(640, 200)) -> Image.Image:
    """Creates synthetic packaged product label image."""
    img = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 80), text, fill=(0, 0, 0))
    return img


def create_blank_image(size=(640, 200)) -> Image.Image:
    """Creates a blank white image with no text."""
    return Image.new("RGB", size, color=(255, 255, 255))


# =====================================================================
# UNIT TESTS (Fast, Isolated, Mocked)
# =====================================================================

def test_paddleocr_unit_provider_initialization():
    """Unit: Verify provider defaults to PP-OCRv6, English language, and CPU device."""
    provider = PaddleOCRProvider()
    assert provider.engine_name == "PaddleOCR-PP-OCRv6"
    assert provider.ocr_version == "PP-OCRv6"
    assert provider.lang == "en"
    assert provider.device == "cpu"
    assert provider.is_available() is True


def test_paddleocr_unit_coordinate_mapping_and_bounding_box(tmp_path):
    """Unit: Verify native PaddleOCR polygon is mapped into exact 8-point and 4-point relative bboxes."""
    # Create fake 400x200 image
    test_img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    test_path = str(tmp_path / "mock_label.jpg")
    test_img.save(test_path, format="JPEG")

    # Mock PaddleOCR predict output: 1 detection with polygon [[50, 60], [250, 60], [250, 100], [50, 100]]
    fake_pred = [{
        "rec_texts": ["NET WT 750 g"],
        "rec_scores": [0.9654],
        "rec_polys": [np.array([[50, 60], [250, 60], [250, 100], [50, 100]])],
        "rec_boxes": [[50, 60, 250, 100]]
    }]

    provider = PaddleOCRProvider()
    with patch("app.services.ocr.providers.paddleocr_provider._shared_paddle_engine") as mock_engine:
        mock_engine.predict.return_value = fake_pred
        res = provider.extract_text(test_path, image_id=42, image_type="FRONT")

    assert res.status == "COMPLETED"
    assert res.total_detections == 1
    assert res.image_id == 42
    assert res.image_type == "FRONT"
    assert res.engine_name == "PaddleOCR-PP-OCRv6"

    box = res.boxes[0]
    assert box.text == "NET WT 750 g"
    assert box.confidence == 0.9654
    assert box.image_id == 42
    assert box.image_type == "FRONT"

    bbox = box.bounding_box
    # Pixel coordinates
    assert bbox["x1"] == 50
    assert bbox["y1"] == 60
    assert bbox["x2"] == 250
    assert bbox["y2"] == 100
    assert bbox["x"] == 50
    assert bbox["y"] == 60
    assert bbox["w"] == 200
    assert bbox["h"] == 40

    # Normalized relative coordinates (clamped 0.0 to 1.0)
    assert bbox["x_rel"] == pytest.approx(50 / 400, 0.001)
    assert bbox["y_rel"] == pytest.approx(60 / 200, 0.001)
    assert bbox["w_rel"] == pytest.approx(200 / 400, 0.001)
    assert bbox["h_rel"] == pytest.approx(40 / 200, 0.001)

    # Full polygon
    assert len(bbox["polygon"]) == 4
    assert bbox["polygon"] == [[50.0, 60.0], [250.0, 60.0], [250.0, 100.0], [50.0, 100.0]]


def test_paddleocr_unit_zero_fake_text_on_empty(tmp_path):
    """Unit: Empty detections produce NO_TEXT_DETECTED with zero fabricated strings."""
    test_img = Image.new("RGB", (300, 150), color=(255, 255, 255))
    test_path = str(tmp_path / "blank.jpg")
    test_img.save(test_path, format="JPEG")

    fake_pred = [{
        "rec_texts": [],
        "rec_scores": [],
        "rec_polys": [],
        "rec_boxes": []
    }]

    provider = PaddleOCRProvider()
    with patch("app.services.ocr.providers.paddleocr_provider._shared_paddle_engine") as mock_engine:
        mock_engine.predict.return_value = fake_pred
        res = provider.extract_text(test_path, image_id=1, image_type="BACK")

    assert res.status == "NO_TEXT_DETECTED"
    assert res.total_detections == 0
    assert len(res.boxes) == 0
    assert res.full_text == ""
    assert res.average_confidence == 0.0
    assert res.high_confidence_count == 0


def test_paddleocr_unit_extraction_pipeline_compatibility():
    """Unit: Verify PaddleOCR output structures plug directly into DeclarationExtractorService."""
    boxes = [
        OCRBoxResult(
            text="MRP Rs 150.00 (INCL OF ALL TAXES)",
            confidence=0.975,
            bounding_box={"x": 50, "y": 60, "w": 250, "h": 30, "x1": 50, "y1": 60, "x2": 300, "y2": 90, "x_rel": 0.05, "y_rel": 0.1, "w_rel": 0.25, "h_rel": 0.05},
            line_number=1,
            image_id=10,
            image_type="FRONT"
        ),
        OCRBoxResult(
            text="NET WEIGHT: 500 g",
            confidence=0.962,
            bounding_box={"x": 50, "y": 100, "w": 180, "h": 25, "x1": 50, "y1": 100, "x2": 230, "y2": 125, "x_rel": 0.05, "y_rel": 0.2, "w_rel": 0.18, "h_rel": 0.04},
            line_number=2,
            image_id=10,
            image_type="FRONT"
        ),
        OCRBoxResult(
            text="MFD DATE 01/2026",
            confidence=0.940,
            bounding_box={"x": 50, "y": 140, "w": 170, "h": 25, "x1": 50, "y1": 140, "x2": 220, "y2": 165, "x_rel": 0.05, "y_rel": 0.3, "w_rel": 0.17, "h_rel": 0.04},
            line_number=3,
            image_id=10,
            image_type="FRONT"
        ),
        OCRBoxResult(
            text="COUNTRY OF ORIGIN: INDIA",
            confidence=0.985,
            bounding_box={"x": 50, "y": 180, "w": 220, "h": 25, "x1": 50, "y1": 180, "x2": 270, "y2": 205, "x_rel": 0.05, "y_rel": 0.4, "w_rel": 0.22, "h_rel": 0.04},
            line_number=4,
            image_id=10,
            image_type="FRONT"
        )
    ]

    image_boxes_map = [
        {
            "image_id": 10,
            "image_role": "front",
            "image_type": "FRONT",
            "boxes": [
                {
                    "id": idx + 1,
                    "text": b.text,
                    "confidence": b.confidence,
                    "bounding_box": b.bounding_box,
                    "line_number": b.line_number
                }
                for idx, b in enumerate(boxes)
            ]
        }
    ]

    # Execute downstream extraction
    extracted_list = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    extracted = {c.field_name: c for c in extracted_list}

    assert "MRP" in extracted
    assert extracted["MRP"].normalized_value == "150.00"
    assert extracted["MRP"].status == "FOUND"

    assert "NET_QUANTITY" in extracted
    assert extracted["NET_QUANTITY"].normalized_value == "500 g"
    assert extracted["NET_QUANTITY"].unit == "g"

    assert "MANUFACTURING_DATE" in extracted
    assert extracted["MANUFACTURING_DATE"].status == "FOUND"

    assert "COUNTRY_OF_ORIGIN" in extracted
    assert extracted["COUNTRY_OF_ORIGIN"].normalized_value.upper() == "INDIA"


# =====================================================================
# INTEGRATION TESTS (Real Pretrained PP-OCRv6 Model Inference)
# =====================================================================

def test_paddleocr_integration_real_model_inference(tmp_path):
    """Integration: Execute real PP-OCRv6 inference on synthetic packaged label."""
    img = create_package_label_image("MRP Rs 249.00 INCL OF ALL TAXES", size=(640, 200))
    test_path = str(tmp_path / "real_paddle_label.jpg")
    img.save(test_path, format="JPEG")

    provider = PaddleOCRProvider()
    res = provider.extract_text(test_path, image_id=100, image_type="FRONT")

    assert res.status == "COMPLETED"
    assert res.total_detections > 0
    assert len(res.boxes) > 0
    assert res.engine_name == "PaddleOCR-PP-OCRv6"
    assert res.average_confidence > 0.50
    assert any("249" in b.text or "MRP" in b.text.upper() or "TAXES" in b.text.upper() for b in res.boxes)

    # Verify bounding box attributes on real output
    first_box = res.boxes[0]
    bbox = first_box.bounding_box
    assert 0.0 <= bbox["x_rel"] <= 1.0
    assert 0.0 <= bbox["y_rel"] <= 1.0
    assert 0.0 <= bbox["w_rel"] <= 1.0
    assert 0.0 <= bbox["h_rel"] <= 1.0
    assert bbox["w"] > 0
    assert bbox["h"] > 0
    assert len(bbox["polygon"]) >= 4


def test_paddleocr_integration_real_blank_image(tmp_path):
    """Integration: Verify real PP-OCRv6 on blank image returns NO_TEXT_DETECTED without fake text."""
    blank = create_blank_image(size=(500, 200))
    test_path = str(tmp_path / "real_paddle_blank.jpg")
    blank.save(test_path, format="JPEG")

    provider = PaddleOCRProvider()
    res = provider.extract_text(test_path, image_id=101, image_type="FRONT")

    assert res.status == "NO_TEXT_DETECTED"
    assert res.total_detections == 0
    assert len(res.boxes) == 0
    assert res.full_text == ""
    assert res.average_confidence == 0.0


def test_paddleocr_integration_orchestrator_primary_path(tmp_path):
    """Integration: Verify PretrainedOCREngine uses PaddleOCR PP-OCRv6 as default primary engine."""
    orchestrator = PretrainedOCREngine()
    assert orchestrator.engine_name == "PaddleOCR-PP-OCRv6"

    img = create_package_label_image("NET QTY 1 kg", size=(500, 150))
    test_path = str(tmp_path / "real_orch_label.jpg")
    img.save(test_path, format="JPEG")

    res = orchestrator.extract_text(test_path, image_id=102, image_type="FRONT")
    assert res.status == "COMPLETED"
    assert res.engine_name == "PaddleOCR-PP-OCRv6"
    assert res.total_detections > 0
    assert any("1" in b.text or "KG" in b.text.upper() or "NET" in b.text.upper() for b in res.boxes)


def test_paddleocr_debug_visualization(tmp_path):
    """Integration: Verify visualize_ocr_boxes generates overlay image without error."""
    img = create_package_label_image("MRP Rs 50.00", size=(400, 150))
    test_path = str(tmp_path / "vis_input.jpg")
    vis_out_path = str(tmp_path / "vis_output.jpg")
    img.save(test_path, format="JPEG")

    provider = PaddleOCRProvider()
    res = provider.extract_text(test_path, image_id=201, image_type="FRONT")
    assert res.status == "COMPLETED"

    vis_img = PaddleOCRProvider.visualize_ocr_boxes(test_path, res, output_path=vis_out_path)
    assert vis_img is not None
    assert os.path.exists(vis_out_path)
    assert os.path.getsize(vis_out_path) > 0
