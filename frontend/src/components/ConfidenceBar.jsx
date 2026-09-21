import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function ConfidenceBar({ confidence = 0.0 }) {
  const percent = Math.round(confidence * 100);

  let barColor = "bg-emerald-500";
  let textColor = "text-emerald-700";
  let rating = "High Confidence";

  if (percent < 55) {
    barColor = "bg-amber-500";
    textColor = "text-amber-700 font-semibold";
    rating = "Low Confidence (Uncertain)";
  } else if (percent < 80) {
    barColor = "bg-blue-500";
    textColor = "text-blue-700";
    rating = "Moderate Confidence";
  }

  return (
    <div className="w-full max-w-xs space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className={`flex items-center gap-1 ${textColor}`}>
          {percent < 55 && <AlertCircle className="w-3 h-3 text-amber-600 inline" />}
          {rating}
        </span>
        <span className="font-mono font-medium text-slate-700">{percent}%</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(100, Math.max(5, percent))}%` }}
        />
      </div>
    </div>
  );
}
