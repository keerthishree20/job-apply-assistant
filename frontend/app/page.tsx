"use client";
import { useState, useRef } from "react";
import { Loader2, Link2, Upload, Send, AlertTriangle, FileText, X, CheckCircle } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import ResultTabs from "@/components/ResultTabs";
import DownloadPanel from "@/components/DownloadPanel";
import ApplyConfirmModal from "@/components/ApplyConfirmModal";
import { getProfile, addApplication } from "@/lib/localStorage";
import { parseResume, scrapeJob, generateContent, answerQuestions, applyPreview, applyConfirm } from "@/lib/api";
import type { GenerateResult, QAItem } from "@/lib/types";

type Step = 0 | 1 | 2 | 3;

const SCREENING_QUESTIONS = [
  "Why do you want to work here?",
  "Describe your experience with the primary tech stack.",
  "What is your notice period?",
  "What is your expected salary?",
];

export default function ApplyPage() {
  const [step, setStep]               = useState<Step>(0);
  const [pdfFile, setPdfFile]         = useState<File | null>(null);
  const [originalResume, setOriginal] = useState("");
  const [parsedResume, setParsed]     = useState("");
  const [parsing, setParsing]         = useState(false);
  const [jobUrl, setJobUrl]           = useState("");
  const [manualJD, setManualJD]       = useState("");
  const [showManual, setShowManual]   = useState(false);
  const [jobMeta, setJobMeta]         = useState({ title: "", company: "", jd: "" });
  const [result, setResult]           = useState<GenerateResult | null>(null);
  const [qaItems, setQaItems]         = useState<QAItem[]>([]);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");
  const [preview, setPreview]         = useState<{ screenshot: string; fields: string[]; session: string } | null>(null);
  const [confirming, setConfirming]   = useState(false);
  const [success, setSuccess]         = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handlePdfUpload = async (file: File) => {
    setPdfFile(file);
    setParsing(true);
    setError("");
    try {
      const { text } = await parseResume(file);
      setOriginal(text);
      setParsed(text);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to read PDF.");
      setPdfFile(null);
    } finally {
      setParsing(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file?.type === "application/pdf") handlePdfUpload(file);
  };

  const handleGenerate = async () => {
    if (!parsedResume.trim()) { setError("Please upload your resume PDF first."); return; }
    if (!jobUrl.trim() && !manualJD.trim()) { setError("Please enter a job URL or paste the job description."); return; }
    setError("");
    setLoading(true);
    setStep(1);

    try {
      let jd = manualJD;
      let title = "";
      let company = "";

      if (jobUrl && !showManual) {
        const scraped = await scrapeJob(jobUrl) as { job_title?: string; company?: string; job_description?: string; error?: string; message?: string };
        if (scraped.error) {
          setShowManual(true);
          setError(scraped.message ?? "Could not scrape. Please paste JD manually.");
          setStep(0); setLoading(false); return;
        }
        jd = scraped.job_description ?? "";
        title = scraped.job_title ?? "";
        company = scraped.company ?? "";
      }

      setJobMeta({ title, company, jd });

      const [gen, qa] = await Promise.all([
        generateContent({ base_resume: parsedResume, job_description: jd, job_title: title, company }) as Promise<GenerateResult>,
        answerQuestions({ tailored_resume: parsedResume, job_title: title, company, job_description: jd, questions: SCREENING_QUESTIONS }) as Promise<{ answers: QAItem[] }>,
      ]);

      setResult(gen);
      setQaItems(qa.answers ?? []);
      setStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setStep(0);
    } finally {
      setLoading(false);
    }
  };

  const handleEasyApply = async () => {
    if (!result) return;
    const profile = getProfile();
    if (!profile) { setError("Please fill your profile first (Profile tab)."); return; }
    setLoading(true); setError("");
    try {
      const prev = await applyPreview({
        job_url: jobUrl,
        resume_pdf_base64: btoa(String.fromCharCode(...new TextEncoder().encode(result.tailored_resume))),
        profile,
        screening_answers: qaItems,
      }) as { screenshot_base64: string; fields_filled: string[]; session_id: string };
      setPreview({ screenshot: prev.screenshot_base64, fields: prev.fields_filled, session: prev.session_id });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Bot failed to open form.");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview) return;
    setConfirming(true);
    try {
      await applyConfirm(preview.session);
      addApplication({ company: jobMeta.company, role: jobMeta.title, url: jobUrl });
      setPreview(null); setSuccess(true); setStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Submit failed.");
    } finally {
      setConfirming(false);
    }
  };

  const resetAll = () => {
    setSuccess(false); setStep(0); setResult(null);
    setJobUrl(""); setManualJD(""); setJobMeta({ title: "", company: "", jd: "" });
    setPdfFile(null); setOriginal(""); setParsed("");
  };

  return (
    <div className="max-w-3xl mx-auto fade-up">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Job Apply Assistant</h1>
        <p className="text-sm text-slate-400 mt-1">Upload resume → paste job URL → AI tailors + applies</p>
      </div>

      <StepIndicator current={step} />

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 bg-red-950/40 border border-red-800/40 rounded-xl p-3 mb-5 text-sm text-red-300">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" /> {error}
        </div>
      )}

      {/* SUCCESS */}
      {success && (
        <div className="card p-8 text-center fade-up">
          <div className="text-5xl mb-4">🎉</div>
          <h2 className="text-xl font-bold text-white mb-2">Application Submitted!</h2>
          <p className="text-slate-400 text-sm mb-4">Logged to your tracker automatically.</p>
          <button onClick={resetAll} className="btn-glow px-6 py-2.5 rounded-xl text-white text-sm font-semibold">
            Apply to Another Job
          </button>
        </div>
      )}

      {!success && (
        <div className="flex flex-col gap-5">

          {/* PDF Upload */}
          <div className="card p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-3">
              <Upload size={15} className="text-violet-400" /> Upload Resume PDF
            </label>

            {!pdfFile ? (
              <div
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center cursor-pointer hover:border-violet-500/50 hover:bg-violet-950/10 transition-all"
              >
                {parsing ? (
                  <div className="flex flex-col items-center gap-2">
                    <Loader2 size={24} className="animate-spin text-violet-400" />
                    <p className="text-sm text-slate-400">Reading your PDF...</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <FileText size={28} className="text-slate-600" />
                    <p className="text-sm text-white font-medium">Drop your resume PDF here</p>
                    <p className="text-xs text-slate-500">or click to browse</p>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) handlePdfUpload(f); }}
                />
              </div>
            ) : (
              <div className="flex items-center gap-3 bg-green-950/30 border border-green-800/40 rounded-xl p-3">
                <CheckCircle size={18} className="text-green-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate">{pdfFile.name}</p>
                  <p className="text-xs text-slate-500">{Math.round(pdfFile.size / 1024)} KB · Resume extracted successfully</p>
                </div>
                <button onClick={() => { setPdfFile(null); setOriginal(""); setParsed(""); }}
                  className="text-slate-500 hover:text-white transition">
                  <X size={16} />
                </button>
              </div>
            )}
          </div>

          {/* Job URL */}
          <div className="card p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-3">
              <Link2 size={15} className="text-violet-400" /> Job URL
            </label>
            <input
              type="url"
              className="w-full px-3 py-2.5 text-sm"
              placeholder="https://linkedin.com/jobs/view/... or naukri.com, indeed.com..."
              value={jobUrl}
              onChange={(e) => setJobUrl(e.target.value)}
            />
            <button onClick={() => setShowManual(!showManual)}
              className="text-xs text-violet-400 mt-2 hover:text-violet-300 transition">
              {showManual ? "Hide manual input" : "URL not working? Paste JD manually →"}
            </button>
            {showManual && (
              <textarea
                className="w-full h-40 p-3 text-sm mt-3 resize-y"
                placeholder="Paste the full job description here..."
                value={manualJD}
                onChange={(e) => setManualJD(e.target.value)}
              />
            )}
          </div>

          {/* Generate */}
          {step < 2 && (
            <button onClick={handleGenerate} disabled={loading || parsing}
              className="btn-glow py-3 rounded-xl text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-50">
              {loading ? (
                <><Loader2 size={17} className="animate-spin" /> AI is tailoring your resume... (~10 sec)</>
              ) : (
                <><Send size={17} /> Generate Tailored Resume &amp; Cover Letter</>
              )}
            </button>
          )}

          {/* RESULT */}
          {step >= 2 && result && (
            <div className="card p-5 fade-up">
              {/* Job badge */}
              {jobMeta.title && (
                <div className="flex items-center gap-3 mb-4 pb-4 border-b border-white/8">
                  <div className="w-9 h-9 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-sm font-bold text-violet-300">
                    {jobMeta.company?.[0] ?? "J"}
                  </div>
                  <div>
                    <p className="text-white font-medium text-sm">{jobMeta.title}</p>
                    <p className="text-slate-400 text-xs">{jobMeta.company}</p>
                  </div>
                </div>
              )}

              <ResultTabs
                result={result}
                originalResume={originalResume}
                qaItems={qaItems}
                onResumeChange={(v) => setResult({ ...result, tailored_resume: v })}
                onCoverChange={(v) => setResult({ ...result, cover_letter: v })}
              />

              <div className="flex flex-col sm:flex-row gap-3 mt-5 pt-4 border-t border-white/8">
                <DownloadPanel resume={result.tailored_resume} coverLetter={result.cover_letter} />
                <button onClick={handleEasyApply} disabled={loading}
                  className="btn-glow px-5 py-2.5 rounded-xl text-white text-sm font-semibold flex items-center gap-2 ml-auto">
                  {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                  Easy Apply
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {preview && (
        <ApplyConfirmModal
          screenshotB64={preview.screenshot}
          fieldsFilled={preview.fields}
          onConfirm={handleConfirm}
          onCancel={() => setPreview(null)}
          loading={confirming}
        />
      )}
    </div>
  );
}
