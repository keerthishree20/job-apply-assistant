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
  /** Set by the backend for legal / personal-status questions the candidate
   *  must answer themselves — a guessed answer would misrepresent them. */
  needs_review?: boolean;
}

export interface ApplyPreview {
  status: string;
  screenshot_base64: string;
  fields_filled: string[];
  /** Left blank on purpose — legal/personal-status questions, required fields
   *  with no data. The candidate answers these in the bot's browser window. */
  needs_input: string[];
  session_id: string;
}

export interface ApplyConfirmResult {
  /** submitted: the site confirmed it. failed: the form showed errors, session
   *  still open. unconfirmed: no confirmation seen, not logged. */
  status: "submitted" | "failed" | "unconfirmed";
  message: string;
  session_open: boolean;
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
