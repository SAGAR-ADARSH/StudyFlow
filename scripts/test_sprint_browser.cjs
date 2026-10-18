// Optional full browser acceptance test. See docs/sprint-mode.md for setup.
const assert = require("node:assert/strict");
const { chromium: playwright } = require("playwright-core");
const chromiumModule = require("@sparticuz/chromium");
const chromium = chromiumModule.default || chromiumModule;
const origin = process.env.WEB_URL || "http://localhost:3000";
const password = "SprintBrowser123!";
const email = `sprint.browser.${Date.now()}@studyflow.edu`;
let token;
async function api(path, method = "GET", body) {
  const response = await fetch(origin + "/api/v1" + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-StudyFlow-Token": token } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  assert.ok(
    response.ok,
    `${path}: ${response.status} ${await response.clone().text()}`,
  );
  return response.json();
}
(async () => {
  const auth = await api("/auth/register", "POST", {
    email,
    password,
    display_name: "Sprint Browser Student",
  });
  token = auth.access_token;
  const sem = await api("/semesters", "POST", {
    name: "Sprint browser semester",
  });
  const sub = await api("/subjects", "POST", {
    name: "Operating Systems",
    semester_id: sem.id,
  });
  const high = await api("/topics", "POST", {
    subject_id: sub.id,
    name: "High priority scheduling",
    priority: "High",
    importance_score: 5,
    estimated_hours: 4,
  });
  await api("/topics", "POST", {
    subject_id: sub.id,
    name: "Lower priority memory",
    priority: "Low",
    importance_score: 1,
  });
  const examDate = new Date();
  examDate.setUTCDate(examDate.getUTCDate() + 5);
  const exam = await api("/exams", "POST", {
    subject_id: sub.id,
    title: "Sprint browser exam",
    exam_date: examDate.toISOString().slice(0, 10),
  });
  // The source and generated quiz use the existing note/insight services, never fake questions.
  const content =
    "A process is a program in execution together with its own address space and register state. A thread is the smallest unit of execution inside a process that shares the process memory. Context switching is the mechanism of saving the state of one process and loading the state of another so that the CPU can serve several programs. Virtual memory is a memory management technique that gives each process the illusion of a large contiguous main memory. Paging is a memory management scheme that divides memory into fixed size blocks called frames and pages. A page fault is an interrupt raised when a program accesses a page that is not currently present in physical memory. A device driver is a program that lets the operating system communicate with a specific hardware device.";
  const note = await api("/notes", "POST", {
    subject_id: sub.id,
    topic_id: high.id,
    title: "Sprint revision note",
    content,
  });
  const fs = require("node:fs");
  const path = require("node:path");
  const tmp = fs.mkdtempSync(
    path.join(require("node:os").tmpdir(), "sprint-pdf-"),
  );
  const pdfPath = path.join(tmp, "lecture.pdf");
  let document;
  try {
    require("node:child_process").execFileSync(
      process.env.PYTHON || ".venv/bin/python",
      ["apps/api/scripts/make_sample_pdf.py", pdfPath],
    );
    const form = new FormData();
    form.set("subject_id", String(sub.id));
    form.set("title", "Sprint lecture PDF");
    form.set(
      "file",
      new Blob([fs.readFileSync(pdfPath)], { type: "application/pdf" }),
      "lecture.pdf",
    );
    const uploaded = await fetch(origin + "/api/v1/documents", {
      method: "POST",
      headers: { "X-StudyFlow-Token": token },
      body: form,
    });
    assert.equal(uploaded.status, 201);
    document = await uploaded.json();
    assert.equal(document.processing_status, "completed");
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
  await api(`/documents/${document.id}/summary`, "POST", { max_words: 120 });
  const quiz = await api(`/documents/${document.id}/quiz`, "POST", {
    question_count: 3,
  });

  const browser = await playwright.launch({
    executablePath: await chromium.executablePath(),
    args: chromium.args,
    headless: true,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1365, height: 900 },
    });
    page.setDefaultTimeout(20000);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(origin + "/login");
    await page.locator('input[name="email"]').fill(email);
    await page.locator('input[name="password"]').fill(password);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL("**/dashboard");
    await page
      .getByRole("button", { name: "Sprint Mode", exact: true })
      .click({ noWaitAfter: true });
    await page
      .getByLabel("Upcoming exam", { exact: true })
      .selectOption(String(exam.id));
    await page.getByLabel("Daily study time", { exact: true }).fill("90");
    await page
      .getByRole("button", { name: "Activate Sprint", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Today’s Focus", exact: false })
      .waitFor();
    let plan = await api("/sprints/active");
    assert.equal(plan.exam_id, exam.id);
    assert.equal(plan.tasks[0].topic_id, high.id);
    assert.ok(plan.tasks.reduce((n, t) => n + t.minutes, 0) <= 90);
    console.log(
      "PASS browser sign-in, exam selection, activation, priority and budget",
    );

    await page
      .getByRole("button", { name: "Review summary", exact: true })
      .click();
    const dialog = page.getByRole("dialog");
    await dialog
      .getByRole("heading", { name: "Summary", exact: true })
      .waitFor();
    await dialog
      .getByRole("button", { name: "Close", exact: true })
      .last()
      .click();
    await page
      .getByRole("article")
      .filter({
        has: page.getByRole("heading", {
          name: "Sprint lecture PDF",
          exact: true,
        }),
      })
      .getByRole("button", { name: "Quizzes & results", exact: true })
      .click();
    await dialog.getByRole("button", { name: "Retake", exact: true }).click();
    for (let i = 0; i < quiz.question_count; i++) {
      // Deliberately skip: all skipped answers are genuinely graded incorrect.
      await dialog
        .getByRole("button", {
          name: i === quiz.question_count - 1 ? "Submit quiz" : "Next",
          exact: true,
        })
        .click();
    }
    await dialog
      .getByRole("heading", { name: "Quiz results", exact: true })
      .waitFor();
    await dialog
      .getByRole("button", { name: "Close", exact: true })
      .last()
      .click();
    await page
      .getByText("Quiz signals refreshed. Completed work was kept.", {
        exact: true,
      })
      .waitFor();
    plan = await api("/sprints/active");
    assert.equal(plan.quiz_average, 0);
    assert.ok(plan.revision_topics.length > 0);
    assert.equal((await api(`/quizzes/${quiz.id}/results`)).attempts.length, 1);
    console.log(
      "PASS summary modal, saved quiz submission, persistence and adaptive signal",
    );

    const first = plan.tasks.find((t) => t.kind === "study");
    await page
      .getByRole("checkbox", { name: `Complete ${first.title}`, exact: true })
      .click();
    await page.getByText("Task updated.", { exact: true }).waitFor();
    await page.getByLabel("Daily study time", { exact: true }).fill("120");
    await page
      .getByRole("button", { name: "Apply budget & recalculate", exact: true })
      .click();
    await page
      .getByText("Plan recalculated. Completed tasks preserved.", {
        exact: true,
      })
      .waitFor();
    plan = await api("/sprints/active");
    assert.equal(plan.budget_minutes, 120);
    assert.equal(plan.tasks.find((t) => t.id === first.id).completed, true);
    await page.reload();
    await page
      .getByRole("button", { name: "Sprint Mode", exact: true })
      .click({ noWaitAfter: true });
    await page
      .getByRole("checkbox", { name: `Complete ${first.title}`, exact: true })
      .waitFor();
    assert.ok(
      await page
        .getByRole("checkbox", { name: `Complete ${first.title}`, exact: true })
        .isChecked(),
    );
    await page.getByRole("button", { name: "Pause", exact: true }).click();
    await page.getByRole("button", { name: "Resume", exact: true }).waitFor();
    assert.ok(
      await page
        .getByRole("checkbox", { name: `Complete ${first.title}`, exact: true })
        .isDisabled(),
    );
    await page.getByRole("button", { name: "Resume", exact: true }).click();
    await page.getByRole("button", { name: "Pause", exact: true }).waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
      "No horizontal overflow at mobile width",
    );
    page.on("dialog", (dialog) => dialog.accept());
    await page
      .getByRole("button", { name: "Exit sprint", exact: true })
      .click();
    await page
      .getByText("Sprint exited. History saved.", { exact: true })
      .waitFor();
    assert.equal((await api(`/sprints/${plan.id}`)).status, "cancelled");
    assert.deepEqual(errors, []);
    console.log(
      "PASS completion, budget change, reload, pause/resume, mobile overflow, exit and no page errors",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
