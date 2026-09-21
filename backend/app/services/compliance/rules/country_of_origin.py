from typing import Dict, Any, Optional
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_country_of_origin_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "COUNTRY_OF_ORIGIN_PRESENT"
    field_name = "COUNTRY_OF_ORIGIN"
    ref = "Rule 6(10), Legal Metrology (PC) Amendment Rules"
    severity = "CRITICAL"

    if not decl or decl.get("extraction_status") == "NOT_FOUND" or not decl.get("detected_value"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Country of Origin declaration was not detected in packaging photographs.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref,
            suggested_action="Locate explicit 'Country of Origin' or 'Made in' declaration on physical packaging."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message=f"Country of Origin declared: {decl.get('detected_value')}.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_country_of_origin_explicit(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "COUNTRY_OF_ORIGIN_EXPLICIT"
    field_name = "COUNTRY_OF_ORIGIN"
    ref = "Rule 6(10), Legal Metrology (PC) Amendment Rules"
    severity = "CRITICAL"

    # Explicit origin declaration check
    if not decl or decl.get("extraction_status") != "FOUND" or not decl.get("detected_value"):
        # Even if manufacturer address has 'India', do NOT infer origin!
        mfg_decl = all_decls.get("MANUFACTURER") or all_decls.get("manufacturer")
        mfg_val = (mfg_decl.get("detected_value") or "").lower() if mfg_decl else ""
        has_addr_india = "india" in mfg_val

        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Statutory rule requires explicit country declaration ('Country of Origin' / 'Made in'). Country cannot be inferred from manufacturer address.",
            field_value=f"Manufacturer Address Context: {mfg_val[:30]}..." if has_addr_india else None,
            confidence=0.0,
            evidence={},
            rule_reference=ref,
            suggested_action="Ensure packaging includes an explicit 'Country of Origin: [Country]' declaration."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message=f"Explicit Country of Origin declaration verified ('{decl.get('detected_value')}').",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def register_country_of_origin_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="COUNTRY_OF_ORIGIN_PRESENT",
        field_name="COUNTRY_OF_ORIGIN",
        description="Mandatory declaration of country of origin or manufacture",
        severity="CRITICAL",
        rule_source="Rule 6(10), Legal Metrology (PC) Amendment Rules",
        evaluator=evaluate_country_of_origin_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="COUNTRY_OF_ORIGIN_EXPLICIT",
        field_name="COUNTRY_OF_ORIGIN",
        description="Requirement that origin be explicitly stated and not inferred from address",
        severity="CRITICAL",
        rule_source="Rule 6(10), Legal Metrology (PC) Amendment Rules",
        evaluator=evaluate_country_of_origin_explicit
    ))
