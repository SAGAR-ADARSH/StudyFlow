// StudyFlow API Client Library

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

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
    headers["Authorization"] = `Bearer ${token}`;
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
    const errorMsg = data.detail || `Request failed with status ${response.status}`;
    throw new Error(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
  }

  return data as T;
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
