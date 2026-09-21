import React from 'react';
import { Check, AlertTriangle, XCircle, Info } from 'lucide-react';

export default function QualityBadge({ status, blurScore, glareScore }) {
  const configs = {
    GOOD: {
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      icon: Check,
      text: "Optimal Quality"
    },
    ACCEPTABLE: {
      bg: "bg-blue-50 text-blue-700 border-blue-200",
      icon: Info,
      text: "Acceptable Quality"
    },
    POOR: {
      bg: "bg-amber-50 text-amber-700 border-amber-200",
      icon: AlertTriangle,
      text: "Quality Warnings"
    },
    CRITICAL_ISSUES: {
      bg: "bg-rose-50 text-rose-700 border-rose-200",
      icon: XCircle,
      text: "Unusable Image"
    }
  };

  const current = configs[status] || configs.GOOD;
  const Icon = current.icon;

  return (
    <div className="flex flex-col gap-1 text-xs">
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-semibold ${current.bg} w-fit`}>
        <Icon className="w-3 h-3" />
        {current.text}
      </span>
      {blurScore !== undefined && glareScore !== undefined && (
        <span className="text-[11px] text-slate-500 font-mono">
          Sharpness: {blurScore} | Glare: {glareScore}%
        </span>
      )}
    </div>
  );
}
