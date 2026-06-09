"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Briefcase, User, BarChart2, Zap } from "lucide-react";

const links = [
  { href: "/", icon: Zap, label: "Apply" },
  { href: "/profile", icon: User, label: "Profile" },
  { href: "/tracker", icon: BarChart2, label: "Tracker" },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-16 md:w-56 flex flex-col shrink-0 border-r border-white/5 bg-[#0d0d16]">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-white/5">
        <div className="w-8 h-8 rounded-lg btn-glow flex items-center justify-center shrink-0">
          <Briefcase size={15} className="text-white" />
        </div>
        <span className="hidden md:block text-sm font-semibold text-white tracking-wide">
          ApplyBot
        </span>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1 p-2 mt-2">
        {links.map(({ href, icon: Icon, label }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                active
                  ? "bg-violet-600/20 text-violet-300 border border-violet-500/30"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <Icon size={17} />
              <span className="hidden md:block">{label}</span>
            </Link>
          );
        })}
      </nav>

    </aside>
  );
}
