"use client";
import dynamic from "next/dynamic";
import { Download } from "lucide-react";

export default function DownloadPanel({ coverLetter }: { coverLetter: string }) {
  const downloadResume = async () => {
    const html2pdf = (await import("html2pdf.js" as never) as { default: Function }).default;
    const el = document.getElementById("resume-print-area");
    if (!el) return;
    html2pdf().set({
      margin: [10, 12],
      filename: "tailored_resume.pdf",
      html2canvas: { scale: 2 },
      jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
    }).from(el).save();
  };

  const downloadCover = async () => {
    const html2pdf = (await import("html2pdf.js" as never) as { default: Function }).default;
    const el = document.getElementById("cover-print-area");
    if (!el) return;
    html2pdf().set({
      margin: [15, 20],
      filename: "cover_letter.pdf",
      html2canvas: { scale: 2 },
      jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
    }).from(el).save();
  };

  return (
    <div className="flex gap-2 flex-wrap">
      <button
        onClick={downloadResume}
        className="flex items-center gap-2 px-4 py-2 rounded-xl border border-violet-500/30 text-violet-300 text-sm hover:bg-violet-600/10 transition"
      >
        <Download size={14} /> Resume PDF
      </button>
      <button
        onClick={downloadCover}
        className="flex items-center gap-2 px-4 py-2 rounded-xl border border-violet-500/30 text-violet-300 text-sm hover:bg-violet-600/10 transition"
      >
        <Download size={14} /> Cover Letter PDF
      </button>
    </div>
  );
}
