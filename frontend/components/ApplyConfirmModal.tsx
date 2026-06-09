"use client";
import { X, CheckCircle, Loader2 } from "lucide-react";

interface Props {
  screenshotB64: string;
  fieldsFilled: string[];
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}

export default function ApplyConfirmModal({ screenshotB64, fieldsFilled, onConfirm, onCancel, loading }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="card w-full max-w-2xl fade-up overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/8">
          <h2 className="text-white font-semibold">Review Before Submitting</h2>
          <button onClick={onCancel} className="text-slate-400 hover:text-white">
            <X size={18} />
          </button>
        </div>

        {/* Screenshot */}
        <div className="p-4 bg-[#0d0d16]">
          <img
            src={`data:image/png;base64,${screenshotB64}`}
            alt="Form preview"
            className="w-full rounded-lg border border-white/8 max-h-72 object-top object-cover"
          />
        </div>

        {/* Fields filled */}
        <div className="px-4 pb-3">
          <p className="text-xs text-slate-400 mb-2">Fields filled by bot:</p>
          <div className="flex flex-wrap gap-2">
            {fieldsFilled.map((f, i) => (
              <span key={i} className="flex items-center gap-1 text-xs bg-green-900/30 text-green-400 border border-green-800/40 px-2 py-0.5 rounded-full">
                <CheckCircle size={11} /> {f}
              </span>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 p-4 border-t border-white/8">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 rounded-xl border border-white/10 text-slate-300 text-sm hover:bg-white/5 transition"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 py-2.5 rounded-xl btn-glow text-white text-sm font-semibold flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
            {loading ? "Submitting..." : "Confirm & Submit"}
          </button>
        </div>
      </div>
    </div>
  );
}
