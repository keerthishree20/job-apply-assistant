"use client";
import { useState } from "react";
import ResumeDiff from "./ResumeDiff";
import type { GenerateResult, QAItem } from "@/lib/types";

interface Props {
  result: GenerateResult;
  originalResume: string;
  qaItems: QAItem[];
  onResumeChange: (v: string) => void;
  onCoverChange: (v: string) => void;
}

const TABS = ["Tailored Resume", "Diff View", "Cover Letter", "Screening Q&A"] as const;

export default function ResultTabs({ result, originalResume, qaItems, onResumeChange, onCoverChange }: Props) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Tailored Resume");

  return (
    <div className="fade-up">
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-white/8 mb-4 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
              tab === t ? "tab-active text-white" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t}
            {t === "Diff View" && result.keywords_added.length > 0 && (
              <span className="ml-1.5 text-[10px] bg-violet-600 text-white px-1.5 py-0.5 rounded-full">
                {result.keywords_added.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tailored Resume — editable */}
      {tab === "Tailored Resume" && (
        <div id="resume-print-area">
          <p className="text-xs text-slate-500 mb-2">AI-tailored to the job. Edit freely before applying.</p>
          <textarea
            className="w-full h-96 p-4 text-sm font-mono resize-y"
            value={result.tailored_resume}
            onChange={(e) => onResumeChange(e.target.value)}
          />
        </div>
      )}

      {/* Diff View — original vs tailored */}
      {tab === "Diff View" && (
        <div>
          <p className="text-xs text-slate-500 mb-3">
            <span className="text-green-400 font-medium">Green +</span> lines are new/improved &nbsp;·&nbsp;
            <span className="text-red-400 font-medium">Red −</span> lines were replaced
          </p>
          <ResumeDiff original={originalResume} tailored={result.tailored_resume} />
        </div>
      )}

      {/* Cover Letter */}
      {tab === "Cover Letter" && (
        <div id="cover-print-area">
          <div className="flex justify-between items-center mb-2">
            <p className="text-xs text-slate-500">Edit if needed before downloading.</p>
            <span className="text-xs text-slate-600">{result.cover_letter.trim().split(/\s+/).length} words</span>
          </div>
          <textarea
            className="w-full h-64 p-4 text-sm resize-y leading-7"
            value={result.cover_letter}
            onChange={(e) => onCoverChange(e.target.value)}
          />
        </div>
      )}

      {/* Screening Q&A */}
      {tab === "Screening Q&A" && (
        <div className="flex flex-col gap-3">
          {qaItems.length === 0 && (
            <p className="text-sm text-slate-500">No screening questions for this job.</p>
          )}
          {qaItems.map((qa, i) => (
            <div key={i} className="card p-4">
              <p className="text-xs text-violet-400 font-medium mb-1">Q: {qa.question}</p>
              <p className="text-sm text-slate-300 leading-6">{qa.answer}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
