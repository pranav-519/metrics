import React, { useState } from 'react';
import { 
  Upload, Image as ImageIcon, CheckCircle, AlertCircle, 
  Trash2, ArrowRight, ShieldCheck, Scale, Sparkles 
} from 'lucide-react';

export default function NewScanPage({ categories = [], onScanCreated, onCancel }) {
  const [productName, setProductName] = useState("");
  const [categoryId, setCategoryId] = useState(categories[0]?.id || 1);
  const [calibrationMethod, setCalibrationMethod] = useState("uncalibrated_heuristic");
  const [pixelsPerMm, setPixelsPerMm] = useState("");
  
  // Image files & previews
  const [images, setImages] = useState({
    front: null,
    back: null,
    side: null,
    close_up: null,
  });

  const [previews, setPreviews] = useState({
    front: null,
    back: null,
    side: null,
    close_up: null,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleImageChange = (role, file) => {
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setErrorMessage("Only image files (.jpg, .jpeg, .png, .webp) are supported.");
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      setErrorMessage("File exceeds the 15MB limit.");
      return;
    }

    setErrorMessage("");
    setImages(prev => ({ ...prev, [role]: file }));

    // Generate preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviews(prev => ({ ...prev, [role]: reader.result }));
    };
    reader.readAsDataURL(file);
  };

  const removeImage = (role) => {
    setImages(prev => ({ ...prev, [role]: null }));
    setPreviews(prev => ({ ...prev, [role]: null }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!productName.trim()) {
      setErrorMessage("Please enter the product name and packaging variant.");
      return;
    }

    if (!images.front) {
      setErrorMessage("Primary / Front panel photograph is mandatory for inspection.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");

    try {
      const formData = new FormData();
      formData.append("product_name", productName.trim());
      formData.append("category_id", categoryId);
      formData.append("calibration_method", calibrationMethod);
      if (pixelsPerMm && Number(pixelsPerMm) > 0) {
        formData.append("pixels_per_mm", pixelsPerMm);
      }

      if (images.front) formData.append("front_image", images.front);
      if (images.back) formData.append("back_image", images.back);
      if (images.side) formData.append("side_image", images.side);
      if (images.close_up) formData.append("close_up_image", images.close_up);

      const response = await fetch("/api/scans", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to initiate compliance analysis.");
      }

      const scanResult = await response.json();
      onScanCreated(scanResult);
    } catch (err) {
      setErrorMessage(err.message || "An unexpected error occurred during image upload.");
      setIsSubmitting(false);
    }
  };

  const slotLabels = {
    front: { title: "Front Panel (Principal Display)", required: true, desc: "Contains brand name, net quantity & MRP" },
    back: { title: "Back Panel (Details & Care)", required: false, desc: "Ingredients, consumer care, mfg address" },
    side: { title: "Side Panel (Batch / Expiry)", required: false, desc: "Batch numbers, date stamps, barcode" },
    close_up: { title: "Close-up (Stamp / Small Text)", required: false, desc: "Fine print declarations or unit sale price" },
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-2">
        <div className="flex items-center gap-2 text-blue-700 text-xs font-semibold uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4" />
          <span>New Legal Metrology Inspection</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Initiate Packaging Compliance Scan</h1>
        <p className="text-sm text-slate-600">
          Upload multi-angle photographs of the packaged product. MetriCheck will perform OCR extraction, 
          apply category-specific legal rules, and calculate physical font height dimensions.
        </p>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Step 1: Product Information */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs flex items-center justify-center font-bold">1</span>
            Product & Statutory Category
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">
                Product Name & Net Specification <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Parle-G Glucose Biscuits (800g)"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white focus:outline-hidden text-slate-900"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">
                Statutory Product Category <span className="text-rose-500">*</span>
              </label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(Number(e.target.value))}
                className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white focus:outline-hidden text-slate-900 cursor-pointer"
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-slate-500">
                Determines applicable versioned legal schedules (e.g. Rule 6 & First Schedule).
              </p>
            </div>
          </div>

          {/* Physical Calibration Setting */}
          <div className="pt-3 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5 text-blue-600" />
                Physical Dimension Calibration Reference
              </label>
              <select
                value={calibrationMethod}
                onChange={(e) => setCalibrationMethod(e.target.value)}
                className="w-full px-3.5 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-700 cursor-pointer"
              >
                <option value="uncalibrated_heuristic">Heuristic Distance Estimate (Uncalibrated - Default)</option>
                <option value="reference_id_card_width">Known Reference: ID/Credit Card (85.6 mm width)</option>
                <option value="reference_rupee_coin_5">Known Reference: ₹5 Coin (23.0 mm diameter)</option>
                <option value="manual_dpi">Manual DPI / Pixel Calibration</option>
              </select>
            </div>

            {calibrationMethod === "manual_dpi" && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">
                  Custom Pixels per Millimeter (px/mm)
                </label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="e.g. 11.8"
                  value={pixelsPerMm}
                  onChange={(e) => setPixelsPerMm(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900"
                />
              </div>
            )}
          </div>
        </div>

        {/* Step 2: Multi-Image Upload */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs flex items-center justify-center font-bold">2</span>
              Package Photographs
            </h2>
            <span className="text-xs text-slate-500">Multi-panel inspection supported</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Object.entries(slotLabels).map(([role, meta]) => {
              const preview = previews[role];

              return (
                <div
                  key={role}
                  className={`border rounded-xl p-4 transition-all ${
                    preview ? 'border-blue-300 bg-blue-50/20' : 'border-slate-200 bg-slate-50/50 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-xs font-bold text-slate-800">
                        {meta.title} {meta.required && <span className="text-rose-500">*</span>}
                      </span>
                      <p className="text-[11px] text-slate-500">{meta.desc}</p>
                    </div>

                    {preview && (
                      <button
                        type="button"
                        onClick={() => removeImage(role)}
                        className="p-1 text-slate-400 hover:text-rose-600 rounded-md transition-colors cursor-pointer"
                        title="Remove photograph"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  {preview ? (
                    <div className="relative rounded-lg overflow-hidden border border-slate-200 bg-black/5 aspect-video flex items-center justify-center">
                      <img
                        src={preview}
                        alt={meta.title}
                        className="w-full h-full object-contain"
                      />
                      <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-md bg-slate-900/80 text-white text-[10px] font-mono flex items-center gap-1">
                        <CheckCircle className="w-3 h-3 text-emerald-400" />
                        <span>Ready for OCR</span>
                      </div>
                    </div>
                  ) : (
                    <label className="cursor-pointer block">
                      <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-blue-500 transition-colors">
                        <Upload className="w-6 h-6 mx-auto text-slate-400 mb-2" />
                        <span className="text-xs font-semibold text-blue-700">Click to upload</span>
                        <p className="text-[11px] text-slate-500 mt-1">JPEG, PNG, WebP up to 15MB</p>
                      </div>
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => handleImageChange(role, e.target.files[0])}
                      />
                    </label>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Submit & Cancel Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2.5 rounded-xl border border-slate-200 text-sm font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            Cancel
          </button>

          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-md shadow-blue-500/25 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Processing Pipeline...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Start Compliance Analysis</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
