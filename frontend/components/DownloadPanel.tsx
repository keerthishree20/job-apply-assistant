"use client";
import { Download } from "lucide-react";

function printContent(title: string, content: string) {
  const win = window.open("", "_blank");
  if (!win) return;
  win.document.write(`<!DOCTYPE html>
<html>
<head>
  <title>${title}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Times New Roman', serif;
      font-size: 12pt;
      line-height: 1.6;
      color: #111;
      padding: 20mm 25mm;
      background: white;
    }
    pre {
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: inherit;
      font-size: inherit;
      line-height: inherit;
    }
    @media print {
      body { padding: 0; }
      @page { margin: 20mm 25mm; }
    }
  </style>
</head>
<body>
  <pre>${content.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>
  <script>
    window.onload = function() {
      window.print();
      setTimeout(() => window.close(), 500);
    }
  </script>
</body>
</html>`);
  win.document.close();
}

interface Props {
  resume: string;
  coverLetter: string;
}

export default function DownloadPanel({ resume, coverLetter }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      <button
        onClick={() => printContent("Tailored Resume", resume)}
        className="flex items-center gap-2 px-4 py-2 rounded-xl border border-violet-500/30 text-violet-300 text-sm hover:bg-violet-600/10 transition"
      >
        <Download size={14} /> Resume PDF
      </button>
      <button
        onClick={() => printContent("Cover Letter", coverLetter)}
        className="flex items-center gap-2 px-4 py-2 rounded-xl border border-violet-500/30 text-violet-300 text-sm hover:bg-violet-600/10 transition"
      >
        <Download size={14} /> Cover Letter PDF
      </button>
    </div>
  );
}
