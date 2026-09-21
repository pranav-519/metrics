import React from 'react';
import { CheckCircle2, AlertOctagon, HelpCircle, XCircle, MinusCircle, Eye } from 'lucide-react';

export default function StatusBadge({ status, size = "md" }) {
  const configs = {
    VERIFIED_COMPLIANT: {
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      icon: CheckCircle2,
      label: "VERIFIED COMPLIANT",
      tooltip: "Declaration satisfies applicable legal requirements with high OCR confidence."
    },
    COMPLIANT: {
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      icon: CheckCircle2,
      label: "COMPLIANT",
      tooltip: "All statutory package declarations satisfy legal requirements."
    },
    PASS: {
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      icon: CheckCircle2,
      label: "PASS",
      tooltip: "Rule evaluated and satisfied with verified evidence."
    },
    POTENTIAL_NON_COMPLIANCE: {
      bg: "bg-rose-50 text-rose-700 border-rose-200",
      icon: AlertOctagon,
      label: "POTENTIAL NON-COMPLIANCE",
      tooltip: "Identified discrepancy against statutory rules. Further verification required."
    },
    NON_COMPLIANT: {
      bg: "bg-rose-50 text-rose-700 border-rose-200",
      icon: XCircle,
      label: "NON-COMPLIANT",
      tooltip: "One or more statutory requirements are affirmatively violated."
    },
    FAIL: {
      bg: "bg-rose-50 text-rose-700 border-rose-200",
      icon: XCircle,
      label: "FAIL",
      tooltip: "Sufficient evidence establishes that statutory requirement is violated."
    },
    WARNING: {
      bg: "bg-amber-50 text-amber-700 border-amber-200",
      icon: AlertOctagon,
      label: "WARNING",
      tooltip: "Advisory or partial compliance note requiring inspector attention."
    },
    NOT_VERIFIABLE: {
      bg: "bg-blue-50 text-blue-700 border-blue-200",
      icon: HelpCircle,
      label: "NOT VERIFIABLE",
      tooltip: "Evidence is missing, low confidence, or ambiguous. Never fabricated."
    },
    UNABLE_TO_VERIFY: {
      bg: "bg-amber-50 text-amber-700 border-amber-200",
      icon: HelpCircle,
      label: "UNABLE TO VERIFY",
      tooltip: "Low OCR confidence or image degradation. NEVER classified as legally missing."
    },
    NOT_FOUND: {
      bg: "bg-slate-100 text-slate-700 border-slate-300",
      icon: XCircle,
      label: "NOT DETECTED",
      tooltip: "Declaration not found across any uploaded packaging panels."
    },
    NOT_APPLICABLE: {
      bg: "bg-slate-50 text-slate-500 border-slate-200",
      icon: MinusCircle,
      label: "NOT APPLICABLE",
      tooltip: "Non-mandatory rule for this product category or packaging size."
    },
    REVIEW_REQUIRED: {
      bg: "bg-indigo-50 text-indigo-700 border-indigo-200",
      icon: Eye,
      label: "REVIEW REQUIRED",
      tooltip: "Manual inspector confirmation recommended for category-specific schedule."
    },
    FOUND: {
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      icon: CheckCircle2,
      label: "FOUND",
      tooltip: "Field detected from package OCR detections."
    },
    AMBIGUOUS: {
      bg: "bg-purple-50 text-purple-700 border-purple-200",
      icon: AlertOctagon,
      label: "AMBIGUOUS",
      tooltip: "Field declaration contains ambiguity or conflicts across multiple photographs."
    },
    LOW_CONFIDENCE: {
      bg: "bg-amber-50 text-amber-700 border-amber-200",
      icon: HelpCircle,
      label: "LOW CONFIDENCE",
      tooltip: "Low OCR detection confidence. Never fabricated or guessed."
    },
  };

  const current = configs[status] || configs.REVIEW_REQUIRED;
  const Icon = current.icon;

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs font-semibold gap-1",
    md: "px-2.5 py-1 text-xs font-semibold gap-1.5",
    lg: "px-3.5 py-1.5 text-sm font-semibold gap-2",
  }[size] || "px-2.5 py-1 text-xs font-semibold gap-1.5";

  return (
    <span
      title={current.tooltip}
      className={`inline-flex items-center rounded-full border shadow-xs transition-colors ${current.bg} ${sizeClasses}`}
    >
      <Icon className={size === "lg" ? "w-4 h-4 shrink-0" : "w-3.5 h-3.5 shrink-0"} />
      <span>{current.label}</span>
    </span>
  );
}
