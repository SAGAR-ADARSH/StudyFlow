"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  BookOpen,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  GraduationCap,
  Layers,
  LogOut,
  Plus,
  Sparkles,
  Trash2,
  User as UserIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  User,
  Semester,
  Subject,
  Topic,
  Exam,
  getMe,
  getSemesters,
  createSemester,
  activateSemester,
  deleteSemester,
  getSubjects,
  createSubject,
  deleteSubject,
  getTopics,
  createTopic,
  updateTopicStatus,
  deleteTopic,
  getExams,
  createExam,
  updateExam,
  deleteExam,
  clearToken,
} from "@/lib/api";

type TabType = "overview" | "semesters" | "subjects" | "topics" | "exams";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [semesters, setSemesters] = useState<Semester[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedSemesterId, setSelectedSemesterId] = useState<number | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | null>(null);

  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal Dialogs state
  const [showSemesterModal, setShowSemesterModal] = useState(false);
  const [showSubjectModal, setShowSubjectModal] = useState(false);
  const [showTopicModal, setShowTopicModal] = useState(false);
  const [showExamModal, setShowExamModal] = useState(false);

  // Form states
  const [semForm, setSemForm] = useState({ name: "", semester_number: 1, is_active: true });
  const [subForm, setSubForm] = useState({
    name: "",
    code: "",
    color: "#4F46E5",
    credits: 3,
    difficulty_level: "Medium",
    target_grade: "A",
  });
  const [topicForm, setTopicForm] = useState({
    name: "",
    description: "",
    unit_number: 1,
    priority: "Medium",
    estimated_hours: 2,
    importance_score: 3,
  });
  const [examForm, setExamForm] = useState({
    title: "",
    subject_id: 0,
    exam_type: "Theory",
    exam_date: new Date().toISOString().split("T")[0],
    start_time: "10:00 AM",
    total_marks: 100,
    passing_marks: 40,
    target_marks: 85,
    location: "Exam Hall",
  });

  async function loadData() {
    setIsLoading(true);
    setError(null);
    try {
      const meData = await getMe();
      setUser(meData);

      const semData = await getSemesters();
      setSemesters(semData);

      const activeSem = semData.find((s) => s.is_active) || semData[0] || null;
      if (activeSem) {
        setSelectedSemesterId(activeSem.id);
      }

      const [subData, topData, exData] = await Promise.all([
        getSubjects(),
        getTopics(),
        getExams(),
      ]);

      setSubjects(subData);
      setTopics(topData);
      setExams(exData);

      if (subData.length > 0 && !selectedSubjectId) {
        setSelectedSubjectId(subData[0].id);
      }
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to load academic data.");
      if (err instanceof Error && (err.message.includes("401") || err.message.includes("credentials") || err.message.includes("Authentication"))) {
        clearToken();
        router.push("/login");
      }
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  // Active semester helper
  const activeSemester = useMemo(() => {
    return (
      semesters.find((s) => s.id === selectedSemesterId) ||
      semesters.find((s) => s.is_active) ||
      semesters[0] ||
      null
    );
  }, [semesters, selectedSemesterId]);

  // Filtered lists
  const currentSemesterSubjects = useMemo(() => {
    if (!activeSemester) return subjects;
    return subjects.filter((s) => s.semester_id === activeSemester.id);
  }, [subjects, activeSemester]);

  const activeSubject = useMemo(() => {
    return (
      currentSemesterSubjects.find((s) => s.id === selectedSubjectId) ||
      currentSemesterSubjects[0] ||
      null
    );
  }, [currentSemesterSubjects, selectedSubjectId]);

  const currentSubjectTopics = useMemo(() => {
    if (!activeSubject) return [];
    return topics.filter((t) => t.subject_id === activeSubject.id);
  }, [topics, activeSubject]);

  const upcomingExams = useMemo(() => {
    return exams.filter((e) => e.status !== "Completed");
  }, [exams]);

  const completedTopicsCount = useMemo(() => {
    return topics.filter((t) => t.status === "Completed").length;
  }, [topics]);

  // Handlers for Semester
  async function handleCreateSemester(e: React.FormEvent) {
    e.preventDefault();
    if (!semForm.name.trim()) return;
    try {
      await createSemester({
        name: semForm.name,
        semester_number: Number(semForm.semester_number) || undefined,
        is_active: semForm.is_active,
      });
      setShowSemesterModal(false);
      setSemForm({ name: "", semester_number: 1, is_active: true });
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create semester");
    }
  }

  async function handleActivateSemester(id: number) {
    try {
      await activateSemester(id);
      setSelectedSemesterId(id);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to activate semester");
    }
  }

  async function handleDeleteSemester(id: number) {
    if (!confirm("Are you sure? This will delete all subjects, topics, and exams in this semester.")) return;
    try {
      await deleteSemester(id);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete semester");
    }
  }

  // Handlers for Subject
  async function handleCreateSubject(e: React.FormEvent) {
    e.preventDefault();
    if (!activeSemester || !subForm.name.trim()) return;
    try {
      await createSubject({
        semester_id: activeSemester.id,
        name: subForm.name,
        code: subForm.code || undefined,
        color: subForm.color || "#4F46E5",
        credits: Number(subForm.credits) || 3,
        difficulty_level: subForm.difficulty_level,
        target_grade: subForm.target_grade || undefined,
      });
      setShowSubjectModal(false);
      setSubForm({
        name: "",
        code: "",
        color: "#4F46E5",
        credits: 3,
        difficulty_level: "Medium",
        target_grade: "A",
      });
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create subject");
    }
  }

  async function handleDeleteSubject(id: number) {
    if (!confirm("Delete this subject and all its topics/exams?")) return;
    try {
      await deleteSubject(id);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete subject");
    }
  }

  // Handlers for Topics
  async function handleCreateTopic(e: React.FormEvent) {
    e.preventDefault();
    if (!activeSubject || !topicForm.name.trim()) return;
    try {
      await createTopic({
        subject_id: activeSubject.id,
        name: topicForm.name,
        description: topicForm.description || undefined,
        unit_number: Number(topicForm.unit_number) || 1,
        priority: topicForm.priority,
        estimated_hours: Number(topicForm.estimated_hours) || 1,
        importance_score: Number(topicForm.importance_score) || 3,
      });
      setShowTopicModal(false);
      setTopicForm({
        name: "",
        description: "",
        unit_number: 1,
        priority: "Medium",
        estimated_hours: 2,
        importance_score: 3,
      });
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create topic");
    }
  }

  async function handleToggleTopicStatus(topic: Topic) {
    const nextStatus =
      topic.status === "Completed"
        ? "Pending"
        : topic.status === "Pending"
        ? "In Progress"
        : "Completed";
    try {
      await updateTopicStatus(topic.id, nextStatus);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update status");
    }
  }

  async function handleDeleteTopic(id: number) {
    if (!confirm("Delete this topic?")) return;
    try {
      await deleteTopic(id);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete topic");
    }
  }

  // Handlers for Exams
  async function handleCreateExam(e: React.FormEvent) {
    e.preventDefault();
    const subjId = Number(examForm.subject_id) || activeSubject?.id;
    if (!subjId || !examForm.title.trim()) {
      alert("Please select a subject and enter exam title");
      return;
    }
    try {
      await createExam({
        subject_id: subjId,
        semester_id: activeSemester?.id,
        title: examForm.title,
        exam_type: examForm.exam_type,
        exam_date: examForm.exam_date,
        start_time: examForm.start_time,
        total_marks: Number(examForm.total_marks) || 100,
        passing_marks: Number(examForm.passing_marks) || 40,
        target_marks: Number(examForm.target_marks) || 85,
        location: examForm.location,
      });
      setShowExamModal(false);
      setExamForm({
        title: "",
        subject_id: activeSubject ? activeSubject.id : 0,
        exam_type: "Theory",
        exam_date: new Date().toISOString().split("T")[0],
        start_time: "10:00 AM",
        total_marks: 100,
        passing_marks: 40,
        target_marks: 85,
        location: "Exam Hall",
      });
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create exam");
    }
  }

  async function handleCompleteExam(exam: Exam) {
    const marksStr = prompt("Enter obtained marks:", exam.obtained_marks?.toString() || "");
    if (marksStr === null) return;
    const obtainedMarks = parseFloat(marksStr) || 0;
    try {
      await updateExam(exam.id, {
        status: "Completed",
        obtained_marks: obtainedMarks,
      });
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update exam");
    }
  }

  async function handleDeleteExam(id: number) {
    if (!confirm("Delete this exam?")) return;
    try {
      await deleteExam(id);
      await loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete exam");
    }
  }

  if (isLoading) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-indigo-600 border-r-transparent"></div>
          <p className="mt-4 text-sm font-medium text-slate-600">Loading your StudyFlow workspace…</p>
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b bg-white sticky top-0 z-30">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 py-3">
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="flex items-center gap-2 font-bold text-slate-900 text-lg">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
                <Sparkles className="h-4 w-4" />
              </div>
              <span>Study<span className="text-indigo-600">Flow</span></span>
            </Link>

            {/* Semester Switcher Dropdown */}
            {semesters.length > 0 && (
              <div className="hidden md:flex items-center gap-2 rounded-lg bg-slate-100 p-1">
                <span className="px-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Semester:</span>
                <select
                  value={selectedSemesterId || ""}
                  onChange={(e) => setSelectedSemesterId(Number(e.target.value))}
                  className="bg-white border border-slate-200 rounded-md px-2 py-1 text-xs font-medium text-slate-800 focus:outline-none"
                >
                  {semesters.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} {s.is_active ? "★ (Active)" : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            {user && (
              <div className="flex items-center gap-2 text-sm text-slate-700">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 font-semibold text-xs">
                  {user.display_name.charAt(0).toUpperCase()}
                </div>
                <div className="hidden sm:block text-left">
                  <p className="font-semibold text-xs leading-none text-slate-900">{user.display_name}</p>
                  <p className="text-[10px] text-slate-500 leading-none mt-1">{user.course_name || "MCA Student"}</p>
                </div>
              </div>
            )}
            <Button variant="ghost" size="default" onClick={handleLogout} className="text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50">
              <LogOut className="h-3.5 w-3.5 mr-1" /> Sign Out
            </Button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="mx-auto max-w-7xl px-4 sm:px-6 flex gap-4 border-t border-slate-100 text-sm overflow-x-auto">
          <button
            onClick={() => setActiveTab("overview")}
            className={`py-3 px-1 border-b-2 font-medium text-xs flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === "overview"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Layers className="h-4 w-4" /> Overview & Planner
          </button>
          <button
            onClick={() => setActiveTab("semesters")}
            className={`py-3 px-1 border-b-2 font-medium text-xs flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === "semesters"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <GraduationCap className="h-4 w-4" /> Semesters ({semesters.length})
          </button>
          <button
            onClick={() => setActiveTab("subjects")}
            className={`py-3 px-1 border-b-2 font-medium text-xs flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === "subjects"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <BookOpen className="h-4 w-4" /> Subjects ({subjects.length})
          </button>
          <button
            onClick={() => setActiveTab("topics")}
            className={`py-3 px-1 border-b-2 font-medium text-xs flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === "topics"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <CheckCircle2 className="h-4 w-4" /> Topics ({topics.length})
          </button>
          <button
            onClick={() => setActiveTab("exams")}
            className={`py-3 px-1 border-b-2 font-medium text-xs flex items-center gap-1.5 whitespace-nowrap transition-colors ${
              activeTab === "exams"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Calendar className="h-4 w-4" /> Exams ({exams.length})
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto max-w-7xl w-full px-4 sm:px-6 py-6 flex-1">
        {error && (
          <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* TAB 1: OVERVIEW & DASHBOARD */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Quick Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Semester</p>
                <h3 className="mt-2 text-xl font-bold text-slate-900 truncate">
                  {activeSemester ? activeSemester.name : "None Added"}
                </h3>
                <p className="mt-1 text-xs text-indigo-600 font-medium">
                  {currentSemesterSubjects.length} enrolled subjects
                </p>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Subjects</p>
                <h3 className="mt-2 text-2xl font-bold text-slate-900">{subjects.length}</h3>
                <p className="mt-1 text-xs text-slate-500">Across {semesters.length} semesters</p>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Topic Progress</p>
                <h3 className="mt-2 text-2xl font-bold text-indigo-600">
                  {completedTopicsCount} <span className="text-sm font-normal text-slate-500">/ {topics.length}</span>
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  {topics.length > 0 ? `${Math.round((completedTopicsCount / topics.length) * 100)}% completed` : "No topics yet"}
                </p>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Upcoming Exams</p>
                <h3 className="mt-2 text-2xl font-bold text-amber-600">{upcomingExams.length}</h3>
                <p className="mt-1 text-xs text-slate-500">Scheduled assessments</p>
              </div>
            </div>

            {/* Quick Actions Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-indigo-50 border border-indigo-100 p-4">
              <div>
                <h4 className="font-semibold text-indigo-950 text-sm">StudyFlow Foundation Workspace</h4>
                <p className="text-xs text-indigo-700 mt-0.5">
                  Organize your curriculum into Semesters → Subjects → Topics → Exams.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="default" onClick={() => setShowSemesterModal(true)} className="text-xs bg-indigo-600">
                  <Plus className="h-3.5 w-3.5 mr-1" /> New Semester
                </Button>
                <Button
                  size="default"
                  onClick={() => setShowSubjectModal(true)}
                  disabled={!activeSemester}
                  className="text-xs bg-indigo-700"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add Subject
                </Button>
                <Button
                  size="default"
                  onClick={() => setShowExamModal(true)}
                  disabled={subjects.length === 0}
                  className="text-xs bg-indigo-800"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Schedule Exam
                </Button>
              </div>
            </div>

            {/* Split layout: Enrolled Subjects & Upcoming Exams */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Subjects in current semester */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 text-base">
                    Subjects ({currentSemesterSubjects.length})
                  </h3>
                  <Button
                    variant="ghost"
                    size="default"
                    onClick={() => setActiveTab("subjects")}
                    className="text-xs text-indigo-600"
                  >
                    View All Subjects <ChevronRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>

                {currentSemesterSubjects.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center bg-white">
                    <BookOpen className="h-8 w-8 text-slate-400 mx-auto" />
                    <p className="mt-2 text-sm font-semibold text-slate-700">No subjects in this semester yet</p>
                    <p className="text-xs text-slate-500 mt-1">Add your subjects to start tracking topics and exams.</p>
                    <Button
                      size="default"
                      onClick={() => setShowSubjectModal(true)}
                      className="mt-4 text-xs"
                      disabled={!activeSemester}
                    >
                      <Plus className="h-3.5 w-3.5 mr-1" /> Add First Subject
                    </Button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {currentSemesterSubjects.map((sub) => {
                      const subTopics = topics.filter((t) => t.subject_id === sub.id);
                      const subDone = subTopics.filter((t) => t.status === "Completed").length;
                      const pct = subTopics.length > 0 ? Math.round((subDone / subTopics.length) * 100) : 0;

                      return (
                        <div
                          key={sub.id}
                          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden"
                        >
                          <div
                            className="absolute top-0 left-0 right-0 h-1.5"
                            style={{ backgroundColor: sub.color || "#4F46E5" }}
                          />
                          <div className="flex items-start justify-between">
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                                {sub.code || "SUB"}
                              </span>
                              <h4 className="mt-2 font-bold text-slate-900 text-base leading-snug">
                                {sub.name}
                              </h4>
                              <p className="text-xs text-slate-500 mt-0.5">
                                {sub.credits} Credits • {sub.difficulty_level} Difficulty
                              </p>
                            </div>
                          </div>

                          <div className="mt-4">
                            <div className="flex justify-between text-xs font-medium text-slate-600 mb-1">
                              <span>Topics: {subDone}/{subTopics.length} done</span>
                              <span>{pct}%</span>
                            </div>
                            <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-indigo-600 rounded-full transition-all"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>

                          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                            <button
                              onClick={() => {
                                setSelectedSubjectId(sub.id);
                                setActiveTab("topics");
                              }}
                              className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                            >
                              Manage Topics ({subTopics.length}) <ChevronRight className="h-3 w-3" />
                            </button>
                            <button
                              onClick={() => handleDeleteSubject(sub.id)}
                              className="text-slate-400 hover:text-rose-600 transition-colors"
                              title="Delete Subject"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Upcoming Exams Panel */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 text-base">Upcoming Exams</h3>
                  <Button
                    variant="ghost"
                    size="default"
                    onClick={() => setActiveTab("exams")}
                    className="text-xs text-indigo-600"
                  >
                    View All <ChevronRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>

                {upcomingExams.length === 0 ? (
                  <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
                    <Calendar className="h-8 w-8 text-slate-400 mx-auto" />
                    <p className="mt-2 text-sm font-semibold text-slate-700">No upcoming exams</p>
                    <p className="text-xs text-slate-500 mt-1">All clear for now! Schedule exam dates to track countdowns.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {upcomingExams.slice(0, 4).map((ex) => (
                      <div
                        key={ex.id}
                        className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-indigo-200 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-50 text-indigo-700">
                              {ex.exam_type}
                            </span>
                            <h4 className="mt-1 font-semibold text-slate-900 text-sm">{ex.title}</h4>
                            <p className="text-xs text-slate-500">{ex.subject_name}</p>
                          </div>
                          {ex.days_remaining !== undefined && (
                            <div className="text-right">
                              <span
                                className={`text-xs font-bold px-2 py-1 rounded-full ${
                                  ex.days_remaining <= 3
                                    ? "bg-rose-100 text-rose-700"
                                    : ex.days_remaining <= 7
                                    ? "bg-amber-100 text-amber-700"
                                    : "bg-emerald-100 text-emerald-700"
                                }`}
                              >
                                {ex.days_remaining === 0
                                  ? "Today!"
                                  : ex.days_remaining < 0
                                  ? `${Math.abs(ex.days_remaining)}d ago`
                                  : `in ${ex.days_remaining}d`}
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="mt-3 flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" /> {ex.exam_date}
                          </span>
                          <button
                            onClick={() => handleCompleteExam(ex)}
                            className="font-medium text-emerald-600 hover:text-emerald-700"
                          >
                            Mark Complete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SEMESTERS */}
        {activeTab === "semesters" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Academic Semesters</h3>
                <p className="text-xs text-slate-600">Create, switch, or manage semester terms.</p>
              </div>
              <Button onClick={() => setShowSemesterModal(true)} className="text-xs">
                <Plus className="h-3.5 w-3.5 mr-1" /> Add Semester
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {semesters.map((sem) => (
                <div
                  key={sem.id}
                  className={`rounded-2xl border p-5 shadow-sm transition-all ${
                    sem.is_active
                      ? "border-indigo-500 bg-white ring-2 ring-indigo-500/20"
                      : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      {sem.is_active && (
                        <span className="inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-600 text-white mb-2">
                          Active Semester
                        </span>
                      )}
                      <h4 className="font-bold text-slate-900 text-lg">{sem.name}</h4>
                      {sem.semester_number && (
                        <p className="text-xs text-slate-500">Semester #{sem.semester_number}</p>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 border-y border-slate-100 py-3 text-center">
                    <div>
                      <p className="text-xs text-slate-400">Subjects</p>
                      <p className="text-base font-bold text-slate-800">{sem.subjects_count || 0}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Exams</p>
                      <p className="text-base font-bold text-slate-800">{sem.exams_count || 0}</p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-2">
                    {!sem.is_active ? (
                      <Button
                        variant="ghost"
                        size="default"
                        onClick={() => handleActivateSemester(sem.id)}
                        className="text-xs text-indigo-600 hover:bg-indigo-50"
                      >
                        Set as Active
                      </Button>
                    ) : (
                      <span className="text-xs font-medium text-emerald-600">Current Term</span>
                    )}

                    <button
                      onClick={() => handleDeleteSemester(sem.id)}
                      className="text-slate-400 hover:text-rose-600 p-2 rounded-lg"
                      title="Delete Semester"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: SUBJECTS */}
        {activeTab === "subjects" && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Curriculum Subjects</h3>
                <p className="text-xs text-slate-600">Manage all courses and course credits.</p>
              </div>
              <Button
                onClick={() => setShowSubjectModal(true)}
                disabled={!activeSemester}
                className="text-xs"
              >
                <Plus className="h-3.5 w-3.5 mr-1" /> Add Subject
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {subjects.map((sub) => (
                <div
                  key={sub.id}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow transition-shadow relative overflow-hidden"
                >
                  <div
                    className="absolute top-0 left-0 right-0 h-1.5"
                    style={{ backgroundColor: sub.color || "#4F46E5" }}
                  />
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {sub.code || "MCA"}
                      </span>
                      <h4 className="mt-2 font-bold text-slate-900 text-base">{sub.name}</h4>
                      <p className="text-xs text-slate-500">{sub.semester_name || "Semester"}</p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg">
                    <span>{sub.credits} Credits</span>
                    <span>Target: {sub.target_grade || "A"}</span>
                    <span>{sub.difficulty_level}</span>
                  </div>

                  <div className="mt-4 flex items-center justify-between">
                    <button
                      onClick={() => {
                        setSelectedSubjectId(sub.id);
                        setActiveTab("topics");
                      }}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
                    >
                      View Syllabus Topics →
                    </button>
                    <button
                      onClick={() => handleDeleteSubject(sub.id)}
                      className="text-slate-400 hover:text-rose-600"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: TOPICS */}
        {activeTab === "topics" && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Syllabus Topics</h3>
                <p className="text-xs text-slate-600">
                  Track individual unit topics, priorities, and study completion.
                </p>
              </div>

              {subjects.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-500">Subject:</span>
                  <select
                    value={selectedSubjectId || ""}
                    onChange={(e) => setSelectedSubjectId(Number(e.target.value))}
                    className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 bg-white"
                  >
                    {subjects.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.code || "SUB"})
                      </option>
                    ))}
                  </select>
                  <Button
                    onClick={() => setShowTopicModal(true)}
                    disabled={!activeSubject}
                    className="text-xs"
                  >
                    <Plus className="h-3.5 w-3.5 mr-1" /> Add Topic
                  </Button>
                </div>
              )}
            </div>

            {currentSubjectTopics.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 p-12 text-center bg-white">
                <CheckCircle2 className="h-10 w-10 text-slate-300 mx-auto" />
                <h4 className="mt-3 text-base font-semibold text-slate-800">No topics added for this subject</h4>
                <p className="text-xs text-slate-500 mt-1">Break down your syllabus into units and study topics.</p>
                <Button
                  onClick={() => setShowTopicModal(true)}
                  disabled={!activeSubject}
                  className="mt-4 text-xs"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add First Topic
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {currentSubjectTopics.map((topic) => (
                  <div
                    key={topic.id}
                    className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 hover:border-slate-300 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <button
                        onClick={() => handleToggleTopicStatus(topic)}
                        className={`mt-0.5 flex h-6 w-6 items-center justify-center rounded-full border transition-colors ${
                          topic.status === "Completed"
                            ? "bg-emerald-600 border-emerald-600 text-white"
                            : topic.status === "In Progress"
                            ? "bg-amber-100 border-amber-400 text-amber-700"
                            : "border-slate-300 text-transparent hover:border-slate-400"
                        }`}
                        title="Click to cycle status: Pending → In Progress → Completed"
                      >
                        ✓
                      </button>

                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                            Unit {topic.unit_number}
                          </span>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                              topic.priority === "High"
                                ? "bg-rose-100 text-rose-700"
                                : topic.priority === "Low"
                                ? "bg-slate-100 text-slate-600"
                                : "bg-blue-100 text-blue-700"
                            }`}
                          >
                            {topic.priority} Priority
                          </span>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                              topic.status === "Completed"
                                ? "bg-emerald-100 text-emerald-700"
                                : topic.status === "In Progress"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {topic.status}
                          </span>
                        </div>
                        <h4
                          className={`mt-1 font-semibold text-sm ${
                            topic.status === "Completed" ? "line-through text-slate-400" : "text-slate-900"
                          }`}
                        >
                          {topic.name}
                        </h4>
                        {topic.description && (
                          <p className="text-xs text-slate-500 mt-0.5">{topic.description}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-4 self-end sm:self-center">
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" />
                        {topic.completed_hours || 0} / {topic.estimated_hours || 1} hrs
                      </span>
                      <button
                        onClick={() => handleDeleteTopic(topic.id)}
                        className="text-slate-400 hover:text-rose-600 p-1"
                        title="Delete topic"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 5: EXAMS */}
        {activeTab === "exams" && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Exams & Assessments</h3>
                <p className="text-xs text-slate-600">Track midterms, practicals, finals, and scored results.</p>
              </div>
              <Button
                onClick={() => setShowExamModal(true)}
                disabled={subjects.length === 0}
                className="text-xs"
              >
                <Plus className="h-3.5 w-3.5 mr-1" /> Schedule Exam
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {exams.map((ex) => (
                <div
                  key={ex.id}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-50 text-indigo-700">
                        {ex.exam_type}
                      </span>
                      <h4 className="mt-2 font-bold text-slate-900 text-base">{ex.title}</h4>
                      <p className="text-xs text-slate-500">{ex.subject_name}</p>
                    </div>
                    <span
                      className={`text-xs font-bold px-2 py-1 rounded-full ${
                        ex.status === "Completed"
                          ? "bg-slate-100 text-slate-600"
                          : ex.days_remaining !== undefined && ex.days_remaining <= 3
                          ? "bg-rose-100 text-rose-700"
                          : "bg-emerald-100 text-emerald-700"
                      }`}
                    >
                      {ex.status === "Completed" ? "Completed" : `${ex.days_remaining}d left`}
                    </span>
                  </div>

                  <div className="mt-4 space-y-1.5 text-xs text-slate-600 border-t border-slate-100 pt-3">
                    <p className="flex justify-between">
                      <span className="text-slate-400">Date:</span>
                      <span className="font-medium text-slate-800">{ex.exam_date} ({ex.start_time || "10:00 AM"})</span>
                    </p>
                    <p className="flex justify-between">
                      <span className="text-slate-400">Target Marks:</span>
                      <span className="font-medium text-slate-800">{ex.target_marks || 85} / {ex.total_marks || 100}</span>
                    </p>
                    {ex.obtained_marks !== null && ex.obtained_marks !== undefined && (
                      <p className="flex justify-between font-bold text-emerald-700">
                        <span>Obtained Marks:</span>
                        <span>{ex.obtained_marks} / {ex.total_marks}</span>
                      </p>
                    )}
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                    <button
                      onClick={() => handleCompleteExam(ex)}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
                    >
                      {ex.status === "Completed" ? "Edit Score" : "Mark Scored"}
                    </button>
                    <button
                      onClick={() => handleDeleteExam(ex.id)}
                      className="text-slate-400 hover:text-rose-600"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* ----------------- MODAL: CREATE SEMESTER ----------------- */}
      {showSemesterModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl animate-in fade-in">
            <h3 className="text-lg font-bold text-slate-900">Add Academic Semester</h3>
            <p className="text-xs text-slate-500 mt-1">Define term name (e.g. MCA Semester 3, Fall 2026).</p>

            <form onSubmit={handleCreateSemester} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700">Semester Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. MCA Semester 1"
                  value={semForm.name}
                  onChange={(e) => setSemForm({ ...semForm, name: e.target.value })}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">Semester Number</label>
                <input
                  type="number"
                  min={1}
                  max={12}
                  value={semForm.semester_number}
                  onChange={(e) => setSemForm({ ...semForm, semester_number: parseInt(e.target.value) || 1 })}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="sem_active"
                  checked={semForm.is_active}
                  onChange={(e) => setSemForm({ ...semForm, is_active: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="sem_active" className="text-xs text-slate-700">Set as currently active semester</label>
              </div>

              <div className="mt-6 flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setShowSemesterModal(false)} className="text-xs">
                  Cancel
                </Button>
                <Button type="submit" className="text-xs">
                  Save Semester
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------- MODAL: CREATE SUBJECT ----------------- */}
      {showSubjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl animate-in fade-in">
            <h3 className="text-lg font-bold text-slate-900">Add Subject</h3>
            <p className="text-xs text-slate-500 mt-1">
              Adding to semester: <span className="font-semibold text-indigo-600">{activeSemester?.name}</span>
            </p>

            <form onSubmit={handleCreateSubject} className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Subject Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Data Structures & Algorithms"
                  value={subForm.name}
                  onChange={(e) => setSubForm({ ...subForm, name: e.target.value })}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Course Code</label>
                  <input
                    type="text"
                    placeholder="e.g. MCA-101"
                    value={subForm.code}
                    onChange={(e) => setSubForm({ ...subForm, code: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700">Credits</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={subForm.credits}
                    onChange={(e) => setSubForm({ ...subForm, credits: parseInt(e.target.value) || 3 })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Difficulty</label>
                  <select
                    value={subForm.difficulty_level}
                    onChange={(e) => setSubForm({ ...subForm, difficulty_level: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700">Target Grade</label>
                  <input
                    type="text"
                    placeholder="e.g. A+ / 90%"
                    value={subForm.target_grade}
                    onChange={(e) => setSubForm({ ...subForm, target_grade: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setShowSubjectModal(false)} className="text-xs">
                  Cancel
                </Button>
                <Button type="submit" className="text-xs">
                  Save Subject
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------- MODAL: CREATE TOPIC ----------------- */}
      {showTopicModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl animate-in fade-in">
            <h3 className="text-lg font-bold text-slate-900">Add Syllabus Topic</h3>
            <p className="text-xs text-slate-500 mt-1">
              Adding to subject: <span className="font-semibold text-indigo-600">{activeSubject?.name}</span>
            </p>

            <form onSubmit={handleCreateTopic} className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Topic Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Binary Search Trees & AVL Trees"
                  value={topicForm.name}
                  onChange={(e) => setTopicForm({ ...topicForm, name: e.target.value })}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Unit Number</label>
                  <input
                    type="number"
                    min={1}
                    value={topicForm.unit_number}
                    onChange={(e) => setTopicForm({ ...topicForm, unit_number: parseInt(e.target.value) || 1 })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700">Priority</label>
                  <select
                    value={topicForm.priority}
                    onChange={(e) => setTopicForm({ ...topicForm, priority: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">Estimated Study Hours</label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  value={topicForm.estimated_hours}
                  onChange={(e) => setTopicForm({ ...topicForm, estimated_hours: parseFloat(e.target.value) || 1 })}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="mt-6 flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setShowTopicModal(false)} className="text-xs">
                  Cancel
                </Button>
                <Button type="submit" className="text-xs">
                  Save Topic
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------- MODAL: CREATE EXAM ----------------- */}
      {showExamModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl animate-in fade-in">
            <h3 className="text-lg font-bold text-slate-900">Schedule Exam</h3>
            <p className="text-xs text-slate-500 mt-1">Set date, time, and target marks for assessment.</p>

            <form onSubmit={handleCreateExam} className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700">Exam Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. DSA Midterm Theory Exam"
                  value={examForm.title}
                  onChange={(e) => setExamForm({ ...examForm, title: e.target.value })}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">Subject *</label>
                <select
                  value={examForm.subject_id || activeSubject?.id || ""}
                  onChange={(e) => setExamForm({ ...examForm, subject_id: parseInt(e.target.value) })}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code || "SUB"})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Exam Date *</label>
                  <input
                    type="date"
                    required
                    value={examForm.exam_date}
                    onChange={(e) => setExamForm({ ...examForm, exam_date: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700">Exam Type</label>
                  <select
                    value={examForm.exam_type}
                    onChange={(e) => setExamForm({ ...examForm, exam_type: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="Theory">Theory</option>
                    <option value="Practical">Practical / Lab</option>
                    <option value="Midterm">Midterm</option>
                    <option value="Final">End Semester Final</option>
                    <option value="Quiz">Quiz / Internal</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Total Marks</label>
                  <input
                    type="number"
                    value={examForm.total_marks}
                    onChange={(e) => setExamForm({ ...examForm, total_marks: parseFloat(e.target.value) || 100 })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700">Target Marks</label>
                  <input
                    type="number"
                    value={examForm.target_marks}
                    onChange={(e) => setExamForm({ ...examForm, target_marks: parseFloat(e.target.value) || 85 })}
                    className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setShowExamModal(false)} className="text-xs">
                  Cancel
                </Button>
                <Button type="submit" className="text-xs">
                  Schedule Exam
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
