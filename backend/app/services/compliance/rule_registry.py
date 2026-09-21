from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
from app.services.compliance.rule_result import EvaluatedRuleResult

@dataclass
class RegisteredRule:
    """
    Metadata and evaluation function for a registered statutory compliance rule.
    Severity indicates statutory importance; Rule Source provides legal provenance.
    """
    rule_id: str
    field_name: str
    description: str
    severity: str  # CRITICAL, ERROR, WARNING, INFO
    rule_source: str  # e.g. "Rule 6(1)(e), Legal Metrology (PC) Rules 2011" or "PENDING_REVIEW"
    evaluator: Callable[[Optional[Dict[str, Any]], Dict[str, Any]], EvaluatedRuleResult]


class RuleRegistry:
    """
    Centralized discovery and management registry for statutory compliance rules.
    """
    _rules: Dict[str, RegisteredRule] = {}

    @classmethod
    def register(cls, rule: RegisteredRule) -> None:
        cls._rules[rule.rule_id] = rule

    @classmethod
    def get_rule(cls, rule_id: str) -> Optional[RegisteredRule]:
        return cls._rules.get(rule_id)

    @classmethod
    def get_all_rules(cls) -> List[RegisteredRule]:
        return list(cls._rules.values())

    @classmethod
    def get_rules_for_field(cls, field_name: str) -> List[RegisteredRule]:
        target = field_name.upper()
        return [r for r in cls._rules.values() if r.field_name.upper() == target]

    @classmethod
    def clear(cls) -> None:
        cls._rules.clear()
