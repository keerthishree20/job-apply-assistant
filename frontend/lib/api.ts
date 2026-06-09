const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export const scrapeJob = (url: string) =>
  post("/api/scrape", { url });

export const generateContent = (body: {
  base_resume: string;
  job_description: string;
  job_title: string;
  company: string;
}) => post("/api/generate", body);

export const answerQuestions = (body: {
  tailored_resume: string;
  job_title: string;
  company: string;
  job_description: string;
  questions: string[];
}) => post("/api/answers", body);

export const applyPreview = (body: {
  job_url: string;
  resume_pdf_base64: string;
  profile: object;
  screening_answers: object[];
}) => post("/api/apply", body);

export const applyConfirm = (session_id: string) =>
  post("/api/apply/confirm", { session_id });

export const exportTracker = () =>
  fetch(`${BASE}/api/tracker/export`).then((r) => r.blob());
