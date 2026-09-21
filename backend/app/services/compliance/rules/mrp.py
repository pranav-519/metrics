from typing import Dict, Any, Optional
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_mrp_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MRP_PRESENT"
    field_name = "MRP"
    ref = "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
    severity = "CRITICAL"

    if not decl or decl.get("extraction_status") == "NOT_FOUND" or not decl.get("detected_value"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Maximum Retail Price (MRP) declaration was not detected in the provided packaging photographs.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref,
            suggested_action="Ensure packaging photographs clearly capture the retail price panel."
        )

    if decl.get("has_conflict"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Conflicting retail prices were detected across uploaded images. Verification requires manual inspection.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.0),
            evidence=decl.get("evidence", {}),
            rule_reference=ref,
            suggested_action="Re-examine packaging to resolve conflicting price declarations."
        )

    if decl.get("extraction_status") == "LOW_CONFIDENCE":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="WARNING",
            severity=severity,
            message=f"MRP declaration was detected with low confidence ({decl.get('confidence', 0.0)*100:.0f}%). Visual confirmation recommended.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.0),
            evidence=decl.get("evidence", {}),
            rule_reference=ref,
            suggested_action="Capture a clearer, glare-free photograph of the price panel."
        )

    if decl.get("extraction_status") == "AMBIGUOUS":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="MRP declaration contains ambiguity. Unable to verify statutory compliance definitively.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.0),
            evidence=decl.get("evidence", {}),
            rule_reference=ref,
            suggested_action="Inspect the physical container to resolve ambiguity."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message="Maximum Retail Price (MRP) declaration is clearly present on the packaging.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref,
        suggested_action="Verified compliant under Rule 6(1)(e)."
    )


def evaluate_mrp_value_valid(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MRP_VALUE_VALID"
    field_name = "MRP"
    ref = "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") in ("NOT_FOUND", "AMBIGUOUS", "LOW_CONFIDENCE") or decl.get("has_conflict"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Unable to verify numeric price value because declaration is absent, low-confidence, conflicting, or unreadable.",
            field_value=decl.get("detected_value") if decl else None,
            confidence=decl.get("confidence", 0.0) if decl else 0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref
        )

    norm_val = decl.get("normalized_value")
    try:
        amt = float(norm_val) if norm_val else 0.0
        if amt > 0:
            return EvaluatedRuleResult(
                rule_id=rule_id,
                field_name=field_name,
                status="PASS",
                severity=severity,
                message=f"Valid statutory price value declared: ₹{amt:.2f}.",
                field_value=f"₹{amt:.2f}",
                confidence=decl.get("confidence", 0.95),
                evidence=decl.get("evidence", {}),
                rule_reference=ref
            )
        else:
            return EvaluatedRuleResult(
                rule_id=rule_id,
                field_name=field_name,
                status="FAIL",
                severity=severity,
                message="Retail price amount is zero or negative, which is not legally permitted.",
                field_value=norm_val,
                confidence=decl.get("confidence", 0.90),
                evidence=decl.get("evidence", {}),
                rule_reference=ref,
                suggested_action="Verify physical packaging price declaration."
            )
    except (ValueError, TypeError):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Price could not be parsed as a valid numeric amount.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.5),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )


def evaluate_mrp_currency_valid(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MRP_CURRENCY_VALID"
    field_name = "MRP"
    ref = "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") in ("NOT_FOUND", "AMBIGUOUS") or decl.get("has_conflict"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Currency cannot be verified because MRP declaration is not available or is conflicting.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref
        )

    currency = decl.get("currency") or ("INR" if "₹" in (decl.get("detected_value") or "") or "rs" in (decl.get("raw_value") or "").lower() else None)
    if currency in ("INR", "₹"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message="MRP is properly denominated in Indian Rupees (INR / ₹).",
            field_value=currency,
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )
    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="WARNING",
        severity=severity,
        message="Currency indicator could not be definitively verified as Indian Rupee (INR).",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.6),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_mrp_conflict_check(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MRP_CONFLICT_CHECK"
    field_name = "MRP"
    ref = "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
    severity = "CRITICAL"

    if not decl or decl.get("extraction_status") == "NOT_FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_APPLICABLE",
            severity="INFO",
            message="Conflict check not applicable as no MRP was detected.",
            field_value=None,
            confidence=1.0,
            evidence={},
            rule_reference=ref
        )

    if decl.get("has_conflict"):
        ev = dict(decl.get("evidence") or {})
        ev["has_conflict"] = True
        if decl.get("alternate_candidates"):
            ev["alternate_candidates"] = decl.get("alternate_candidates")
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Conflicting retail prices detected across packaging panels. Both candidates preserved in evidence.",
            field_value=decl.get("detected_value"),
            confidence=0.0,
            evidence=ev,
            rule_reference=ref,
            suggested_action="Review alternate candidates in evidence to check if dual pricing or over-stamping exists."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message="No conflicting retail price declarations detected across images.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def register_mrp_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="MRP_PRESENT",
        field_name="MRP",
        description="Statutory declaration of Maximum Retail Price (MRP)",
        severity="CRITICAL",
        rule_source="Rule 6(1)(e), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mrp_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="MRP_VALUE_VALID",
        field_name="MRP",
        description="Validation that declared price is a positive numerical amount",
        severity="ERROR",
        rule_source="Rule 6(1)(e), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mrp_value_valid
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="MRP_CURRENCY_VALID",
        field_name="MRP",
        description="Validation of Indian Rupee (INR / ₹) currency symbol",
        severity="ERROR",
        rule_source="Rule 6(1)(e), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mrp_currency_valid
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="MRP_CONFLICT_CHECK",
        field_name="MRP",
        description="Cross-image consistency check for retail price declarations",
        severity="CRITICAL",
        rule_source="Rule 6(1)(e), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mrp_conflict_check
    ))
