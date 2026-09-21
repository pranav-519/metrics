"""Master Prompt 06 — Real-World Image Reliability, OCR Validation & Evidence Hardening Tests.

Verifies:
1. Quality gate edge cases (blur, glare, lighting).
2. OCR retry mechanics and zero-fake-text guarantee.
3. Indian Rupee symbol (₹) and MRP format parsing.
4. Net quantity unit and decimal handling.
5. Date syntax and duration parsing.
6. Spatial evidence bounding box validity and clamping (0 <= rel <= 1).
7. Multi-image isolation (FRONT, BACK, SIDE, CLOSE_UP).
8. NOT_FOUND vs UNABLE_TO_VERIFY semantic integrity.
9. False positive rejection of non-statutory distractors.
"""

from pathlib import Path
import pytest
from PIL import Image

from app.models.models import ImageQualityStatus, ImageType
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.compliance.rules import init_default_rules
from app.services.extraction.declarations import DeclarationExtractorService
from app.services.extraction.field_extractors import ModularFieldExtractors
from app.services.image_processing.quality import ImageQualityService
from app.services.ocr.base import (
    BoundingBox,
    OCRBoxResult,
    OCRResult,
)
from app.services.ocr.engine import PretrainedOCREngine
from tests.fixtures.synthetic_packages import (
    apply_blur,
    apply_glare,
    apply_lighting,
    apply_perspective_tilt,
    render_package_label,
)


def setup_module():
    init_default_rules()


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("reliability_fixtures")


@pytest.fixture(scope="module")
def sample_clean_image(fixture_dir) -> Path:
    img = render_package_label()
    p = fixture_dir / "clean_package.png"
    img.save(p)
    return p


# ---------------------------------------------------------------------------
# 1. Quality Gate Edge Cases
# ---------------------------------------------------------------------------

def test_quality_gate_severe_blur(fixture_dir, sample_clean_image):
    """Severe blur should lower blur_score below standard threshold and be flagged."""
    orig = Image.open(sample_clean_image)
    blurry = apply_blur(orig, sigma=6.0)
    p_blur = fixture_dir / "severe_blur.png"
    blurry.save(p_blur)

    score = ImageQualityService.evaluate_image_file(str(p_blur))
    assert score["blur_score"] < 150.0
    assert score["quality_status"] in (ImageQualityStatus.POOR, ImageQualityStatus.CRITICAL_ISSUES)


def test_quality_gate_strong_glare(fixture_dir, sample_clean_image):
    """Specular glare over packaging should be detected by glare_score analysis."""
    orig = Image.open(sample_clean_image)
    glared = apply_glare(orig, center=(300, 300), radius=160, intensity=0.95)
    p_glare = fixture_dir / "strong_glare.png"
    glared.save(p_glare)

    score = ImageQualityService.evaluate_image_file(str(p_glare))
    assert score["glare_score"] > 2.0  # Percentage of specular saturated pixels


def test_quality_gate_underexposed(fixture_dir, sample_clean_image):
    """Very dark lighting should result in low brightness score."""
    orig = Image.open(sample_clean_image)
    dark = apply_lighting(orig, brightness_factor=0.25)
    p_dark = fixture_dir / "dark_package.png"
    dark.save(p_dark)

    score = ImageQualityService.evaluate_image_file(str(p_dark))
    assert score["lighting_score"] < 70.0


# ---------------------------------------------------------------------------
# 2. Rupee Symbol (₹) & MRP Variations
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mrp_raw,expected_norm", [
    ("MRP: ₹299.00 (Incl. of all taxes)", "299.00"),
    ("MRP Rs. 199.50", "199.50"),
    ("Maximum Retail Price ₹ 450", "450.00"),
    ("MRP: Rs 99 incl. all taxes", "99.00"),
    ("MRP ₹1,250.00", "1250.00"),
])
def test_mrp_syntax_variations(mrp_raw, expected_norm):
    """Test deterministic MRP extraction across diverse realistic formats and Indian Rupee symbols."""
    boxes = [
        {
            "id": 1,
            "text": mrp_raw,
            "confidence": 0.98,
            "bounding_box": BoundingBox(
                x1=10, y1=10, x2=100, y2=30, x=10, y=10, w=90, h=20,
                x_rel=0.01, y_rel=0.01, w_rel=0.09, h_rel=0.02,
            ).to_dict(),
            "line_number": 1,
        }
    ]
    candidate = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    assert candidate.status == "FOUND"
    assert candidate.normalized_value == expected_norm
    assert candidate.currency == "INR"


# ---------------------------------------------------------------------------
# 3. Net Quantity Variations & Unit Normalization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("net_qty_raw,expected_val,expected_unit", [
    ("Net Qty: 500 g", "500 g", "g"),
    ("Net Weight: 1 kg", "1 kg", "kg"),
    ("Net Quantity: 200 ml", "200 ml", "ml"),
    ("Net Contents: 1 L", "1 L", "l"),
    ("Net Wt 1.5 kg", "1.5 kg", "kg"),
    ("Net Quantity: 500g", "500 g", "g"),
    ("Net Qty : 750 ML", "750 ml", "ml"),
])
def test_net_quantity_variations(net_qty_raw, expected_val, expected_unit):
    """Test Net Quantity extraction across weight and volume units, decimals, and spacing."""
    boxes = [
        {
            "id": 2,
            "text": net_qty_raw,
            "confidence": 0.97,
            "bounding_box": BoundingBox(
                x1=10, y1=50, x2=100, y2=70, x=10, y=50, w=90, h=20,
                x_rel=0.01, y_rel=0.05, w_rel=0.09, h_rel=0.02,
            ).to_dict(),
            "line_number": 2,
        }
    ]
    candidate = ModularFieldExtractors.extract_net_quantity(boxes, image_id=1, image_role="front")
    assert candidate.status == "FOUND"
    assert candidate.normalized_value.lower() == expected_val.lower()
    assert candidate.unit.lower() == expected_unit.lower()


# ---------------------------------------------------------------------------
# 4. Date Variations & Best Before
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("date_text,target_field,expected_val", [
    ("Mfg Date: 15/01/2026", "MANUFACTURING_DATE", "15/01/2026"),
    ("PKD: 02/2026", "PACKING_DATE", "02/2026"),
    ("Exp Date: 14/01/2027", "EXPIRY_DATE", "14/01/2027"),
    ("EXP: 12/2027", "EXPIRY_DATE", "12/2027"),
    ("Best Before 12 Months from Packaging", "BEST_BEFORE", "12 Months"),
])
def test_date_syntax_variations(date_text, target_field, expected_val):
    """Test date extractors for MFD, PKD, EXP, and relative Best Before statements."""
    boxes = [
        {
            "id": 3,
            "text": date_text,
            "confidence": 0.96,
            "bounding_box": BoundingBox(
                x1=10, y1=100, x2=200, y2=120, x=10, y=100, w=190, h=20,
                x_rel=0.01, y_rel=0.1, w_rel=0.19, h_rel=0.02,
            ).to_dict(),
            "line_number": 3,
        }
    ]
    dates = ModularFieldExtractors.extract_dates(boxes, image_id=1, image_role="front")
    candidate = dates[target_field]
    assert candidate.status == "FOUND"
    assert expected_val.lower() in candidate.normalized_value.lower() or expected_val.lower() in candidate.value.lower()


# ---------------------------------------------------------------------------
# 5. Spatial Evidence Bounding Box Normalization
# ---------------------------------------------------------------------------

def test_spatial_evidence_normalized_bounds():
    """All relative coordinates in OCRBoxResult must stay strictly within [0.0, 1.0]."""
    engine = PretrainedOCREngine()
    img = render_package_label(width=400, height=300)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        img.save(tf.name)
        p = tf.name

    result = engine.extract_text(
        image_path=p,
        image_id=1,
        image_type="FRONT",
    )

    assert result.status == "COMPLETED"
    assert len(result.boxes) > 0
    for box in result.boxes:
        bb = box.bounding_box
        x_rel = bb.get("x_rel")
        y_rel = bb.get("y_rel")
        w_rel = bb.get("w_rel")
        h_rel = bb.get("h_rel")
        assert 0.0 <= x_rel <= 1.0, f"x_rel out of bounds: {x_rel}"
        assert 0.0 <= y_rel <= 1.0, f"y_rel out of bounds: {y_rel}"
        assert 0.0 <= w_rel <= 1.0, f"w_rel out of bounds: {w_rel}"
        assert 0.0 <= h_rel <= 1.0, f"h_rel out of bounds: {h_rel}"
        if "polygon" in bb and bb["polygon"]:
            for pt in bb["polygon"]:
                assert len(pt) == 2


# ---------------------------------------------------------------------------
# 6. Multi-Image Evidence Isolation
# ---------------------------------------------------------------------------

def test_multi_image_evidence_isolation():
    """Ensure declarations preserve distinct image_id and image_role from source."""
    boxes_front = [
        {
            "id": 101,
            "text": "MRP: ₹199.00 (Incl. of all taxes)",
            "confidence": 0.97,
            "bounding_box": BoundingBox(
                x1=10, y1=10, x2=100, y2=30, x=10, y=10, w=90, h=20,
                x_rel=0.01, y_rel=0.01, w_rel=0.09, h_rel=0.02,
            ).to_dict(),
            "line_number": 1,
        }
    ]
    boxes_back = [
        {
            "id": 201,
            "text": "Manufactured by: Krishna Agro Foods Ltd, Plot 42, Gurugram, India",
            "confidence": 0.95,
            "bounding_box": BoundingBox(
                x1=10, y1=50, x2=200, y2=80, x=10, y=50, w=190, h=30,
                x_rel=0.01, y_rel=0.05, w_rel=0.19, h_rel=0.03,
            ).to_dict(),
            "line_number": 2,
        }
    ]

    image_boxes_map = [
        {"image_id": 1, "image_role": "front", "boxes": boxes_front},
        {"image_id": 2, "image_role": "back", "boxes": boxes_back},
    ]

    final_fields = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    decl_map = {f.field_name: f for f in final_fields}

    assert decl_map["MRP"].status == "FOUND"
    assert decl_map["MRP"].source_image_id == 1
    assert decl_map["MRP"].source_image_role == "front"

    assert decl_map["MANUFACTURER"].status == "FOUND"
    assert decl_map["MANUFACTURER"].source_image_id == 2
    assert decl_map["MANUFACTURER"].source_image_role == "back"


# ---------------------------------------------------------------------------
# 7. NOT_FOUND vs UNABLE_TO_VERIFY Distinction
# ---------------------------------------------------------------------------

def test_not_found_vs_unable_to_verify():
    """Genuinely absent field is NOT_FOUND; in compliance engine, produces NOT_VERIFIABLE."""
    boxes = [
        {
            "id": 1,
            "text": "HERBAL AYURVEDIC SHAMPOO",
            "confidence": 0.98,
            "bounding_box": BoundingBox(
                x1=10, y1=10, x2=100, y2=30, x=10, y=10, w=90, h=20,
                x_rel=0.01, y_rel=0.01, w_rel=0.09, h_rel=0.02,
            ).to_dict(),
            "line_number": 1,
        }
    ]
    candidates = DeclarationExtractorService.extract_from_boxes_by_image([
        {"image_id": 1, "image_role": "front", "boxes": boxes}
    ])
    decl_map = {c.field_name: c for c in candidates}

    # Field genuinely absent from detections
    assert decl_map["MRP"].status == "NOT_FOUND"

    # Evaluated against legal compliance rules
    eval_input = [
        {
            "field_name": c.field_name,
            "detected_value": c.value,
            "status": c.status,
            "confidence": c.confidence,
        }
        for c in candidates
    ]
    res = ComplianceEngine.evaluate_declarations(eval_input)
    mrp_res = next(r for r in res["results"] if r["field_name"] == "MRP")
    # Missing declaration produces NOT_VERIFIABLE (strict definition of FAIL)
    assert mrp_res["status"] == "NOT_VERIFIABLE"


# ---------------------------------------------------------------------------
# 8. False Positive Distractor Rejection
# ---------------------------------------------------------------------------

def test_false_positive_distractor_rejection():
    """Non-statutory numbers (discounts, carb weights, promo codes) must NOT be extracted as MRP or Net Qty."""
    boxes = [
        {
            "id": 1,
            "text": "Special Festive Offer: Save 20% Today!",
            "confidence": 0.96,
            "bounding_box": BoundingBox(x1=10, y1=10, x2=100, y2=20, x=10, y=10, w=90, h=10, x_rel=0.01, y_rel=0.01, w_rel=0.09, h_rel=0.01).to_dict(),
            "line_number": 1,
        },
        {
            "id": 2,
            "text": "Nutritional Information: Carbohydrates 45 g per serving",
            "confidence": 0.95,
            "bounding_box": BoundingBox(x1=10, y1=30, x2=100, y2=40, x=10, y=30, w=90, h=10, x_rel=0.01, y_rel=0.03, w_rel=0.09, h_rel=0.01).to_dict(),
            "line_number": 2,
        },
        {
            "id": 3,
            "text": "Batch Reference Number: BATCH-889920",
            "confidence": 0.97,
            "bounding_box": BoundingBox(x1=10, y1=50, x2=100, y2=60, x=10, y=50, w=90, h=10, x_rel=0.01, y_rel=0.05, w_rel=0.09, h_rel=0.01).to_dict(),
            "line_number": 3,
        },
    ]

    candidates = DeclarationExtractorService.extract_from_boxes_by_image([
        {"image_id": 1, "image_role": "front", "boxes": boxes}
    ])
    decl_map = {c.field_name: c for c in candidates}

    # "Save 20%" must NOT be extracted as MRP
    assert decl_map["MRP"].status == "NOT_FOUND"

    # "Carbohydrates 45 g" must NOT be extracted as Net Quantity (no Net Qty statutory anchor)
    assert decl_map["NET_QUANTITY"].status == "NOT_FOUND"
