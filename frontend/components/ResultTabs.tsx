"use client";
import { useState } from "react";
import DiffHighlight from "./DiffHighlight";
import type { GenerateResult, QAItem } from "@/lib/types";

interface Props {
  result: GenerateResult;
  qaItems: QAItem[];
  onResumeChange: (v: string) => void;
  onCoverChange: (v: string) => void;
}

const TABS = ["Resume", "Cover Letter", "Screening Q&A", "Changes"] as const;

export default function ResultTabs({ result, qaItems, onResumeChange, onCoverChange }: Props) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Resume");

  return (
    <div className="fade-up">
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-white/8 mb-4">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              tab === t ? "tab-active text-white" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t}
            {t === "Changes" && result.keywords_added.length > 0 && (
              <span className="ml-1.5 text-[10px] bg-violet-600 text-white px-1.5 py-0.5 rounded-full">
                {result.keywords_added.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Resume */}
      {tab === "Resume" && (
        <div id="resume-print-area">
          <textarea
            className="w-full h-96 p-4 text-sm font-mono resize-y"
            value={result.tailored_resume}
            onChange={(e) => onResumeChange(e.target.value)}
          />
          <p className="text-xs text-slate-500 mt-2">
            Green highlights = keywords added by AI. Edit freely before applying.
          </p>
        </div>
      )}

      {/* Cover Letter */}
      {tab === "Cover Letter" && (
        <div id="cover-print-area">
          <textarea
            className="w-full h-64 p-4 text-sm resize-y"
            value={result.cover_letter}
            onChange={(e) => onCoverChange(e.target.value)}
          />
          <p className="text-xs text-slate-500 mt-2">{result.cover_letter.split(" ").length} words</p>
        </div>
      )}

      {/* Q&A */}
      {tab === "Screening Q&A" && (
        <div className="flex flex-col gap-3">
          {qaItems.length === 0 && (
            <p className="text-sm text-slate-500">No screening questions detected for this job.</p>
          )}
          {qaItems.map((qa, i) => (
            <div key={i} className="card p-4">
              <p className="text-xs text-violet-400 font-medium mb-1">Q: {qa.question}</p>
              <p className="text-sm text-slate-300">{qa.answer}</p>
            </div>
          ))}
        </div>
      )}

      {/* Changes */}
      {tab === "Changes" && (
        <div>
          <div className="mb-4 flex gap-2 flex-wrap">
            {result.keywords_added.map((kw, i) => (
              <span key={i} className="diff-add text-xs px-2 py-1 rounded-full">{kw}</span>
            ))}
          </div>
          <DiffHighlight text={result.tailored_resume} keywords={result.keywords_added} />
        </div>
      )}
    </div>
  );
}
