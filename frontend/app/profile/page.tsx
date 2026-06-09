"use client";
import { useState, useEffect } from "react";
import { Save, User, CheckCircle } from "lucide-react";
import { getProfile, saveProfile } from "@/lib/localStorage";
import type { UserProfile } from "@/lib/types";

const EMPTY: UserProfile = {
  name: "", email: "", phone: "",
  linkedin_url: "", github_url: "", portfolio_url: "",
  college: "", graduation_year: "",
};

const fields: { key: keyof UserProfile; label: string; type?: string; placeholder: string }[] = [
  { key: "name",            label: "Full Name",        placeholder: "KeerthiShree TS" },
  { key: "email",           label: "Email",            type: "email", placeholder: "keerthishreets@gmail.com" },
  { key: "phone",           label: "Phone",            type: "tel",   placeholder: "+91 9876543210" },
  { key: "linkedin_url",    label: "LinkedIn URL",     type: "url",   placeholder: "https://linkedin.com/in/..." },
  { key: "github_url",      label: "GitHub URL",       type: "url",   placeholder: "https://github.com/..." },
  { key: "portfolio_url",   label: "Portfolio / Website", type: "url", placeholder: "https://..." },
  { key: "college",         label: "College",          placeholder: "SNS College of Technology" },
  { key: "graduation_year", label: "Graduation Year",  placeholder: "2026" },
];

export default function ProfilePage() {
  const [form, setForm] = useState<UserProfile>(EMPTY);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const p = getProfile();
    if (p) setForm(p);
  }, []);

  const set = (k: keyof UserProfile, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const handleSave = () => {
    saveProfile(form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-xl mx-auto fade-up">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <User size={20} className="text-violet-400" /> Your Profile
        </h1>
        <p className="text-sm text-slate-400 mt-1">Fill once — bot uses this to auto-fill application forms.</p>
      </div>

      <div className="card p-6 flex flex-col gap-4">
        {fields.map(({ key, label, type, placeholder }) => (
          <div key={key}>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">{label}</label>
            <input
              type={type ?? "text"}
              className="w-full px-3 py-2.5 text-sm"
              placeholder={placeholder}
              value={form[key]}
              onChange={(e) => set(key, e.target.value)}
            />
          </div>
        ))}

        <button
          onClick={handleSave}
          className="btn-glow mt-2 py-3 rounded-xl text-white font-semibold flex items-center justify-center gap-2"
        >
          {saved ? <CheckCircle size={16} /> : <Save size={16} />}
          {saved ? "Saved!" : "Save Profile"}
        </button>
      </div>
    </div>
  );
}
