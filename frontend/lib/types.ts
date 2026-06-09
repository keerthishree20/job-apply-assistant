export interface UserProfile {
  name: string;
  email: string;
  phone: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
  college: string;
  graduation_year: string;
}

export interface DiffChange {
  type: "added" | "reworded" | "removed";
  phrase?: string;
  original?: string;
  new?: string;
}

export interface QAItem {
  question: string;
  answer: string;
}

export interface GenerateResult {
  tailored_resume: string;
  cover_letter: string;
  keywords_added: string[];
  diff: DiffChange[];
}

export interface ScrapeResult {
  job_title: string;
  company: string;
  job_description: string;
  source: string;
  error?: string;
  message?: string;
}

export interface Application {
  id: string;
  company: string;
  role: string;
  url: string;
  date: string;
  status: "Applied" | "Interviewing" | "Offer" | "Rejected";
}
