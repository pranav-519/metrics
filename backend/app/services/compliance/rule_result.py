from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class EvaluatedRuleResult:
    """
    Structured outcome of a deterministic compliance rule evaluation.
    Severity and status are strictly independent.
    """
    rule_id: str
    field_name: str
    status: str  # PASS, FAIL, WARNING, NOT_VERIFIABLE, NOT_APPLICABLE
    severity: str = "ERROR"  # CRITICAL, ERROR, WARNING, INFO
    message: str = ""
    field_value: Optional[str] = None
    confidence: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    rule_reference: Optional[str] = None
    suggested_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "field_name": self.field_name,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "reason": self.message,
            "field_value": self.field_value,
            "detected_value": self.field_value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "rule_reference": self.rule_reference,
            "rule_source": self.rule_reference,
            "suggested_action": self.suggested_action,
        }
