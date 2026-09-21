import React, { useEffect, useState } from 'react';
import { 
  CheckCircle2, Loader2, ShieldCheck, Eye, 
  FileText, Sparkles, Scale, Sliders, Check 
} from 'lucide-react';

const STAGES = [
  { id: "uploading", label: "Uploading Package Images", desc: "Verifying MIME format and multi-panel uploads" },
  { id: "quality", label: "Image Quality & Glare Check", desc: "Computing Laplacian blur score and specular highlights" },
  { id: "preprocess", label: "CLAHE Preprocessing", desc: "Adaptive histogram equalization and perspective correction" },
  { id: "ocr", label: "Pre-trained OCR Execution", desc: "Extracting text bounding boxes with per-token confidence" },
  { id: "extraction", label: "Declaration Extraction", desc: "Parsing MRP, Net Qty, Dates, Mfg details & Consumer Care" },
  { id: "rules_sel", label: "Category Rule Selection", desc: "Loading statutory schedules for selected commodity category" },
  { id: "validation", label: "Versioned Legal Rule Validation", desc: "Checking clauses against Legal Metrology Rules 2011" },
  { id: "measurement", label: "Physical Font Height Measurement", desc: "Pixel-to-physical dimension conversion against statutory minimums" },
  { id: "reporting", label: "Explainable Report Generation", desc: "Synthesizing audit verdict, warnings, and suggested actions" },
];

export default function AnalysisPage({ scanResult, onComplete }) {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    // Progressively advance through stages to provide visual clarity to inspectors
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < STAGES.length - 1) {
          return prev + 1;
        } else {
          clearInterval(interval);
          setTimeout(() => {
            onComplete(scanResult);
          }, 800);
          return prev;
        }
      });
    }, 450);

    return () => clearInterval(interval);
  }, [scanResult, onComplete]);

  return (
    <div className="max-w-3xl mx-auto py-8 space-y-6">
      {/* Top Card */}
      <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm text-center space-y-3">
        <div className="w-12 h-12 rounded-2xl bg-blue-100 text-blue-700 flex items-center justify-center mx-auto shadow-inner">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-blue-700">Pipeline in Progress</span>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Analyzing Packaging Compliance</h1>
          <p className="text-sm text-slate-500 max-w-md mx-auto mt-1">
            Applying Legal Metrology (Packaged Commodities) Rules 2011 to <strong>{scanResult?.product_name || "Packaging Sample"}</strong>
          </p>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden max-w-md mx-auto border border-slate-200 mt-4">
          <div
            className="h-full bg-blue-600 rounded-full transition-all duration-300"
            style={{ width: `${Math.round(((currentStep + 1) / STAGES.length) * 100)}%` }}
          />
        </div>
        <p className="text-xs font-mono text-slate-500">
          Stage {currentStep + 1} of {STAGES.length} ({Math.round(((currentStep + 1) / STAGES.length) * 100)}%)
        </p>
      </div>

      {/* Pipeline Steps List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs divide-y divide-slate-100 overflow-hidden">
        {STAGES.map((stage, idx) => {
          const isDone = idx < currentStep;
          const isCurrent = idx === currentStep;

          return (
            <div
              key={stage.id}
              className={`p-4 flex items-center gap-4 transition-colors ${
                isCurrent ? 'bg-blue-50/50' : isDone ? 'bg-white' : 'bg-slate-50/40 opacity-60'
              }`}
            >
              <div className="shrink-0">
                {isDone ? (
                  <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                    <Check className="w-4 h-4" />
                  </div>
                ) : isCurrent ? (
                  <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-sm shadow-blue-500/30">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                ) : (
                  <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center text-xs font-mono">
                    {idx + 1}
                  </div>
                )}
              </div>

              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className={`text-sm font-semibold ${isCurrent ? 'text-blue-900' : isDone ? 'text-slate-900' : 'text-slate-500'}`}>
                    {stage.label}
                  </h3>
                  {isCurrent && (
                    <span className="text-[11px] font-semibold text-blue-600 bg-blue-100/70 px-2 py-0.5 rounded-full">
                      Processing...
                    </span>
                  )}
                  {isDone && (
                    <span className="text-[11px] font-medium text-emerald-600">
                      Verified
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{stage.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
