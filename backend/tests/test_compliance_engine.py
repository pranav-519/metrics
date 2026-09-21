import pytest
from app.services.compliance.rule_registry import RuleRegistry, RegisteredRule
from app.services.compliance.rule_result import EvaluatedRuleResult
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.compliance.rules import init_default_rules
from app.services.compliance.rules.net_quantity import evaluate_net_quantity_qualifier
from app.services.compliance.rules.dates import evaluate_date_consistency
from app.services.compliance.rules.country_of_origin import evaluate_country_of_origin_explicit

def setup_module():
    init_default_rules()

# ============================================================================
# 1. SEPARATION OF SEVERITY AND STATUS TESTS
# ============================================================================

def test_severity_does_not_determine_status():
    """
    Validates that rule severity (CRITICAL, ERROR, WARNING, INFO) does NOT dictate
    evaluation status (PASS, FAIL, WARNING, NOT_VERIFIABLE, NOT_APPLICABLE).
    """
    # Case A: ERROR + PASS
    err_pass = EvaluatedRuleResult(
        rule_id="TEST_ERR_PASS",
        field_name="MRP",
        status="PASS",
        severity="ERROR",
        message="Requirement satisfied."
    )
    assert err_pass.severity == "ERROR"
    assert err_pass.status == "PASS"

    # Case B: ERROR + NOT_VERIFIABLE
    err_nv = EvaluatedRuleResult(
        rule_id="TEST_ERR_NV",
        field_name="MRP",
        status="NOT_VERIFIABLE",
        severity="ERROR",
        message="Declaration missing from packaging."
    )
    assert err_nv.severity == "ERROR"
    assert err_nv.status == "NOT_VERIFIABLE"

    # Case C: ERROR + FAIL
    err_fail = EvaluatedRuleResult(
        rule_id="TEST_ERR_FAIL",
        field_name="NET_QUANTITY",
        status="FAIL",
        severity="ERROR",
        message="Affirmative violation found."
    )
    assert err_fail.severity == "ERROR"
    assert err_fail.status == "FAIL"

    # Case D: CRITICAL + PASS
    crit_pass = EvaluatedRuleResult(
        rule_id="TEST_CRIT_PASS",
        field_name="PRODUCT_NAME",
        status="PASS",
        severity="CRITICAL",
        message="Critical requirement satisfied."
    )
    assert crit_pass.severity == "CRITICAL"
    assert crit_pass.status == "PASS"

    # Case E: WARNING + FAIL
    warn_fail = EvaluatedRuleResult(
        rule_id="TEST_WARN_FAIL",
        field_name="CONSUMER_CARE",
        status="FAIL",
        severity="WARNING",
        message="Secondary check failed."
    )
    assert warn_fail.severity == "WARNING"
    assert warn_fail.status == "FAIL"


# ============================================================================
# 2. STRICT DEFINITION OF FAIL (NOT_FOUND != FAIL, CONFLICT != FAIL)
# ============================================================================

def test_missing_field_is_not_verifiable_not_fail():
    """
    NOT_FOUND must produce NOT_VERIFIABLE, never FAIL.
    Inability to extract a field is NOT automatic proof of legal non-compliance.
    """
    declarations = [
        {
            "field_name": "MRP",
            "detected_value": None,
            "extraction_status": "NOT_FOUND",
            "status": "NOT_FOUND",
            "confidence": 0.0
        }
    ]
    res = ComplianceEngine.evaluate_declarations(declarations)
    mrp_present = next(r for r in res["results"] if r["rule_id"] == "MRP_PRESENT")
    
    assert mrp_present["status"] == "NOT_VERIFIABLE"
    assert mrp_present["status"] != "FAIL"
    assert mrp_present["severity"] == "CRITICAL"  # Severity is CRITICAL, but status is NOT_VERIFIABLE!


def test_ambiguous_field_is_not_verifiable():
    """
    AMBIGUOUS extraction status must produce NOT_VERIFIABLE.
    """
    declarations = [
        {
            "field_name": "MANUFACTURING_DATE",
            "detected_value": "04/2024",
            "extraction_status": "AMBIGUOUS",
            "status": "REVIEW_REQUIRED",
            "confidence": 0.5
        }
    ]
    res = ComplianceEngine.evaluate_declarations(declarations)
    date_rule = next(r for r in res["results"] if r["rule_id"] == "MANUFACTURING_OR_PACKING_DATE_PRESENT")
    assert date_rule["status"] == "NOT_VERIFIABLE"


def test_low_confidence_field_is_not_verifiable():
    """
    LOW_CONFIDENCE text must produce NOT_VERIFIABLE (or WARNING), never FAIL.
    """
    declarations = [
        {
            "field_name": "MRP",
            "detected_value": "₹ 50.00",
            "extraction_status": "LOW_CONFIDENCE",
            "status": "UNABLE_TO_VERIFY",
            "confidence": 0.35,
            "raw_ocr_confidence": 0.35
        }
    ]
    res = ComplianceEngine.evaluate_declarations(declarations)
    mrp_val = next(r for r in res["results"] if r["rule_id"] == "MRP_VALUE_VALID")
    assert mrp_val["status"] in ("NOT_VERIFIABLE", "WARNING")
    assert mrp_val["status"] != "FAIL"


def test_conflict_field_is_not_verifiable_and_preserves_evidence():
    """
    When has_conflict=True, the rule must evaluate to NOT_VERIFIABLE
    without arbitrarily picking one candidate, and must retain alternate candidates in evidence.
    """
    declarations = [
        {
            "field_name": "MRP",
            "detected_value": "₹ 45.00",
            "normalized_value": "45.00",
            "extraction_status": "FOUND",
            "confidence": 0.85,
            "has_conflict": True,
            "evidence": {"source_ocr_ids": [10, 11]},
            "alternate_candidates": [
                {"value": "₹ 55.00", "source_image_role": "back"}
            ]
        }
    ]
    res = ComplianceEngine.evaluate_declarations(declarations)
    conflict_rule = next(r for r in res["results"] if r["rule_id"] == "MRP_CONFLICT_CHECK")
    
    assert conflict_rule["status"] == "NOT_VERIFIABLE"
    assert conflict_rule["status"] != "FAIL"
    assert "evidence" in conflict_rule
    assert conflict_rule["evidence"].get("has_conflict") is True
    assert len(conflict_rule["evidence"].get("alternate_candidates", [])) == 1


# ============================================================================
# 3. STRICT AFFIRMATIVE FAIL CONDITIONS
# ============================================================================

def test_prohibited_qualifier_fails():
    """
    Rule 11: Net quantity qualified by 'when packed' affirmatively violates statutory rules.
    """
    decl = {
        "field_name": "NET_QUANTITY",
        "detected_value": "500 g when packed",
        "raw_value": "Net Wt. 500 g when packed",
        "extraction_status": "FOUND"
    }
    res = evaluate_net_quantity_qualifier(decl, {})
    assert res.status == "FAIL"
    assert "when packed" in res.message
    assert "Rule 11" in res.rule_reference


def test_manufacturing_date_after_expiry_fails():
    """
    Consistent packaging chronology: mfg_date > expiry_date is an affirmative violation -> FAIL.
    """
    decl_map = {
        "MANUFACTURING_DATE": {
            "field_name": "MANUFACTURING_DATE",
            "detected_value": "2025-06-01",
            "extraction_status": "FOUND"
        },
        "EXPIRY_DATE": {
            "field_name": "EXPIRY_DATE",
            "detected_value": "2024-06-01",
            "extraction_status": "FOUND"
        }
    }
    res = evaluate_date_consistency(None, decl_map)
    assert res.status == "FAIL"
    assert "occurs after Expiry date" in res.message


def test_single_date_is_not_verifiable_no_fabrication():
    """
    If only mfg date exists, do NOT invent or assume expiry date; evaluate as NOT_VERIFIABLE.
    """
    decl_map = {
        "MANUFACTURING_DATE": {
            "field_name": "MANUFACTURING_DATE",
            "detected_value": "2024-01-01",
            "extraction_status": "FOUND"
        }
    }
    res = evaluate_date_consistency(None, decl_map)
    assert res.status == "NOT_VERIFIABLE"
    assert res.status != "FAIL"


# ============================================================================
# 4. COUNTRY OF ORIGIN EXPLICIT (NO INFERENCE FROM ADDRESS)
# ============================================================================

def test_country_of_origin_not_inferred_from_address():
    """
    Country of Origin must not be inferred from a manufacturer address in India.
    If not explicitly declared on package, it must evaluate to NOT_VERIFIABLE.
    """
    decl_map = {
        "MANUFACTURER": {
            "field_name": "MANUFACTURER",
            "detected_value": "Britannia Industries Ltd, Bangalore, Karnataka, India",
            "extraction_status": "FOUND"
        },
        "COUNTRY_OF_ORIGIN": {
            "field_name": "COUNTRY_OF_ORIGIN",
            "detected_value": None,
            "extraction_status": "NOT_FOUND"
        }
    }
    target = decl_map["COUNTRY_OF_ORIGIN"]
    res = evaluate_country_of_origin_explicit(target, decl_map)
    assert res.status == "NOT_VERIFIABLE"
    assert res.status != "PASS"
    assert "cannot be inferred from manufacturer address" in res.message


# ============================================================================
# 5. OVERALL COMPLIANCE AGGREGATION SEMANTICS
# ============================================================================

def test_overall_status_aggregation_rules():
    """
    1. Any definitive FAIL -> NON_COMPLIANT
    2. No FAIL + unresolved NOT_VERIFIABLE / WARNING -> REVIEW_REQUIRED
    3. All applicable checks PASS -> COMPLIANT
    """
    # Case 1: Has one FAIL
    declarations_fail = [
        {
            "field_name": "PRODUCT_NAME",
            "detected_value": "Marie Gold Biscuits",
            "extraction_status": "FOUND"
        },
        {
            "field_name": "NET_QUANTITY",
            "detected_value": "100 g when packed",
            "raw_value": "100 g when packed",
            "extraction_status": "FOUND"
        }
    ]
    res_fail = ComplianceEngine.evaluate_declarations(declarations_fail)
    assert res_fail["overall_status"] == "NON_COMPLIANT"

    # Case 2: No FAIL, but missing fields -> REVIEW_REQUIRED
    declarations_unresolved = [
        {
            "field_name": "PRODUCT_NAME",
            "detected_value": "Marie Gold Biscuits",
            "extraction_status": "FOUND"
        },
        {
            "field_name": "MRP",
            "detected_value": None,
            "extraction_status": "NOT_FOUND"
        }
    ]
    res_unresolved = ComplianceEngine.evaluate_declarations(declarations_unresolved)
    assert res_unresolved["overall_status"] == "REVIEW_REQUIRED"

    # Case 3: Fully compliant declarations
    declarations_pass = [
        {"field_name": "PRODUCT_NAME", "detected_value": "Marie Gold", "extraction_status": "FOUND"},
        {"field_name": "MRP", "detected_value": "₹ 20.00", "normalized_value": "20.00", "currency": "INR", "extraction_status": "FOUND"},
        {"field_name": "NET_QUANTITY", "detected_value": "100 g", "normalized_value": "100", "unit": "g", "extraction_status": "FOUND"},
        {"field_name": "MANUFACTURER", "detected_value": "Britannia Industries Ltd, Bangalore", "extraction_status": "FOUND"},
        {"field_name": "PACKER", "detected_value": "Britannia Packing Unit", "extraction_status": "FOUND"},
        {"field_name": "IMPORTER", "detected_value": "Not Applicable", "extraction_status": "NOT_APPLICABLE"},
        {"field_name": "MANUFACTURING_DATE", "detected_value": "2024-01-01", "extraction_status": "FOUND"},
        {"field_name": "EXPIRY_DATE", "detected_value": "2024-06-01", "extraction_status": "FOUND"},
        {"field_name": "CONSUMER_CARE", "detected_value": "care@britannia.com, 1800-425-4444", "extraction_status": "FOUND"},
        {"field_name": "COUNTRY_OF_ORIGIN", "detected_value": "India", "extraction_status": "FOUND"},
    ]
    res_pass = ComplianceEngine.evaluate_declarations(declarations_pass)
    # Check that failed count is 0
    assert res_pass["summary"]["failed"] == 0
    assert res_pass["overall_status"] == "COMPLIANT"


# ============================================================================
# 6. EVIDENCE TRACEABILITY
# ============================================================================

def test_evidence_traceability_preserved():
    """
    Rule results must reference source image, OCR records, and bounding boxes.
    """
    declarations = [
        {
            "field_name": "MRP",
            "detected_value": "₹ 99.00",
            "normalized_value": "99.00",
            "currency": "INR",
            "extraction_status": "FOUND",
            "source_image_id": 42,
            "source_ocr_ids": [101, 102],
            "bounding_box": {"x": 10, "y": 20, "w": 80, "h": 25},
            "evidence": {
                "source_image_id": 42,
                "source_ocr_ids": [101, 102],
                "bounding_boxes": [{"x": 10, "y": 20, "w": 80, "h": 25}]
            }
        }
    ]
    res = ComplianceEngine.evaluate_declarations(declarations)
    mrp_res = next(r for r in res["results"] if r["rule_id"] == "MRP_PRESENT")
    
    assert mrp_res["evidence"] is not None
    assert mrp_res["evidence"]["source_image_id"] == 42
    assert mrp_res["evidence"]["source_ocr_ids"] == [101, 102]


# ============================================================================
# 7. LEGAL RULE PROVENANCE
# ============================================================================

def test_legal_rule_provenance_citations():
    """
    Every registered rule must have an approved statutory reference (e.g. Rule 6(1)(e), Rule 11).
    No legal citation may be invented.
    """
    rules = RuleRegistry.get_all_rules()
    assert len(rules) >= 15
    for r in rules:
        assert r.rule_source is not None
        assert len(r.rule_source.strip()) > 0
        assert "Legal Metrology" in r.rule_source or "Rule" in r.rule_source or "Advisory" in r.rule_source or "APPROVED" in r.rule_source


# ============================================================================
# 8. API ENDPOINT & PERSISTENCE TESTS
# ============================================================================

def test_evaluate_api_endpoint():
    """
    Tests POST /api/scans/{scan_id}/evaluate:
    Ensures that evaluations are computed, returned, and persisted with both
    ComplianceEvaluation and ComplianceRuleResult records.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database.session import SessionLocal
    from app.models.models import Scan, ScanImage, ExtractedDeclaration, ProductCategory, ComplianceEvaluation, ComplianceRuleResult

    client = TestClient(app)
    with SessionLocal() as db:
        category = db.query(ProductCategory).first()
        assert category is not None

        # Create scan
        scan = Scan(
            product_name="Test Product for Compliance Evaluation",
            category_id=category.id,
            analysis_step="EXTRACTION"
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        # Add mock extracted declarations
        d1 = ExtractedDeclaration(
            scan_id=scan.id,
            field_name="MRP",
            display_name="Maximum Retail Price (MRP)",
            detected_value="₹ 149.00",
            normalized_value="149.00",
            currency="INR",
            extraction_status="FOUND",
            confidence=0.92,
            source_ocr_ids=[101],
            evidence={"source_ocr_ids": [101]}
        )
        d2 = ExtractedDeclaration(
            scan_id=scan.id,
            field_name="NET_QUANTITY",
            display_name="Net Quantity",
            detected_value="500 g",
            normalized_value="500",
            unit="g",
            extraction_status="FOUND",
            confidence=0.94,
            source_ocr_ids=[102],
            evidence={"source_ocr_ids": [102]}
        )
        db.add_all([d1, d2])
        db.commit()

        # Call evaluate API
        resp = client.post(f"/api/scans/{scan.id}/evaluate")
        assert resp.status_code == 200
        data = resp.json()

        assert data["scan_id"] == scan.id
        assert "overall_status" in data
        assert "summary" in data
        assert len(data["results"]) >= 15

        # Verify DB persistence
        db_eval = db.query(ComplianceEvaluation).filter(ComplianceEvaluation.scan_id == scan.id).first()
        assert db_eval is not None
        assert db_eval.total_rules >= 15

        db_results = db.query(ComplianceRuleResult).filter(ComplianceRuleResult.evaluation_id == db_eval.id).all()
        assert len(db_results) >= 15

        # Check get scan details includes latest_evaluation
        detail_resp = client.get(f"/api/scans/{scan.id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data.get("latest_evaluation") is not None
        assert detail_data["latest_evaluation"]["scan_id"] == scan.id


def test_evaluate_api_errors():
    """
    Tests error handling for /api/scans/{scan_id}/evaluate:
    - Non-existent scan returns 404
    - Scan with no declarations returns 400
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database.session import SessionLocal
    from app.models.models import Scan, ProductCategory

    client = TestClient(app)
    # 404 test
    resp = client.post("/api/scans/999999/evaluate")
    assert resp.status_code == 404

    # 400 test (scan without declarations)
    with SessionLocal() as db:
        category = db.query(ProductCategory).first()
        empty_scan = Scan(
            product_name="Empty Scan",
            category_id=category.id,
            analysis_step="UPLOADING"
        )
        db.add(empty_scan)
        db.commit()
        db.refresh(empty_scan)

        resp = client.post(f"/api/scans/{empty_scan.id}/evaluate")
        assert resp.status_code == 400
        assert "no extracted declarations" in resp.json()["detail"]

