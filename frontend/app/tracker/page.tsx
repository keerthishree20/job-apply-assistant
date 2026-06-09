"use client";
import { useState, useEffect } from "react";
import { Download, ExternalLink, BarChart2 } from "lucide-react";
import { getApplications, updateApplicationStatus } from "@/lib/localStorage";
import { exportTracker } from "@/lib/api";
import type { Application } from "@/lib/types";

const COLUMNS: Application["status"][] = ["Applied", "Interviewing", "Offer", "Rejected"];

const COL_STYLE: Record<Application["status"], string> = {
  Applied:      "border-blue-500/30 bg-blue-950/20",
  Interviewing: "border-yellow-500/30 bg-yellow-950/20",
  Offer:        "border-green-500/30 bg-green-950/20",
  Rejected:     "border-red-500/30 bg-red-950/20",
};
const DOT: Record<Application["status"], string> = {
  Applied:      "bg-blue-400",
  Interviewing: "bg-yellow-400",
  Offer:        "bg-green-400",
  Rejected:     "bg-red-400",
};

export default function TrackerPage() {
  const [apps, setApps] = useState<Application[]>([]);

  useEffect(() => { setApps(getApplications()); }, []);

  const move = (id: string, status: Application["status"]) => {
    updateApplicationStatus(id, status);
    setApps(getApplications());
  };

  const handleExport = async () => {
    const blob = await exportTracker();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "jobs_applied.xlsx"; a.click();
  };

  return (
    <div className="fade-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart2 size={20} className="text-violet-400" /> Application Tracker
          </h1>
          <p className="text-sm text-slate-400 mt-1">{apps.length} total applications</p>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-violet-500/30 text-violet-300 text-sm hover:bg-violet-600/10 transition"
        >
          <Download size={14} /> Export Excel
        </button>
      </div>

      {apps.length === 0 && (
        <div className="card p-12 text-center">
          <p className="text-3xl mb-3">📋</p>
          <p className="text-white font-medium">No applications yet</p>
          <p className="text-slate-400 text-sm mt-1">Go to Apply tab and submit your first application!</p>
        </div>
      )}

      {/* Kanban */}
      {apps.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {COLUMNS.map((col) => {
            const colApps = apps.filter((a) => a.status === col);
            return (
              <div key={col} className={`rounded-xl border p-3 ${COL_STYLE[col]}`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={`w-2 h-2 rounded-full ${DOT[col]}`} />
                  <span className="text-sm font-semibold text-white">{col}</span>
                  <span className="ml-auto text-xs text-slate-500">{colApps.length}</span>
                </div>
                <div className="flex flex-col gap-2">
                  {colApps.map((app) => (
                    <div key={app.id} className="card p-3 group">
                      <p className="text-sm font-medium text-white truncate">{app.company || "Company"}</p>
                      <p className="text-xs text-slate-400 truncate">{app.role || "Role"}</p>
                      <p className="text-[11px] text-slate-600 mt-1">{app.date}</p>
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {COLUMNS.filter((c) => c !== col).map((c) => (
                          <button
                            key={c}
                            onClick={() => move(app.id, c)}
                            className="text-[10px] px-2 py-0.5 rounded-full border border-white/10 text-slate-500 hover:text-white hover:border-white/30 transition"
                          >
                            → {c}
                          </button>
                        ))}
                        {app.url && (
                          <a href={app.url} target="_blank" rel="noopener noreferrer"
                            className="text-[10px] px-2 py-0.5 rounded-full border border-white/10 text-slate-500 hover:text-violet-400 transition ml-auto">
                            <ExternalLink size={10} />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                  {colApps.length === 0 && (
                    <p className="text-xs text-slate-600 text-center py-4">Empty</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
