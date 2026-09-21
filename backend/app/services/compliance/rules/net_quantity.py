from typing import Dict, Any, Optional
import re
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_net_quantity_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "NET_QUANTITY_PRESENT"
    field_name = "NET_QUANTITY"
    ref = "Rule 6(1)(d), Legal Metrology (PC) Rules 2011"
    severity = "CRITICAL"

    if not decl or decl.get("extraction_status") == "NOT_FOUND" or not decl.get("detected_value"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Net quantity declaration was not detected on the packaging.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref,
            suggested_action="Verify packaging panel for statutory net weight or volume statement."
        )

    if decl.get("extraction_status") == "LOW_CONFIDENCE":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="WARNING",
            severity=severity,
            message=f"Net quantity was detected with low confidence ({decl.get('confidence', 0.0)*100:.0f}%). Visual inspection advised.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.0),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )

    if decl.get("extraction_status") == "AMBIGUOUS":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Net quantity declaration contains ambiguity.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.0),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message="Net quantity declaration is clearly present on packaging.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_net_quantity_numeric(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "NET_QUANTITY_NUMERIC"
    field_name = "NET_QUANTITY"
    ref = "Rule 11, Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") in ("NOT_FOUND", "AMBIGUOUS"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Numeric net quantity cannot be verified due to missing or ambiguous declaration.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref
        )

    val = decl.get("normalized_value") or decl.get("detected_value") or ""
    match = re.search(r'(\d+(?:\.\d+)?)', val)
    if match:
        try:
            num = float(match.group(1))
            if num > 0:
                return EvaluatedRuleResult(
                    rule_id=rule_id,
                    field_name=field_name,
                    status="PASS",
                    severity=severity,
                    message=f"Valid statutory positive quantity magnitude: {num}.",
                    field_value=str(num),
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
                    message="Net quantity amount is zero or negative.",
                    field_value=str(num),
                    confidence=decl.get("confidence", 0.90),
                    evidence=decl.get("evidence", {}),
                    rule_reference=ref
                )
        except ValueError:
            pass

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="NOT_VERIFIABLE",
        severity=severity,
        message="Could not parse numerical value for net quantity.",
        field_value=val,
        confidence=0.5,
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_net_quantity_unit_recognized(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "NET_QUANTITY_UNIT_RECOGNIZED"
    field_name = "NET_QUANTITY"
    ref = "Rule 11, Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") in ("NOT_FOUND", "AMBIGUOUS"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Unit cannot be verified because quantity declaration was not found.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref
        )

    recognized_units = {"g", "kg", "mg", "ml", "l", "cm", "m", "mm", "units"}
    unit = (decl.get("unit") or "").strip().lower()
    if not unit:
        # Fallback search from detected_value
        val = decl.get("detected_value") or ""
        match = re.search(r'\b(kg|g|mg|ml|l|cm|m|mm|units?)\b', val, re.IGNORECASE)
        unit = match.group(1).lower() if match else ""

    if unit in recognized_units:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message=f"Statutory standardized metric unit declared: '{unit}'.",
            field_value=unit,
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="WARNING",
        severity=severity,
        message=f"Declared quantity unit '{unit}' could not be definitively validated against Rule 11 metric standards.",
        field_value=unit or "UNKNOWN",
        confidence=decl.get("confidence", 0.6),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_net_quantity_qualifier(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "NET_QUANTITY_QUALIFIER_CHECK"
    field_name = "NET_QUANTITY"
    ref = "Rule 11, Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") == "NOT_FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_APPLICABLE",
            severity="INFO",
            message="Qualifier check not applicable as net quantity is not present.",
            field_value=None,
            confidence=1.0,
            evidence={},
            rule_reference=ref
        )

    raw_text = (decl.get("raw_value") or decl.get("detected_value") or "").lower()
    if "when packed" in raw_text:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="FAIL",
            severity=severity,
            message="Prohibited qualification: Rule 11 strictly prohibits qualifying net quantity with phrases such as 'when packed'.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref,
            suggested_action="Remove non-statutory 'when packed' qualification from the package label."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message="Net quantity is declared without prohibited qualifiers.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def register_net_quantity_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="NET_QUANTITY_PRESENT",
        field_name="NET_QUANTITY",
        description="Declaration of net quantity in terms of weight, measure, or number",
        severity="CRITICAL",
        rule_source="Rule 6(1)(d), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_net_quantity_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="NET_QUANTITY_NUMERIC",
        field_name="NET_QUANTITY",
        description="Validation of positive numeric quantity magnitude",
        severity="ERROR",
        rule_source="Rule 11, Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_net_quantity_numeric
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="NET_QUANTITY_UNIT_RECOGNIZED",
        field_name="NET_QUANTITY",
        description="Validation of recognized metric unit (g, kg, ml, L, etc.)",
        severity="ERROR",
        rule_source="Rule 11, Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_net_quantity_unit_recognized
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="NET_QUANTITY_QUALIFIER_CHECK",
        field_name="NET_QUANTITY",
        description="Prohibition of non-statutory qualifiers like 'when packed'",
        severity="ERROR",
        rule_source="Rule 11, Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_net_quantity_qualifier
    ))
