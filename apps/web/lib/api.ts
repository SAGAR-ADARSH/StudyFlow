// StudyFlow API Client Library

// Relative by default so the browser only ever talks to its own origin; the Next.js
// server proxies /api/v1 to the FastAPI backend (see next.config.ts). Set
// NEXT_PUBLIC_API_URL to call the API directly instead.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export interface User {
  id: number;
  email: string;
  display_name: string;
  college_name?: string | null;
  course_name?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user?: User;
}

export interface Semester {
  id: number;
  user_id: number;
  name: string;
  semester_number?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
  subjects_count?: number;
  exams_count?: number;
}

export interface Subject {
  id: number;
  user_id: number;
  semester_id: number;
  name: string;
  code?: string | null;
  color?: string | null;
  credits?: number;
  target_grade?: string | null;
  difficulty_level?: string;
  description?: string | null;
  created_at: string;
  updated_at?: string | null;
  semester_name?: string;
  topics_count?: number;
  completed_topics_count?: number;
  exams_count?: number;
}

export interface Topic {
  id: number;
  user_id: number;
  subject_id: number;
  name: string;
  description?: string | null;
  unit_number?: number;
  priority: "High" | "Medium" | "Low" | string;
  status: "Pending" | "In Progress" | "Completed" | string;
  estimated_hours?: number;
  completed_hours?: number;
  importance_score?: number;
  order_index?: number;
  created_at: string;
  updated_at?: string | null;
  subject_name?: string;
}

export interface Exam {
  id: number;
  user_id: number;
  semester_id?: number | null;
  subject_id: number;
  title: string;
  exam_type: string;
  exam_date: string;
  start_time?: string | null;
  duration_minutes?: number;
  total_marks?: number;
  passing_marks?: number;
  target_marks?: number | null;
  obtained_marks?: number | null;
  location?: string | null;
  notes?: string | null;
  status: "Upcoming" | "Completed" | "Cancelled" | string;
  created_at: string;
  updated_at?: string | null;
  subject_name?: string;
  semester_name?: string;
  days_remaining?: number;
}

export interface Note {
  id: number;
  user_id: number;
  subject_id: number | null;
  topic_id: number | null;
  title: string;
  content: string;
  tags: string[];
  is_pinned: boolean;
  created_at: string;
  updated_at?: string | null;
  subject_name?: string | null;
  topic_name?: string | null;
}

// Token management in localStorage
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("studyflow_token");
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("studyflow_token", token);
  }
}

export function clearToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("studyflow_token");
  }
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

// Generic Authenticated Fetch Helper
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    // Direct API deployments use Bearer; same-origin requests use a header
    // that hosted preview gateways do not consume. Our route translates it.
    if (API_BASE.startsWith("/")) headers["X-StudyFlow-Token"] = token;
    else headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(extractErrorMessage(data, response.status), response.status);
  }

  return data as T;
}

// Multipart uploads must not force a JSON content type, so they get their own helper.
async function requestForm<T>(endpoint: string, body: FormData): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    // Direct API deployments use Bearer; same-origin requests use a header
    // that hosted preview gateways do not consume. Our route translates it.
    if (API_BASE.startsWith("/")) headers["X-StudyFlow-Token"] = token;
    else headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers,
    body,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(extractErrorMessage(data, response.status), response.status);
  }
  return data as T;
}

function extractErrorMessage(data: unknown, status: number): string {
  if (data && typeof data === "object") {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object") {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string") return message;
      const code = (detail as { code?: unknown }).code;
      if (typeof code === "string") return code;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first?.msg === "string") return first.msg;
    }
  }
  return `Request failed with status ${status}`;
}

// ----------------------------------------------------------------------
// Authentication & User APIs
// ----------------------------------------------------------------------
export async function login(email: string, password: string): Promise<AuthResponse> {
  const result = await request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (result.access_token) {
    setToken(result.access_token);
  }
  return result;
}

export async function register(payload: {
  email: string;
  password: string;
  display_name: string;
  college_name?: string;
  course_name?: string;
}): Promise<AuthResponse> {
  const result = await request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (result.access_token) {
    setToken(result.access_token);
  }
  return result;
}

export async function getMe(): Promise<User> {
  return request<User>("/auth/me");
}

export async function updateProfile(payload: {
  display_name?: string;
  college_name?: string;
  course_name?: string;
}): Promise<User> {
  return request<User>("/users/me", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<AuthResponse> {
  const result = await request<AuthResponse>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (result.access_token) {
    setToken(result.access_token);
  }
  return result;
}

// ----------------------------------------------------------------------
// Semesters APIs
// ----------------------------------------------------------------------
export async function getSemesters(): Promise<Semester[]> {
  return request<Semester[]>("/semesters");
}

export async function getSemester(id: number): Promise<Semester> {
  return request<Semester>(`/semesters/${id}`);
}

export async function createSemester(payload: {
  name: string;
  semester_number?: number;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
}): Promise<Semester> {
  return request<Semester>("/semesters", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSemester(
  id: number,
  payload: {
    name?: string;
    semester_number?: number;
    start_date?: string;
    end_date?: string;
    is_active?: boolean;
  }
): Promise<Semester> {
  return request<Semester>(`/semesters/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteSemester(id: number): Promise<void> {
  return request<void>(`/semesters/${id}`, {
    method: "DELETE",
  });
}

export async function activateSemester(id: number): Promise<Semester> {
  return request<Semester>(`/semesters/${id}/activate`, {
    method: "POST",
  });
}

// ----------------------------------------------------------------------
// Subjects APIs
// ----------------------------------------------------------------------
export async function getSubjects(semesterId?: number): Promise<Subject[]> {
  const query = semesterId ? `?semester_id=${semesterId}` : "";
  return request<Subject[]>(`/subjects${query}`);
}

export async function getSubject(id: number): Promise<Subject> {
  return request<Subject>(`/subjects/${id}`);
}

export async function createSubject(payload: {
  semester_id: number;
  name: string;
  code?: string;
  color?: string;
  credits?: number;
  target_grade?: string;
  difficulty_level?: string;
  description?: string;
}): Promise<Subject> {
  return request<Subject>("/subjects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSubject(
  id: number,
  payload: {
    semester_id?: number;
    name?: string;
    code?: string;
    color?: string;
    credits?: number;
    target_grade?: string;
    difficulty_level?: string;
    description?: string;
  }
): Promise<Subject> {
  return request<Subject>(`/subjects/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteSubject(id: number): Promise<void> {
  return request<void>(`/subjects/${id}`, {
    method: "DELETE",
  });
}

// ----------------------------------------------------------------------
// Topics APIs
// ----------------------------------------------------------------------
export async function getTopics(
  subjectId?: number,
  status?: string
): Promise<Topic[]> {
  const params = new URLSearchParams();
  if (subjectId) params.append("subject_id", subjectId.toString());
  if (status) params.append("status", status);
  const query = params.toString() ? `?${params.toString()}` : "";
  return request<Topic[]>(`/topics${query}`);
}

export async function getTopic(id: number): Promise<Topic> {
  return request<Topic>(`/topics/${id}`);
}

export async function createTopic(payload: {
  subject_id: number;
  name: string;
  description?: string;
  unit_number?: number;
  priority?: string;
  status?: string;
  estimated_hours?: number;
  importance_score?: number;
  order_index?: number;
}): Promise<Topic> {
  return request<Topic>("/topics", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateTopic(
  id: number,
  payload: {
    name?: string;
    description?: string;
    unit_number?: number;
    priority?: string;
    status?: string;
    estimated_hours?: number;
    completed_hours?: number;
    importance_score?: number;
    order_index?: number;
  }
): Promise<Topic> {
  return request<Topic>(`/topics/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function updateTopicStatus(
  id: number,
  status: string,
  completedHours?: number
): Promise<Topic> {
  return request<Topic>(`/topics/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, completed_hours: completedHours }),
  });
}

export async function deleteTopic(id: number): Promise<void> {
  return request<void>(`/topics/${id}`, {
    method: "DELETE",
  });
}

// ----------------------------------------------------------------------
// Exams APIs
// ----------------------------------------------------------------------
export async function getExams(params?: {
  semester_id?: number;
  subject_id?: number;
  status?: string;
  upcoming?: boolean;
}): Promise<Exam[]> {
  const queryParams = new URLSearchParams();
  if (params?.semester_id) queryParams.append("semester_id", params.semester_id.toString());
  if (params?.subject_id) queryParams.append("subject_id", params.subject_id.toString());
  if (params?.status) queryParams.append("status", params.status);
  if (params?.upcoming) queryParams.append("upcoming", "true");
  const query = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return request<Exam[]>(`/exams${query}`);
}

export async function getExam(id: number): Promise<Exam> {
  return request<Exam>(`/exams/${id}`);
}

export async function createExam(payload: {
  subject_id: number;
  semester_id?: number;
  title: string;
  exam_type?: string;
  exam_date: string;
  start_time?: string;
  duration_minutes?: number;
  total_marks?: number;
  passing_marks?: number;
  target_marks?: number;
  location?: string;
  notes?: string;
  status?: string;
}): Promise<Exam> {
  return request<Exam>("/exams", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateExam(
  id: number,
  payload: {
    subject_id?: number;
    semester_id?: number;
    title?: string;
    exam_type?: string;
    exam_date?: string;
    start_time?: string;
    duration_minutes?: number;
    total_marks?: number;
    passing_marks?: number;
    target_marks?: number;
    obtained_marks?: number;
    location?: string;
    notes?: string;
    status?: string;
  }
): Promise<Exam> {
  return request<Exam>(`/exams/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteExam(id: number): Promise<void> {
  return request<void>(`/exams/${id}`, {
    method: "DELETE",
  });
}

// ----------------------------------------------------------------------
// Notes APIs
// ----------------------------------------------------------------------
export async function getNotes(params?: {
  q?: string;
  subject_id?: number;
  topic_id?: number;
  pinned?: boolean;
  limit?: number;
  offset?: number;
}): Promise<Note[]> {
  const queryParams = new URLSearchParams();
  if (params?.q) queryParams.append("q", params.q);
  if (params?.subject_id) queryParams.append("subject_id", params.subject_id.toString());
  if (params?.topic_id) queryParams.append("topic_id", params.topic_id.toString());
  if (params?.pinned !== undefined) queryParams.append("pinned", String(params.pinned));
  if (params?.limit) queryParams.append("limit", params.limit.toString());
  if (params?.offset) queryParams.append("offset", params.offset.toString());
  const query = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return request<Note[]>(`/notes${query}`);
}

export async function createNote(payload: {
  title: string;
  content: string;
  subject_id?: number | null;
  topic_id?: number | null;
  tags?: string[];
  is_pinned?: boolean;
}): Promise<Note> {
  return request<Note>("/notes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateNote(
  id: number,
  payload: {
    title?: string;
    content?: string;
    subject_id?: number | null;
    topic_id?: number | null;
    tags?: string[];
    is_pinned?: boolean;
  }
): Promise<Note> {
  return request<Note>(`/notes/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteNote(id: number): Promise<void> {
  return request<void>(`/notes/${id}`, {
    method: "DELETE",
  });
}

// ----------------------------------------------------------------------
// Documents (PDF uploads), summaries, and quizzes
// ----------------------------------------------------------------------
export type DocumentProcessingStatus = "pending" | "processing" | "completed" | "failed";

export interface StudyDocument {
  id: number;
  user_id: number;
  semester_id: number | null;
  subject_id: number | null;
  title: string;
  original_filename: string;
  file_size_bytes: number;
  page_count: number;
  processing_status: DocumentProcessingStatus;
  extracted_chars: number;
  word_count: number;
  text_truncated: boolean;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at?: string | null;
  subject_name?: string | null;
  semester_name?: string | null;
  summary_count: number;
  latest_summary_id: number | null;
  summary_updated_at?: string | null;
  quiz_count: number;
  latest_quiz_id: number | null;
}

export interface DocumentListResult {
  items: StudyDocument[];
  total: number;
  limit: number;
  offset: number;
}

export interface DocumentText {
  document_id: number;
  title: string;
  processing_status: DocumentProcessingStatus;
  page_count: number;
  extracted_chars: number;
  text_truncated: boolean;
  text: string | null;
}

export interface DocumentSummary {
  id: number;
  user_id: number;
  document_id: number | null;
  note_id: number | null;
  method: string;
  engine_version: string;
  summary_text: string;
  key_points: string[];
  source_chars: number;
  source_sentences: number;
  chunk_count: number;
  word_count: number;
  created_at: string;
  source_title?: string | null;
  warnings: string[];
}

export interface QuizQuestion {
  id: number;
  order_index: number;
  question_type: string;
  prompt: string;
  options: string[];
  source_page?: number | null;
}

export interface Quiz {
  id: number;
  user_id: number;
  document_id: number | null;
  note_id: number | null;
  semester_id: number | null;
  subject_id: number | null;
  title: string;
  method: string;
  engine_version: string;
  requested_count: number;
  question_count: number;
  source_chars: number;
  created_at: string;
  questions: QuizQuestion[];
  subject_name?: string | null;
  semester_name?: string | null;
  document_title?: string | null;
  attempt_count: number;
  best_score_percent: number | null;
  warnings: string[];
}

export interface AttemptAnswerDetail {
  question_id: number;
  order_index: number;
  prompt: string;
  options: string[];
  selected_index: number | null;
  correct_index: number;
  is_correct: boolean;
  explanation: string;
  source_excerpt?: string | null;
  source_page?: number | null;
}

export interface QuizAttempt {
  id: number;
  quiz_id: number;
  user_id: number;
  total_questions: number;
  correct_count: number;
  score_percent: number;
  duration_seconds: number | null;
  submitted_at: string;
  answers: AttemptAnswerDetail[];
}

export interface QuizResults {
  quiz: Quiz;
  attempts: QuizAttempt[];
  best_score_percent: number | null;
  average_score_percent: number | null;
}

export type InsightSource =
  | { kind: "document"; id: number }
  | { kind: "note"; id: number };

function insightPath(source: InsightSource): string {
  return source.kind === "document" ? `/documents/${source.id}` : `/notes/${source.id}`;
}

export async function getDocuments(params?: {
  q?: string;
  subject_id?: number;
  semester_id?: number;
  status?: DocumentProcessingStatus;
  limit?: number;
  offset?: number;
}): Promise<DocumentListResult> {
  const queryParams = new URLSearchParams();
  if (params?.q) queryParams.append("q", params.q);
  if (params?.subject_id) queryParams.append("subject_id", params.subject_id.toString());
  if (params?.semester_id) queryParams.append("semester_id", params.semester_id.toString());
  if (params?.status) queryParams.append("status", params.status);
  if (params?.limit) queryParams.append("limit", params.limit.toString());
  if (params?.offset) queryParams.append("offset", params.offset.toString());
  const query = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return request<DocumentListResult>(`/documents${query}`);
}

export async function uploadDocument(payload: {
  file: File;
  title?: string;
  subject_id?: number | null;
  semester_id?: number | null;
}): Promise<StudyDocument> {
  const form = new FormData();
  form.append("file", payload.file);
  if (payload.title?.trim()) form.append("title", payload.title.trim());
  if (payload.subject_id) form.append("subject_id", payload.subject_id.toString());
  if (payload.semester_id) form.append("semester_id", payload.semester_id.toString());
  return requestForm<StudyDocument>("/documents", form);
}

export async function getDocumentText(id: number): Promise<DocumentText> {
  return request<DocumentText>(`/documents/${id}/text`);
}

export async function reprocessDocument(id: number): Promise<StudyDocument> {
  return request<StudyDocument>(`/documents/${id}/reprocess`, { method: "POST" });
}

export async function deleteDocument(id: number): Promise<void> {
  return request<void>(`/documents/${id}`, { method: "DELETE" });
}

export async function generateSummary(
  source: InsightSource,
  payload: { max_words?: number; max_key_points?: number } = {}
): Promise<DocumentSummary> {
  return request<DocumentSummary>(`${insightPath(source)}/summary`, {
    method: "POST",
    body: JSON.stringify({
      max_words: payload.max_words ?? 220,
      max_key_points: payload.max_key_points ?? 6,
      regenerate: true,
    }),
  });
}

export async function getSummary(source: InsightSource): Promise<DocumentSummary> {
  return request<DocumentSummary>(`${insightPath(source)}/summary`);
}

export async function generateQuiz(
  source: InsightSource,
  questionCount: number
): Promise<Quiz> {
  return request<Quiz>(`${insightPath(source)}/quiz`, {
    method: "POST",
    body: JSON.stringify({ question_count: questionCount }),
  });
}

export async function listQuizzes(source: InsightSource): Promise<Quiz[]> {
  return request<Quiz[]>(`${insightPath(source)}/quizzes`);
}

export async function getQuiz(quizId: number): Promise<Quiz> {
  return request<Quiz>(`/quizzes/${quizId}`);
}

export async function submitQuizAttempt(
  quizId: number,
  answers: { question_id: number; selected_index: number | null }[],
  durationSeconds?: number
): Promise<QuizAttempt> {
  return request<QuizAttempt>(`/quizzes/${quizId}/attempts`, {
    method: "POST",
    body: JSON.stringify({ answers, duration_seconds: durationSeconds ?? null }),
  });
}

export async function getQuizResults(quizId: number): Promise<QuizResults> {
  return request<QuizResults>(`/quizzes/${quizId}/results`);
}
