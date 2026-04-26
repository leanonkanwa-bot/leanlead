const $ = (id) => document.getElementById(id);

const loginCard = $("login");
const appCard = $("tool");
const loginForm = $("loginForm");

if (!appCard) {
  console.error("LeanLead: #tool not found in DOM. Did the HTML structure change?");
}
const loginPwd = $("loginPwd");
const loginErr = $("loginErr");

const form = $("form");
const submitBtn = $("submit");
const drop = document.querySelector(".drop");
const dropLabel = $("dropLabel");
const videoInput = $("video");

const statusCard = $("statusCard");
const statusLabel = $("statusLabel");
const statusMsg = $("statusMsg");
const statusPip = $("statusPip");
const barFill = $("barFill");

const resultCard = $("resultCard");
const player = $("player");
const downloadLink = $("downloadLink");
const pkgTitle = $("pkgTitle");
const pkgThumb = $("pkgThumb");
const pkgEnd = $("pkgEnd");
const planJson = $("planJson");

(async () => {
  try {
    const res = await fetch("/api/auth/status", { credentials: "same-origin" });
    const j = await res.json();
    if (j.required && !j.authed) {
      loginCard.classList.remove("hidden");
    } else {
      appCard.classList.remove("hidden");
    }
  } catch {
    appCard.classList.remove("hidden");
  }
})();

loginForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginErr.textContent = "";
  const fd = new FormData();
  fd.set("password", loginPwd.value);
  const res = await fetch("/api/auth/login", {
    method: "POST",
    body: fd,
    credentials: "same-origin",
  });
  if (!res.ok) {
    loginErr.textContent = "Wrong password.";
    return;
  }
  loginCard.classList.add("hidden");
  appCard.classList.remove("hidden");
  appCard.scrollIntoView({ behavior: "smooth", block: "start" });
});

videoInput.addEventListener("change", () => {
  const f = videoInput.files?.[0];
  if (f) {
    dropLabel.textContent = `${f.name} — ${(f.size / (1024 * 1024)).toFixed(1)} MB`;
    drop.classList.add("has-file");
  }
});

["dragenter", "dragover"].forEach((ev) =>
  drop.addEventListener(ev, (e) => {
    e.preventDefault();
    drop.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((ev) =>
  drop.addEventListener(ev, (e) => {
    e.preventDefault();
    drop.classList.remove("dragover");
  })
);

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  resultCard.classList.add("hidden");
  statusCard.classList.remove("hidden");
  statusCard.scrollIntoView({ behavior: "smooth", block: "center" });
  setStatus("queued", "Uploading…", 5);
  submitBtn.disabled = true;
  submitBtn.querySelector(".btn-label").textContent = "Working…";

  const fd = new FormData(form);
  let res;
  try {
    res = await fetch("/api/edit", {
      method: "POST",
      body: fd,
      credentials: "same-origin",
    });
  } catch (err) {
    return fail(`Upload failed: ${err.message}`);
  }
  if (res.status === 401) {
    loginCard.classList.remove("hidden");
    appCard.classList.add("hidden");
    statusCard.classList.add("hidden");
    submitBtn.disabled = false;
    submitBtn.querySelector(".btn-label").textContent = "Edit my video";
    return;
  }
  if (!res.ok) return fail(`Server: ${res.status} ${await res.text()}`);
  const { job_id } = await res.json();
  poll(job_id);
});

async function poll(jobId) {
  while (true) {
    await new Promise((r) => setTimeout(r, 1500));
    const res = await fetch(`/api/jobs/${jobId}`, { credentials: "same-origin" });
    if (!res.ok) return fail(`Lost the job: ${res.status}`);
    const job = await res.json();
    setStatus(job.status, job.message || "", job.progress || 0);
    if (job.status === "done") return showResult(jobId, job.result);
    if (job.status === "error") return fail(job.error || "Unknown error");
  }
}

const STATUS_LABELS = {
  queued: "Queued",
  transcribing: "Transcribing",
  planning: "Planning the edit",
  rendering: "Rendering",
  done: "Done",
  error: "Error",
};
const STATUS_PIPS = {
  queued: "1/4",
  transcribing: "2/4",
  planning: "3/4",
  rendering: "4/4",
  done: "✓",
  error: "✗",
};

function setStatus(status, message, progress) {
  statusLabel.textContent = STATUS_LABELS[status] || status;
  statusMsg.textContent = message;
  statusPip.textContent = STATUS_PIPS[status] || "…";
  barFill.style.width = `${progress}%`;
  if (status === "error") {
    barFill.style.background = "var(--err)";
    statusPip.style.color = "var(--err)";
    statusPip.style.borderColor = "rgba(255,92,122,.3)";
    statusPip.style.background = "rgba(255,92,122,.08)";
  } else {
    barFill.style.background = "linear-gradient(90deg, var(--accent), var(--accent-2))";
    statusPip.style.color = "var(--accent)";
    statusPip.style.borderColor = "rgba(255,214,10,.2)";
    statusPip.style.background = "rgba(255,214,10,.08)";
  }
}

function fail(msg) {
  submitBtn.disabled = false;
  submitBtn.querySelector(".btn-label").textContent = "Edit my video";
  setStatus("error", msg, 100);
}

function showResult(jobId, result) {
  submitBtn.disabled = false;
  submitBtn.querySelector(".btn-label").textContent = "Edit another";
  resultCard.classList.remove("hidden");
  resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
  player.src = `/api/download/${jobId}`;
  downloadLink.href = `/api/download/${jobId}`;
  const pkg = result?.packaging || {};
  pkgTitle.textContent = pkg.title || "—";
  pkgThumb.textContent = pkg.thumbnail_word || "—";
  pkgEnd.textContent = pkg.end_caption || "—";
  planJson.textContent = JSON.stringify(result?.plan ?? {}, null, 2);
}
