import type { UserProfile, Application } from "./types";

const RESUME_KEY = "jaa_resume";
const PROFILE_KEY = "jaa_profile";
const APPS_KEY = "jaa_applications";

export const getResume = (): string =>
  typeof window !== "undefined" ? localStorage.getItem(RESUME_KEY) ?? "" : "";

export const saveResume = (text: string) =>
  localStorage.setItem(RESUME_KEY, text);

export const getProfile = (): UserProfile | null => {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(PROFILE_KEY);
  return raw ? JSON.parse(raw) : null;
};

export const saveProfile = (p: UserProfile) =>
  localStorage.setItem(PROFILE_KEY, JSON.stringify(p));

export const getApplications = (): Application[] => {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(APPS_KEY);
  return raw ? JSON.parse(raw) : [];
};

export const addApplication = (app: Omit<Application, "id" | "date" | "status">) => {
  const apps = getApplications();
  apps.unshift({
    ...app,
    id: crypto.randomUUID(),
    date: new Date().toLocaleDateString("en-IN"),
    status: "Applied",
  });
  localStorage.setItem(APPS_KEY, JSON.stringify(apps));
};

export const updateApplicationStatus = (id: string, status: Application["status"]) => {
  const apps = getApplications().map((a) => (a.id === id ? { ...a, status } : a));
  localStorage.setItem(APPS_KEY, JSON.stringify(apps));
};
