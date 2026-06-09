"use client";
import { useState, useEffect, useRef } from "react";
import { Loader2, Link2, FileText, Send, AlertTriangle } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import ResultTabs from "@/components/ResultTabs";
import DownloadPanel from "@/components/DownloadPanel";
import ApplyConfirmModal from "@/components/ApplyConfirmModal";
import { getResume, saveResume, getProfile } from "@/lib/localStorage";
import { scrapeJob, generateContent, answerQuestions, applyPreview, applyConfirm } from "@/lib/api";
import type { GenerateResult, QAItem } from "@/lib/types";
import { addApplication } from "@/lib/localStorage";

type Step = 0 | 1 | 2 | 3;

const SCREENING_QUESTIONS = [
  "Why do you want to work here?",
  "Describe your experience with the primary tech stack.",
  "What is your notice period?",
  "What is your expected salary?",
];

export default function ApplyPage() {
  const [step, setStep] = useState<Step>(0);
  const [resume, setResume] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [manualJD, setManualJD] = useState("");
  const [showManual, setShowManual] = useState(false);
  const [jobMeta, setJobMeta] = useState({ title: "", company: "", jd: "" });
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [qaItems, setQaItems] = useState<QAItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<{ screenshot: string; fields: string[]; session: string } | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setResume(getResume());
  }, []);

  const handleResumeChange = (v: string) => {
    setResume(v);
    saveResume(v);
  };

  const handleGenerate = async () => {
    if (!resume.trim()) { setError("Please paste your resume first."); return; }
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
          setStep(0);
          setLoading(false);
          return;
        }
        jd = scraped.job_description ?? "";
        title = scraped.job_title ?? "";
        company = scraped.company ?? "";
      }

      setJobMeta({ title, company, jd });

      const [gen, qa] = await Promise.all([
        generateContent({ base_resume: resume, job_description: jd, job_title: title, company }) as Promise<GenerateResult>,
        answerQuestions({ tailored_resume: resume, job_title: title, company, job_description: jd, questions: SCREENING_QUESTIONS }) as Promise<{ answers: QAItem[] }>,
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
    if (!profile) {
      setError("Please fill your profile first (Profile tab).");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const prev = await applyPreview({
        job_url: jobUrl,
        resume_pdf_base64: btoa(result.tailored_resume),
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
      setPreview(null);
      setSuccess(true);
      setStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Submit failed.");
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto fade-up">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Job Apply Assistant</h1>
        <p className="text-sm text-slate-400 mt-1">Paste URL → AI tailors your resume → One-click apply</p>
      </div>

      <StepIndicator current={step} />

      {/* Error banner */}
      {error && (
        <div className="flex items-start gap-3 bg-red-950/40 border border-red-800/40 rounded-xl p-3 mb-5 text-sm text-red-300">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* SUCCESS */}
      {success && (
        <div className="card p-8 text-center fade-up">
          <div className="text-5xl mb-4">🎉</div>
          <h2 className="text-xl font-bold text-white mb-2">Application Submitted!</h2>
          <p className="text-slate-400 text-sm mb-4">Logged to your tracker automatically.</p>
          <button
            onClick={() => { setSuccess(false); setStep(0); setResult(null); setJobUrl(""); setManualJD(""); setJobMeta({ title:"", company:"", jd:"" }); }}
            className="btn-glow px-6 py-2.5 rounded-xl text-white text-sm font-semibold"
          >
            Apply to Another Job
          </button>
        </div>
      )}

      {/* STEP 0 — Input */}
      {!success && (
        <div className="flex flex-col gap-5">
          {/* Resume */}
          <div className="card p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-3">
              <FileText size={15} className="text-violet-400" /> Your Base Resume
            </label>
            <textarea
              className="w-full h-48 p-3 text-sm font-mono resize-y"
              placeholder="Paste your resume here... (saved automatically)"
              value={resume}
              onChange={(e) => handleResumeChange(e.target.value)}
            />
          </div>

          {/* Job URL */}
          <div className="card p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-3">
              <Link2 size={15} className="text-violet-400" /> Job URL
            </label>
            <input
              type="url"
              className="w-full px-3 py-2.5 text-sm"
              placeholder="https://linkedin.com/jobs/view/... or indeed.com, naukri.com..."
              value={jobUrl}
              onChange={(e) => setJobUrl(e.target.value)}
            />
            <button
              onClick={() => setShowManual(!showManual)}
              className="text-xs text-violet-400 mt-2 hover:text-violet-300 transition"
            >
              {showManual ? "Hide manual input" : "URL blocked? Paste JD manually →"}
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

          {/* Generate button */}
          {step < 2 && (
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="btn-glow py-3 rounded-xl text-white font-semibold flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={17} className="animate-spin" />
                  AI is working... (~8 sec)
                </>
              ) : (
                <>
                  <Send size={17} />
                  Generate & Tailor Resume
                </>
              )}
            </button>
          )}

          {/* STEP 2 — Result */}
          {step >= 2 && result && (
            <div className="card p-5 fade-up">
              {/* Job info */}
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
                qaItems={qaItems}
                onResumeChange={(v) => setResult({ ...result, tailored_resume: v })}
                onCoverChange={(v) => setResult({ ...result, cover_letter: v })}
              />

              <div className="flex flex-col sm:flex-row gap-3 mt-5 pt-4 border-t border-white/8">
                <DownloadPanel coverLetter={result.cover_letter} />
                <button
                  onClick={handleEasyApply}
                  disabled={loading}
                  className="btn-glow px-5 py-2.5 rounded-xl text-white text-sm font-semibold flex items-center gap-2 ml-auto"
                >
                  {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                  Easy Apply
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Preview modal */}
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
