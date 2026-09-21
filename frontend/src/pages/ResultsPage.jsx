import React, { useState } from 'react';
import { 
  ShieldCheck, AlertTriangle, CheckCircle2, HelpCircle, 
  ArrowLeft, Download, Printer, RefreshCw, Eye, 
  Scale, Tag, Info, AlertOctagon, FileText, Calendar 
} from 'lucide-react';
import StatusBadge from '../components/StatusBadge';
import ConfidenceBar from '../components/ConfidenceBar';
import QualityBadge from '../components/QualityBadge';

export default function ResultsPage({ scan, onBack, onRefresh }) {
  const [activeTab, setActiveTab] = useState("rules"); // default to rules to highlight compliance
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evalError, setEvalError] = useState(null);

  if (!scan) {
    return (
      <div className="p-8 text-center text-slate-500">
        <p>No scan selected or report not found.</p>
        <button onClick={onBack} className="mt-4 text-blue-600 underline font-semibold text-sm">
          Return to Dashboard
        </button>
      </div>
    );
  }

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    setEvalError(null);
    try {
      const res = await fetch(`/api/scans/${scan.id}/evaluate`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Evaluation failed.");
      }
      if (onRefresh) {
        await onRefresh();
      }
    } catch (e) {
      setEvalError(e.message);
    } finally {
      setIsEvaluating(false);
    }
  };

  const declarations = scan.declarations || [];
  const rules = scan.latest_evaluation?.results || scan.rule_results || [];
  const evaluation = scan.latest_evaluation;
  const images = scan.images || [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Top Breadcrumb & Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white px-3 py-1.5 rounded-lg border border-slate-200 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Dashboard</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={handleEvaluate}
            disabled={isEvaluating}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-3 py-1.5 rounded-lg shadow-xs transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isEvaluating ? "animate-spin" : ""}`} />
            <span>{isEvaluating ? "Evaluating..." : "Re-evaluate Rules"}</span>
          </button>

          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs transition-colors cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Report</span>
          </button>
        </div>
      </div>

      {evalError && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs text-rose-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{evalError}</span>
        </div>
      )}

      {/* Primary Executive Verdict Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-slate-100 pb-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-700 text-xs font-medium">
                {scan.category_name || "General Packaged Commodity"}
              </span>
              <span className="text-xs text-slate-400 font-mono">Scan ID #{scan.id}</span>
              {scan.is_demo && (
                <span className="px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200 text-[10px] font-bold">
                  DEMO AUDIT RECORD
                </span>
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              {scan.product_name}
            </h1>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Calendar className="w-3.5 h-3.5" />
              <span>Inspection Timestamp: {new Date(scan.created_at).toLocaleString()}</span>
            </div>
          </div>

          {/* Verdict Badge & Score Box */}
          <div className="flex sm:flex-col items-center sm:items-end justify-between gap-3 shrink-0 bg-slate-50 sm:bg-transparent p-4 sm:p-0 rounded-xl">
            <StatusBadge status={scan.overall_status} size="lg" />
            <div className="text-right">
              <span className="text-xs text-slate-500 font-medium">Compliance Score</span>
              <div className="text-2xl font-bold font-mono text-slate-900">
                {scan.compliance_score}%
              </div>
            </div>
          </div>
        </div>

        {/* Summary Verdict Note */}
        <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/80 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            <span>Official Inspection Assistance Assessment</span>
          </div>
          <p className="text-sm text-slate-800 leading-relaxed font-medium">
            {scan.summary_verdict || "Assessment completed."}
          </p>

          <div className="pt-2 border-t border-slate-200/60 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
            <div className="flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-slate-400" />
              <span>
                Measurement Status: <strong>{scan.is_calibrated ? "Calibrated against known reference" : "Estimated distance heuristic"}</strong>
              </span>
            </div>
            <span className="italic text-slate-400">
              * Legal Metrology Act, 2009 & Packaged Commodities Rules, 2011
            </span>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-slate-200 gap-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab("declarations")}
          className={`pb-3 relative cursor-pointer ${
            activeTab === "declarations"
              ? "text-blue-700 font-bold border-b-2 border-blue-600"
              : "text-slate-500 hover:text-slate-900"
          }`}
        >
          <span>Extracted Declarations</span>
          <span className="ml-2 px-1.5 py-0.5 rounded-full bg-slate-100 text-[11px] text-slate-600">
            {declarations.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("rules")}
          className={`pb-3 relative cursor-pointer ${
            activeTab === "rules"
              ? "text-blue-700 font-bold border-b-2 border-blue-600"
              : "text-slate-500 hover:text-slate-900"
          }`}
        >
          <span>Rule Verifications & Explainability</span>
          <span className="ml-2 px-1.5 py-0.5 rounded-full bg-slate-100 text-[11px] text-slate-600">
            {rules.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("images")}
          className={`pb-3 relative cursor-pointer ${
            activeTab === "images"
              ? "text-blue-700 font-bold border-b-2 border-blue-600"
              : "text-slate-500 hover:text-slate-900"
          }`}
        >
          <span>Packaging Photographs & Quality</span>
          <span className="ml-2 px-1.5 py-0.5 rounded-full bg-slate-100 text-[11px] text-slate-600">
            {images.length}
          </span>
        </button>
      </div>

      {/* Tab Content: Extracted Declarations */}
      {activeTab === "declarations" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-800">Statutory Package Declarations</h3>
              <p className="text-xs text-slate-500">Extracted fields, OCR confidences, and physical font measurements</p>
            </div>
            <span className="text-xs text-slate-500 font-mono">
              Threshold: 55% confidence
            </span>
          </div>

          <div className="divide-y divide-slate-100">
            {declarations.map((decl) => (
              <div key={decl.id || decl.field_name} className="p-5 space-y-3 hover:bg-slate-50/50 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-slate-900">{decl.display_name}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono uppercase">
                        {decl.field_name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-mono uppercase">
                        {decl.source_image_role} panel
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {decl.has_conflict && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 font-bold uppercase tracking-wider">
                        Conflict
                      </span>
                    )}
                    <StatusBadge status={decl.extraction_status || decl.status} size="sm" />
                  </div>
                </div>

                {/* Detected Value & OCR Snippet */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/60 space-y-1">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase">Detected Value:</span>
                    <p className="font-semibold text-slate-900 text-sm">
                      {decl.detected_value || <span className="text-slate-400 italic">Not Detected</span>}
                    </p>
                  </div>

                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/60 space-y-1">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase">Raw OCR String:</span>
                    <p className="font-mono text-slate-700 break-all text-xs">
                      {decl.raw_ocr_snippet || <span className="text-slate-400 italic">No text extracted</span>}
                    </p>
                  </div>
                </div>

                {/* Uncertainty & Measurement Indicators */}
                <div className="flex flex-wrap items-center justify-between gap-4 pt-1 text-xs border-t border-slate-100">
                  <div className="w-full sm:w-auto">
                    <ConfidenceBar confidence={decl.confidence} />
                  </div>

                  {decl.estimated_font_height_mm && (
                    <div className="flex items-center gap-3 text-slate-600">
                      <div className="flex items-center gap-1">
                        <Scale className="w-3.5 h-3.5 text-blue-600" />
                        <span>Estimated Font Height:</span>
                        <strong className="font-mono text-slate-900">{decl.estimated_font_height_mm} mm</strong>
                      </div>
                      <span className="text-slate-300">|</span>
                      <span className="text-slate-500">
                        Statutory Min: <strong className="font-mono">{decl.required_font_height_mm} mm</strong>
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        decl.measurement_confidence === "VERIFIED" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
                      }`}>
                        {decl.measurement_confidence}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab Content: Rule Verifications */}
      {activeTab === "rules" && (
        <div className="space-y-4">
          {/* Executive Evaluation Summary Metrics Bar */}
          {evaluation?.summary && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-blue-600" />
                  <span className="font-bold text-slate-900 text-sm">Deterministic Compliance Evaluation</span>
                  <span className="text-xs text-slate-400">({evaluation.total_rules} Statutory Rules Evaluated)</span>
                </div>
                <StatusBadge status={evaluation.overall_status} size="md" />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-center text-xs">
                <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200">
                  <div className="text-lg font-bold text-emerald-700">{evaluation.summary.passed_rules ?? evaluation.passed_rules}</div>
                  <div className="text-[11px] font-semibold text-emerald-800 uppercase">PASS</div>
                </div>
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200">
                  <div className="text-lg font-bold text-rose-700">{evaluation.summary.failed_rules ?? evaluation.failed_rules}</div>
                  <div className="text-[11px] font-semibold text-rose-800 uppercase">FAIL</div>
                </div>
                <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200">
                  <div className="text-lg font-bold text-amber-700">{evaluation.summary.warning_rules ?? evaluation.warning_rules}</div>
                  <div className="text-[11px] font-semibold text-amber-800 uppercase">WARNING</div>
                </div>
                <div className="p-2.5 rounded-lg bg-blue-50 border border-blue-200">
                  <div className="text-lg font-bold text-blue-700">{evaluation.summary.not_verifiable_rules ?? evaluation.not_verifiable_rules}</div>
                  <div className="text-[11px] font-semibold text-blue-800 uppercase">NOT VERIFIABLE</div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="text-lg font-bold text-slate-700">{evaluation.summary.not_applicable_rules ?? evaluation.not_applicable_rules}</div>
                  <div className="text-[11px] font-semibold text-slate-600 uppercase">NOT APPLICABLE</div>
                </div>
                <div className="p-2.5 rounded-lg bg-purple-50 border border-purple-200">
                  <div className="text-lg font-bold text-purple-700">{evaluation.summary.critical_errors ?? evaluation.critical_errors ?? 0}</div>
                  <div className="text-[11px] font-semibold text-purple-800 uppercase">CRITICAL FAIL</div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-900">
            <p className="font-semibold">Legal Metrology Compliance Guarantee</p>
            <p className="text-blue-800 mt-0.5">
              Rule severity (CRITICAL, ERROR, WARNING, INFO) and compliance status (PASS, FAIL, WARNING, NOT_VERIFIABLE, NOT_APPLICABLE) are strictly decoupled. Missing or blurry declarations are marked NOT_VERIFIABLE and are never fabricated into premature legal violations.
            </p>
          </div>

          <div className="space-y-3">
            {rules.map((rule, idx) => {
              const severity = rule.severity || "ERROR";
              const severityClasses = {
                CRITICAL: "bg-red-100 text-red-800 border-red-200",
                ERROR: "bg-amber-100 text-amber-800 border-amber-200",
                WARNING: "bg-yellow-100 text-yellow-800 border-yellow-200",
                INFO: "bg-slate-100 text-slate-700 border-slate-200"
              }[severity] || "bg-slate-100 text-slate-700 border-slate-200";

              const fieldLabel = (rule.field_name || rule.field_target || "Declaration").toUpperCase();
              const ruleSource = rule.rule_source || rule.rule_reference || "APPROVED_RULE_REFERENCE";

              return (
                <div key={rule.id || rule.rule_id || idx} className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-slate-900">
                          {fieldLabel} Check
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${severityClasses}`}>
                          SEVERITY: {severity}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-[10px] font-mono font-semibold border border-blue-200">
                          {ruleSource}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 font-mono">
                        Rule ID: {rule.rule_id}
                      </div>
                    </div>

                    <StatusBadge status={rule.status} size="md" />
                  </div>

                  {/* Values & Evidence Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/60">
                      <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">Detected Packaging Value:</span>
                      <p className="font-semibold text-slate-900">{rule.detected_value || rule.field_value || <span className="text-slate-400 italic">Not Detected</span>}</p>
                      {rule.normalized_value && rule.normalized_value !== rule.detected_value && (
                        <p className="text-[11px] text-slate-500 mt-1">Normalized: <span className="font-mono font-semibold text-slate-700">{rule.normalized_value}</span></p>
                      )}
                    </div>

                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/60">
                      <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">Evidence & Traceability:</span>
                      {rule.evidence && Object.keys(rule.evidence).length > 0 ? (
                        <div className="text-[11px] text-slate-600 space-y-0.5">
                          {rule.evidence.source_ocr_ids && (
                            <p>Source OCR IDs: <span className="font-mono text-slate-800">{JSON.stringify(rule.evidence.source_ocr_ids)}</span></p>
                          )}
                          {rule.evidence.has_conflict && (
                            <p className="text-amber-700 font-semibold">Multiple conflicting detections found on package</p>
                          )}
                          {rule.evidence.bounding_box && (
                            <p>Box: <span className="font-mono text-slate-700">{JSON.stringify(rule.evidence.bounding_box)}</span></p>
                          )}
                        </div>
                      ) : (
                        <p className="text-slate-400 italic">No OCR box coordinates mapped</p>
                      )}
                    </div>
                  </div>

                  {/* Conflict alert when has_conflict is true */}
                  {rule.evidence?.has_conflict && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 space-y-1">
                      <div className="flex items-center gap-1.5 font-bold text-amber-800">
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                        <span>Conflicting Candidates Detected (Rule Evaluated as NOT_VERIFIABLE)</span>
                      </div>
                      <p className="text-amber-800">
                        System detected multiple conflicting declarations across panels. Compliance status is strictly set to NOT_VERIFIABLE rather than arbitrarily picking one candidate.
                      </p>
                      {rule.evidence.alternate_candidates && (
                        <p className="font-mono text-[11px] text-amber-700 mt-1">
                          Alternates: {rule.evidence.alternate_candidates.map(a => a.value || a.raw_value).join(", ")}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Statutory Reason & Suggested Action */}
                  <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200/60 text-xs space-y-1.5">
                    <div className="flex items-start gap-2">
                      <Info className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                      <div>
                        <strong className="text-slate-800">Reason / Finding: </strong>
                        <span className="text-slate-700">{rule.reason || rule.message}</span>
                      </div>
                    </div>

                    {rule.suggested_action && (
                      <div className="flex items-start gap-2 text-emerald-800 bg-emerald-50/70 p-2 rounded border border-emerald-100">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-emerald-900">Recommended Action: </strong>
                          <span>{rule.suggested_action}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab Content: Packaging Images & Quality */}
      {activeTab === "images" && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="text-base font-bold text-slate-900">Uploaded Packaging Photographs</h3>
            <p className="text-xs text-slate-500">Computer-vision quality assessments (sharpness, glare, lighting, resolution)</p>
          </div>

          {images.length === 0 ? (
            <p className="text-xs text-slate-500">No images linked to this scan.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {images.map((img) => (
                <div key={img.id} className="border border-slate-200 rounded-xl overflow-hidden bg-slate-50/50">
                  <div className="p-3 border-b border-slate-200 bg-white flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-800">
                        {img.image_type || img.image_role} Panel
                      </span>
                      <span className="text-[11px] text-slate-500">
                        {img.resolution_w}x{img.resolution_h}px
                      </span>
                      {img.ocr_engine_used && (
                        <span className="text-[10px] font-mono bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-semibold">
                          {img.ocr_engine_used}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {img.preprocessing_status === "APPLIED" && (
                        <span className="text-[10px] font-medium bg-purple-50 text-purple-700 border border-purple-200 px-1.5 py-0.5 rounded">
                          CLAHE Preprocessed
                        </span>
                      )}
                      <QualityBadge
                        status={img.quality_status}
                        blurScore={img.blur_score}
                        glareScore={img.glare_score}
                      />
                    </div>
                  </div>

                  <div className="aspect-video bg-black/5 flex items-center justify-center p-2">
                    <img
                      src={img.file_path}
                      alt={img.original_filename}
                      className="max-h-56 w-auto object-contain rounded-md"
                      onError={(e) => {
                        // Fallback placeholder
                        e.target.onerror = null;
                        e.target.src = "https://placehold.co/600x400/e2e8f0/475569?text=Packaging+Image+Preview";
                      }}
                    />
                  </div>

                  <div className="p-3 bg-white border-t border-slate-200 text-xs text-slate-600 space-y-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <span className="font-semibold text-slate-700">Quality Notes: </span>
                        <span>{img.quality_notes || "Adequate resolution and contrast for OCR."}</span>
                      </div>
                      {img.ocr_detections_count !== undefined && (
                        <span className="text-[11px] font-mono text-slate-500">
                          {img.ocr_detections_count} text token{img.ocr_detections_count === 1 ? '' : 's'} (avg conf: {Math.round((img.ocr_confidence || 0) * 100)}%)
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
