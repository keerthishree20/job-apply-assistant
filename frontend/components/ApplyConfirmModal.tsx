"use client";
import { X, CheckCircle, Loader2, AlertTriangle } from "lucide-react";

interface Props {
  screenshotB64: string;
  fieldsFilled: string[];
  /** Fields the bot left blank on purpose; the candidate fills them in the browser window. */
  needsInput: string[];
  /** Set when a confirm attempt was rejected by the form; the session is still open. */
  errorMessage?: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}

export default function ApplyConfirmModal({
  screenshotB64, fieldsFilled, needsInput, errorMessage, onConfirm, onCancel, loading,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="card w-full max-w-2xl fade-up overflow-hidden max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/8">
          <h2 className="text-white font-semibold">Review Before Submitting</h2>
          <button onClick={onCancel} className="text-slate-400 hover:text-white">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto">
          {/* Screenshot */}
          {/* Full-page capture; scroll to check every field before confirming. */}
          <div className="p-4 bg-[#0d0d16]">
            <div className="max-h-80 overflow-y-auto rounded-lg border border-white/8">
              <img
                src={`data:image/png;base64,${screenshotB64}`}
                alt="Form preview"
                className="w-full"
              />
            </div>
          </div>

          {/* Fields filled */}
          <div className="px-4 pb-3">
            <p className="text-xs text-slate-400 mb-2">Filled by the bot from your profile, resume and prepared answers:</p>
            <div className="flex flex-wrap gap-2">
              {fieldsFilled.length === 0 && <span className="text-xs text-slate-500">Nothing.</span>}
              {fieldsFilled.map((f, i) => (
                <span key={i} className="flex items-center gap-1 text-xs bg-green-900/30 text-green-400 border border-green-800/40 px-2 py-0.5 rounded-full">
                  <CheckCircle size={11} /> {f}
                </span>
              ))}
            </div>
          </div>

          {/* Needs the candidate */}
          {needsInput.length > 0 && (
            <div className="mx-4 mb-3 rounded-xl border border-amber-700/40 bg-amber-950/30 p-3">
              <p className="flex items-center gap-2 text-sm text-amber-300 font-medium mb-1">
                <AlertTriangle size={14} /> You need to answer these yourself
              </p>
              <p className="text-xs text-amber-200/70 mb-2">
                Legal or personal questions, and required fields with no data, are never guessed.
                Fill them in the browser window the bot opened, then confirm.
              </p>
              <ul className="text-xs text-amber-100 list-disc ml-5 space-y-0.5">
                {needsInput.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            </div>
          )}

          {errorMessage && (
            <div className="mx-4 mb-3 flex items-start gap-2 rounded-xl border border-red-800/40 bg-red-950/40 p-3 text-xs text-red-300">
              <AlertTriangle size={14} className="shrink-0 mt-0.5" /> {errorMessage}
            </div>
          )}
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
            {loading ? "Submitting..." : errorMessage ? "Try Again" : "Confirm & Submit"}
          </button>
        </div>
      </div>
    </div>
  );
}
