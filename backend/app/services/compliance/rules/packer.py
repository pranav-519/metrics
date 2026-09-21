from typing import Dict, Any, Optional
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_packer_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "PACKER_PRESENT"
    field_name = "PACKER"
    ref = "Rule 6(1)(b), Legal Metrology (PC) Rules 2011"
    severity = "WARNING"

    if decl and decl.get("extraction_status") == "FOUND" and decl.get("detected_value"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message="Packer declaration detected on package.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )

    # If manufacturer is already declared, packer declaration is often not applicable
    mfg_decl = all_decls.get("MANUFACTURER") or all_decls.get("manufacturer")
    if mfg_decl and mfg_decl.get("extraction_status") == "FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_APPLICABLE",
            severity="INFO",
            message="Distinct packer declaration is optional when manufacturer details are declared.",
            field_value=None,
            confidence=1.0,
            evidence={},
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="NOT_VERIFIABLE",
        severity=severity,
        message="Neither manufacturer nor packer declaration was detected.",
        field_value=None,
        confidence=0.0,
        evidence={},
        rule_reference=ref
    )


def evaluate_packer_address_evidence(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "PACKER_ADDRESS_EVIDENCE"
    field_name = "PACKER"
    ref = "Rule 6(1)(b), Legal Metrology (PC) Rules 2011"
    severity = "WARNING"

    if not decl or decl.get("extraction_status") != "FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_APPLICABLE",
            severity="INFO",
            message="Packer address evidence not applicable when packer is not declared.",
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
            message="Packer physical address evidence is substantive.",
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
        message="Packer address appears brief. Full physical postal address advised.",
        field_value=val,
        confidence=decl.get("confidence", 0.6),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def register_packer_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="PACKER_PRESENT",
        field_name="PACKER",
        description="Declaration of third-party or contract packaging entity",
        severity="WARNING",
        rule_source="Rule 6(1)(b), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_packer_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="PACKER_ADDRESS_EVIDENCE",
        field_name="PACKER",
        description="Substantive physical premises address evidence for packer",
        severity="WARNING",
        rule_source="Rule 6(1)(b), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_packer_address_evidence
    ))
