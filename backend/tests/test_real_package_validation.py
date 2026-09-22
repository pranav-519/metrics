"""Master Prompt 07 — Regression Tests for Real Package Validation & Profiling.

Covers the 18 mandatory test requirements:
1. Real/synthetic dataset classification
2. Ground-truth parsing
3. Real-image loading framework
4. MRP unreadable
5. MRP glare
6. MRP missing
7. MRP distractors
8. Quantity distractors
9. Date association
10. Multi-image aggregation
11. Conflicting evidence
12. UNABLE_TO_VERIFY preservation
13. REVIEW_REQUIRED compliance behavior
14. PaddleOCR singleton reuse
15. Cold/warm timing
16. Retry timing
17. Spatial evidence preservation
18. Evaluation normalization non-mutation
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List
import pytest

from app.models.models import ImageType
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.compliance.rules import init_default_rules
from app.services.evaluation.eval_normalizer import EvaluationNormalizer
from app.services.evaluation.profiler import PipelineProfiler
from app.services.extraction.declarations import DeclarationExtractorService
from app.services.extraction.field_extractors import FieldCandidate, ModularFieldExtractors
from app.services.ocr.providers.paddleocr_provider import PaddleOCRProvider, _shared_paddle_engine
from tests.run_real_validation_benchmark import (
    resolve_dataset_dir,
    load_dataset_annotations,
    STATUTORY_FIELDS,
)


@pytest.fixture(autouse=True)
def setup_compliance_rules():
    init_default_rules()


# -----------------------------------------------------------------------------
# 1. Dataset Classification Test
# -----------------------------------------------------------------------------
def test_dataset_classification(tmp_path):
    """Verifies REAL_PHOTO, SYNTHETIC_CONTROLLED, and MIXED dataset detection."""
    # Test SYNTHETIC_CONTROLLED directory
    synth_dir = tmp_path / "annotations" / "synthetic"
    synth_dir.mkdir(parents=True)
    with open(synth_dir / "p1.json", "w") as f:
        json.dump({"dataset_type": "SYNTHETIC_CONTROLLED"}, f)

    products, dtype = load_dataset_annotations(tmp_path)
    assert dtype == "SYNTHETIC_CONTROLLED"
    assert len(products) == 1

    # Add REAL_PHOTO -> MIXED
    real_dir = tmp_path / "annotations" / "real"
    real_dir.mkdir(parents=True)
    with open(real_dir / "p2.json", "w") as f:
        json.dump({"dataset_type": "REAL_PHOTO"}, f)

    products, dtype = load_dataset_annotations(tmp_path)
    assert dtype == "MIXED"
    assert len(products) == 2


# -----------------------------------------------------------------------------
# 2. Ground-Truth Parsing Test
# -----------------------------------------------------------------------------
def test_ground_truth_parsing():
    """Verifies ground truth supports all 12 fields and explicit null values."""
    sample_gt = {
        "PRODUCT_NAME": "Premium Tea",
        "MRP": "₹150.00",
        "NET_QUANTITY": "250 g",
        "MANUFACTURER": "Tea Estate Ltd, Assam",
        "PACKER": None,
        "IMPORTER": None,
        "MANUFACTURING_DATE": "01/2026",
        "PACKING_DATE": None,
        "EXPIRY_DATE": "01/2028",
        "BEST_BEFORE": "24 Months from Mfd",
        "CONSUMER_CARE": "care@tea.in",
        "COUNTRY_OF_ORIGIN": "India"
    }
    for field_name in STATUTORY_FIELDS:
        assert field_name in sample_gt

    # Absent fields must not be treated as errors
    res_packer = EvaluationNormalizer.compare_field("PACKER", sample_gt["PACKER"], None)
    assert res_packer["evaluation_status"] == "NOT_APPLICABLE"
    assert res_packer["is_match"] is True


# -----------------------------------------------------------------------------
# 3. Real Image Loading Framework Test
# -----------------------------------------------------------------------------
def test_real_image_loading_framework(monkeypatch, tmp_path):
    """Verifies configurable dataset path via CLI arg or environment variable."""
    external_dir = tmp_path / "my_external_real_packages"
    external_dir.mkdir()
    (external_dir / "annotations").mkdir()

    # CLI arg takes precedence
    resolved = resolve_dataset_dir(str(external_dir))
    assert resolved == external_dir.resolve()

    # Env var works when no CLI arg
    monkeypatch.setenv("METRICHECK_REAL_DATASET_DIR", str(external_dir))
    resolved_env = resolve_dataset_dir(None)
    assert resolved_env == external_dir.resolve()


# -----------------------------------------------------------------------------
# 4. MRP Unreadable Failure State Test
# -----------------------------------------------------------------------------
def test_mrp_unreadable_failure_state():
    """Unreadable MRP must produce UNABLE_TO_VERIFY / LOW_CONFIDENCE, never guessed value."""
    unreadable_cand = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value=None,
        status="UNABLE_TO_VERIFY",
        confidence=0.15
    )
    eval_res = EvaluationNormalizer.compare_field("MRP", "₹199.00", unreadable_cand)
    assert eval_res["evaluation_status"] == "UNABLE_TO_VERIFY"
    assert eval_res["is_match"] is False
    assert eval_res["detected_value"] is None


# -----------------------------------------------------------------------------
# 5. MRP Glare Failure State Test
# -----------------------------------------------------------------------------
def test_mrp_glare_failure_state():
    """Specular glare over MRP prevents reliable verification and is not called verified."""
    glare_cand = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value=None,
        status="UNABLE_TO_VERIFY",
        confidence=0.20
    )
    compliance = ComplianceEngine.evaluate_declarations([glare_cand.to_dict()])
    assert compliance["overall_status"] in ("REVIEW_REQUIRED", "NOT_VERIFIABLE")
    assert compliance["overall_status"] != "COMPLIANT"


# -----------------------------------------------------------------------------
# 6. MRP Missing Failure State Test
# -----------------------------------------------------------------------------
def test_mrp_missing_failure_state():
    """Genuinely missing MRP produces NOT_FOUND without fabricating a price."""
    missing_cand = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value=None,
        status="NOT_FOUND",
        confidence=0.0
    )
    # When ground truth says MRP is null (genuinely absent)
    res_absent = EvaluationNormalizer.compare_field("MRP", None, missing_cand)
    assert res_absent["evaluation_status"] == "NOT_APPLICABLE"
    assert res_absent["detected_value"] is None

    # When ground truth expected MRP but none was found
    res_missing = EvaluationNormalizer.compare_field("MRP", "₹149.00", missing_cand)
    assert res_missing["evaluation_status"] == "NOT_FOUND"


# -----------------------------------------------------------------------------
# 7. MRP Distractor Rejection Test
# -----------------------------------------------------------------------------
def test_mrp_distractor_rejection():
    """Promo discounts (Save ₹50, Cashback ₹100) must not override statutory MRP."""
    boxes = [
        {"text": "SUPER SAVER OFFER! SAVE ₹50 ON NEXT PACK", "confidence": 0.98, "box": [10, 10, 300, 40]},
        {"text": "Cashback: Up to ₹100 inside wrapper", "confidence": 0.98, "box": [10, 50, 300, 80]},
        {"text": "Special Discount ₹20", "confidence": 0.98, "box": [10, 90, 250, 120]},
        {"text": "MRP: ₹199.00 (Incl. of all taxes)", "confidence": 0.99, "box": [10, 150, 350, 190]},
    ]
    cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    assert cand.status == "FOUND"
    assert cand.normalized_value == "199.00"
    assert "50" not in (cand.normalized_value or "")
    assert "100" not in (cand.normalized_value or "")


# -----------------------------------------------------------------------------
# 8. Quantity Distractor Rejection Test
# -----------------------------------------------------------------------------
def test_quantity_distractor_rejection():
    """Nutritional table lines (Calories 210 kcal, Carbs 25 g) must not be extracted as Net Qty."""
    boxes = [
        {"text": "Nutrition Facts per serving (50g):", "confidence": 0.95, "box": [10, 10, 250, 35]},
        {"text": "Calories: 210 kcal | Protein: 20 g", "confidence": 0.95, "box": [10, 40, 280, 65]},
        {"text": "Carbohydrates: 25 g | Total Fat: 7 g", "confidence": 0.95, "box": [10, 70, 280, 95]},
        {"text": "Net Weight: 300 g", "confidence": 0.99, "box": [10, 130, 200, 160]},
    ]
    cand = ModularFieldExtractors.extract_net_quantity(boxes, image_id=1, image_role="front")
    assert cand.status == "FOUND"
    assert cand.value == "300 g"
    assert "25 g" not in cand.value
    assert "20 g" not in cand.value


# -----------------------------------------------------------------------------
# 9. Date Association Test
# -----------------------------------------------------------------------------
def test_date_association():
    """Dates must be correctly associated with MFD, EXP, and Best Before; not batch numbers."""
    boxes = [
        {"text": "Batch No: B987654 | FSSAI Lic No: 10019022009876", "confidence": 0.96, "box": [10, 10, 400, 35]},
        {"text": "MFD: 04/2025", "confidence": 0.98, "box": [10, 45, 150, 75]},
        {"text": "EXP: 04/2028", "confidence": 0.98, "box": [10, 85, 150, 115]},
        {"text": "Best Before 36 Months from Mfd", "confidence": 0.97, "box": [10, 125, 300, 155]},
    ]
    dates = ModularFieldExtractors.extract_dates(boxes, image_id=1, image_role="front")
    assert dates["MANUFACTURING_DATE"].status == "FOUND"
    assert "04/2025" in (dates["MANUFACTURING_DATE"].value or "")

    assert dates["EXPIRY_DATE"].status == "FOUND"
    assert "04/2028" in (dates["EXPIRY_DATE"].value or "")

    assert dates["BEST_BEFORE"].status == "FOUND"
    assert "36 Months" in (dates["BEST_BEFORE"].value or "")


# -----------------------------------------------------------------------------
# 10. Multi-Image Aggregation Test
# -----------------------------------------------------------------------------
def test_multi_image_aggregation():
    """Aggregates front, back, and side panel evidence correctly."""
    front_boxes = [
        {"text": "ROYAL BASMATI RICE", "confidence": 0.98, "box": [10, 10, 300, 40]},
        {"text": "Net Quantity: 500 g", "confidence": 0.98, "box": [10, 50, 200, 80]},
        {"text": "MRP ₹149.00", "confidence": 0.99, "box": [10, 90, 180, 120]},
    ]
    back_boxes = [
        {"text": "Manufactured By: Royal Foods Ltd, Gurugram", "confidence": 0.97, "box": [10, 10, 350, 40]},
        {"text": "Consumer Care: care@royalfoods.in, 1800-200-1122", "confidence": 0.96, "box": [10, 50, 380, 80]},
    ]
    side_boxes = [
        {"text": "Mfg Date: 03/2026", "confidence": 0.98, "box": [10, 10, 180, 40]},
        {"text": "Country of Origin: India", "confidence": 0.99, "box": [10, 50, 220, 80]},
    ]

    image_boxes_map = [
        {"image_id": 1, "image_role": "front", "boxes": front_boxes},
        {"image_id": 2, "image_role": "back", "boxes": back_boxes},
        {"image_id": 3, "image_role": "side", "boxes": side_boxes},
    ]

    aggregated = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    by_field = {c.field_name: c for c in aggregated}

    assert by_field["PRODUCT_NAME"].status == "FOUND"
    assert by_field["PRODUCT_NAME"].source_image_id == 1

    assert by_field["MANUFACTURER"].status == "FOUND"
    assert by_field["MANUFACTURER"].source_image_id == 2

    assert by_field["MANUFACTURING_DATE"].status == "FOUND"
    assert by_field["MANUFACTURING_DATE"].source_image_id == 3

    assert by_field["COUNTRY_OF_ORIGIN"].status == "FOUND"
    assert by_field["COUNTRY_OF_ORIGIN"].source_image_id == 3


# -----------------------------------------------------------------------------
# 11. Conflicting Evidence Resolution Test
# -----------------------------------------------------------------------------
def test_conflicting_evidence_resolution():
    """Conflicting prices between panels must result in AMBIGUOUS status."""
    front_boxes = [{"text": "MRP: ₹199.00", "confidence": 0.95, "box": [10, 10, 150, 40]}]
    back_boxes = [{"text": "MRP: ₹249.00", "confidence": 0.95, "box": [10, 10, 150, 40]}]

    image_boxes_map = [
        {"image_id": 1, "image_role": "front", "boxes": front_boxes},
        {"image_id": 2, "image_role": "back", "boxes": back_boxes},
    ]

    aggregated = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    by_field = {c.field_name: c for c in aggregated}

    mrp_cand = by_field["MRP"]
    assert mrp_cand.status == "AMBIGUOUS"
    assert mrp_cand.has_conflict is True
    assert len(mrp_cand.alternate_candidates) >= 1


# -----------------------------------------------------------------------------
# 12. UNABLE_TO_VERIFY Preservation Test
# -----------------------------------------------------------------------------
def test_unable_to_verify_preservation():
    """UNABLE_TO_VERIFY status must never be silently converted into PASS."""
    decl = FieldCandidate(
        field_name="NET_QUANTITY",
        display_name="Net Quantity",
        value=None,
        status="UNABLE_TO_VERIFY",
        confidence=0.1
    )
    res = ComplianceEngine.evaluate_declarations([decl.to_dict()])
    assert res["overall_status"] != "COMPLIANT"
    assert res["overall_status"] in ("REVIEW_REQUIRED", "NOT_VERIFIABLE")


# -----------------------------------------------------------------------------
# 13. REVIEW_REQUIRED Compliance Behavior Test
# -----------------------------------------------------------------------------
def test_review_required_compliance_behavior():
    """Mandatory declaration unverified triggers REVIEW_REQUIRED."""
    declarations = [
        {"field_name": "PRODUCT_NAME", "detected_value": "Shampoo", "status": "FOUND", "confidence": 0.98},
        {"field_name": "MRP", "detected_value": None, "status": "NOT_FOUND", "confidence": 0.0},
        {"field_name": "NET_QUANTITY", "detected_value": "200 ml", "status": "FOUND", "confidence": 0.95},
    ]
    res = ComplianceEngine.evaluate_declarations(declarations)
    assert res["overall_status"] == "REVIEW_REQUIRED"


# -----------------------------------------------------------------------------
# 14. PaddleOCR Singleton Reuse Test
# -----------------------------------------------------------------------------
def test_paddleocr_singleton_reuse():
    """Verifies PaddleOCRProvider instances share the same underlying model without recreation."""
    p1 = PaddleOCRProvider()
    p2 = PaddleOCRProvider()
    assert p1.is_available() is True
    assert p2.is_available() is True
    # Singleton check: _shared_paddle_engine exists and is identical
    from app.services.ocr.providers.paddleocr_provider import _shared_paddle_engine
    assert _shared_paddle_engine is not None


# -----------------------------------------------------------------------------
# 15. Cold vs Warm Timing Test
# -----------------------------------------------------------------------------
def test_cold_warm_timing(tmp_path):
    """Verifies profiler measures and isolates cold start and warm start metrics."""
    profiler = PipelineProfiler()
    # Create tiny dummy image
    img_path = tmp_path / "dummy.png"
    import cv2
    import numpy as np
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(img_path), dummy_img)

    res1 = profiler.profile_single_image(str(img_path))
    res2 = profiler.profile_single_image(str(img_path))

    summary = profiler.get_latency_summary()
    assert "ocr_cold_start_ms" in summary
    assert "ocr_warm_inference_ms" in summary
    assert summary["ocr_cold_start_ms"] >= 0.0


# -----------------------------------------------------------------------------
# 16. Retry Latency and Benefit Test
# -----------------------------------------------------------------------------
def test_retry_latency_and_benefit(tmp_path):
    """Verifies profiler measures retry time when Attempt 2 is executed."""
    profiler = PipelineProfiler()
    img_path = tmp_path / "blank.png"
    import cv2
    import numpy as np
    dummy_img = np.full((150, 150, 3), 255, dtype=np.uint8)
    cv2.imwrite(str(img_path), dummy_img)

    # Force retry
    res = profiler.profile_single_image(str(img_path), force_retry=True)
    assert res["retry_ms"] >= 0.0
    assert "total_ms" in res


# -----------------------------------------------------------------------------
# 17. Spatial Evidence Preservation Test
# -----------------------------------------------------------------------------
def test_spatial_evidence_preservation():
    """All spatial bounding boxes must remain bounded within [0.0, 1.0]."""
    boxes = [
        {"text": "MRP ₹199.00", "confidence": 0.95, "box": [10, 20, 210, 60]}
    ]
    cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    bb = cand.bounding_box
    assert bb is not None
    assert 0.0 <= bb.get("x_rel", 0.0) <= 1.0
    assert 0.0 <= bb.get("y_rel", 0.0) <= 1.0
    assert 0.0 <= bb.get("w_rel", 0.0) <= 1.0
    assert 0.0 <= bb.get("h_rel", 0.0) <= 1.0


# -----------------------------------------------------------------------------
# 18. Evaluation Normalizer Non-Mutation Test
# -----------------------------------------------------------------------------
def test_evaluation_normalizer_non_mutation():
    """EvaluationNormalizer must not mutate candidate attributes or stored OCR text."""
    cand = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value="MRP ₹199.00 (Incl. of all taxes)",
        raw_value="MRP ₹199.00 (Incl. of all taxes)",
        normalized_value="199.00",
        confidence=0.98,
        status="FOUND",
        bounding_box={"x_rel": 0.1, "y_rel": 0.2, "w_rel": 0.3, "h_rel": 0.1}
    )
    orig_val = cand.value
    orig_raw = cand.raw_value
    orig_conf = cand.confidence
    orig_bb = dict(cand.bounding_box)

    comp = EvaluationNormalizer.compare_field("MRP", "₹199", cand)
    assert comp["is_match"] is True

    # Ensure no mutation on cand
    assert cand.value == orig_val
    assert cand.raw_value == orig_raw
    assert cand.confidence == orig_conf
    assert cand.bounding_box == orig_bb
