const STEPS = ["Input", "Generate", "Review", "Apply"];

export default function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {STEPS.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <div key={i} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div
                className={`relative w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  done
                    ? "bg-violet-600 text-white"
                    : active
                    ? "bg-violet-600 text-white step-active"
                    : "bg-white/5 text-slate-500 border border-white/10"
                }`}
              >
                {done ? "✓" : i + 1}
              </div>
              <span
                className={`text-[10px] font-medium hidden sm:block ${
                  active ? "text-violet-300" : done ? "text-slate-400" : "text-slate-600"
                }`}
              >
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={`h-px w-12 sm:w-20 mx-1 mb-4 transition-all ${
                  done ? "bg-violet-600" : "bg-white/8"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
