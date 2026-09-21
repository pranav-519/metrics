from typing import Dict, Any, Optional
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_importer_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "IMPORTER_PRESENT"
    field_name = "IMPORTER"
    ref = "Rule 6(1)(b), Legal Metrology (PC) Rules 2011"
    severity = "WARNING"

    if decl and decl.get("extraction_status") == "FOUND" and decl.get("detected_value"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message="Importer declaration clearly present.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )

    # If country of origin is domestic (India), importer is not applicable
    origin_decl = all_decls.get("COUNTRY_OF_ORIGIN") or all_decls.get("country_of_origin")
    origin_text = (origin_decl.get("detected_value") or "").lower() if origin_decl else ""
    if "india" in origin_text:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_APPLICABLE",
            severity="INFO",
            message="Importer declaration not applicable for domestic (India) manufactured commodities.",
            field_value=None,
            confidence=1.0,
            evidence={},
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="NOT_APPLICABLE",
        severity="INFO",
        message="Importer declaration is applicable specifically to imported goods.",
        field_value=None,
        confidence=1.0,
        evidence={},
        rule_reference=ref
    )


def evaluate_importer_address_evidence(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "IMPORTER_ADDRESS_EVIDENCE"
    field_name = "IMPORTER"
    ref = "Rule 6(1)(b), Legal Metrology (PC) Rules 2011"
    severity = "WARNING"

    if not decl or decl.get("extraction_status") != "FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_APPLICABLE",
            severity="INFO",
            message="Importer address evidence not applicable when importer is not declared.",
            field_value=None,
            confidence=1.0,
            evidence={},
            rule_reference=ref
        )

    val = decl.get("detected_value") or ""
    if len(val.strip()) >= 10:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message="Importer physical address evidence is substantive.",
            field_value=val,
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="WARNING",
        severity=severity,
        message="Importer address appears brief.",
        field_value=val,
        confidence=decl.get("confidence", 0.6),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def register_importer_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="IMPORTER_PRESENT",
        field_name="IMPORTER",
        description="Declaration of authorized Indian importer for foreign packaged goods",
        severity="WARNING",
        rule_source="Rule 6(1)(b), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_importer_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="IMPORTER_ADDRESS_EVIDENCE",
        field_name="IMPORTER",
        description="Substantive physical premises address evidence for importer",
        severity="WARNING",
        rule_source="Rule 6(1)(b), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_importer_address_evidence
    ))
