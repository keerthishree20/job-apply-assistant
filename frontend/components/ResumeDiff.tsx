"use client";

interface Props {
  original: string;
  tailored: string;
}

type LineType = "same" | "added" | "removed";
interface DiffLine { type: LineType; text: string; }

function computeDiff(original: string, tailored: string): DiffLine[] {
  const origLines = original.split("\n");
  const newLines  = tailored.split("\n");
  const result: DiffLine[] = [];

  const origSet = new Set(origLines.map(l => l.trim()).filter(Boolean));
  const newSet  = new Set(newLines.map(l => l.trim()).filter(Boolean));

  // Show tailored (new) lines with added/same markers
  for (const line of newLines) {
    const trimmed = line.trim();
    if (!trimmed) { result.push({ type: "same", text: "" }); continue; }
    const wasInOriginal = origLines.some(ol => ol.trim() === trimmed);
    result.push({ type: wasInOriginal ? "same" : "added", text: line });
  }

  // Show lines removed from original
  for (const line of origLines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const stillPresent = newLines.some(nl => nl.trim() === trimmed);
    if (!stillPresent) {
      result.push({ type: "removed", text: line });
    }
  }

  return result;
}

export default function ResumeDiff({ original, tailored }: Props) {
  const diff = computeDiff(original, tailored);
  const added   = diff.filter(d => d.type === "added").length;
  const removed = diff.filter(d => d.type === "removed").length;

  return (
    <div>
      {/* Stats */}
      <div className="flex gap-3 mb-3 text-xs">
        <span className="flex items-center gap-1.5 bg-green-900/30 text-green-400 border border-green-800/40 px-2.5 py-1 rounded-full">
          <span className="font-bold">+{added}</span> lines improved
        </span>
        <span className="flex items-center gap-1.5 bg-red-900/30 text-red-400 border border-red-800/40 px-2.5 py-1 rounded-full">
          <span className="font-bold">−{removed}</span> lines replaced
        </span>
      </div>

      {/* Diff view */}
      <div className="rounded-xl border border-white/8 overflow-hidden font-mono text-xs leading-6 max-h-[480px] overflow-y-auto">
        {diff.map((line, i) => (
          <div
            key={i}
            className={`flex gap-3 px-4 py-0.5 ${
              line.type === "added"
                ? "bg-green-950/40 border-l-2 border-green-500"
                : line.type === "removed"
                ? "bg-red-950/40 border-l-2 border-red-500 line-through opacity-60"
                : "bg-transparent border-l-2 border-transparent"
            }`}
          >
            <span className={`select-none w-4 shrink-0 ${
              line.type === "added" ? "text-green-500" :
              line.type === "removed" ? "text-red-500" : "text-slate-700"
            }`}>
              {line.type === "added" ? "+" : line.type === "removed" ? "−" : " "}
            </span>
            <span className={
              line.type === "added" ? "text-green-300" :
              line.type === "removed" ? "text-red-400" : "text-slate-400"
            }>
              {line.text || " "}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
