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
      document.querySelectorAll('a[href="#tool"]').forEach((a) => { a.href = "#login"; });
    } else {
      appCard.classList.remove("hidden");
    }
  } catch {
    // Backend is unreachable — show the tool section but with a prominent warning
    // so the user knows they need to start the server before submitting.
    appCard.classList.remove("hidden");
    const warn = document.createElement("p");
    warn.id = "backendWarn";
    warn.style.cssText = "color:var(--err,#ff5c7a);margin-bottom:1rem;font-size:.9rem";
    warn.textContent = "⚠ Backend not reachable. Run “python app.py” and reload this page before editing a video.";
    appCard.querySelector(".tool-head")?.after(warn);
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
  document.querySelectorAll('a[href="#login"]').forEach((a) => { a.href = "#tool"; });
  appCard.scrollIntoView({ behavior: "smooth", block: "start" });
});

const CHUNK_SIZE = 50 * 1024 * 1024; // 50 MB per chunk

videoInput.addEventListener("change", () => {
  const f = videoInput.files?.[0];
  if (!f) return;
  const mb = (f.size / (1024 * 1024)).toFixed(1);
  dropLabel.textContent = `${f.name} — ${mb} MB`;
  drop.classList.add("has-file");
});

["dragenter", "dragover"].forEach((ev) =>
  drop.addEventListener(ev, (e) => {
    e.preventDefault();
    drop.classList.add("dragover");
  })
);
drop.addEventListener("dragleave", (e) => {
  e.preventDefault();
  drop.classList.remove("dragover");
});

drop.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.classList.remove("dragover");
  const files = e.dataTransfer?.files;
  if (files?.length) {
    const dt = new DataTransfer();
    dt.items.add(files[0]);
    videoInput.files = dt.files;
    videoInput.dispatchEvent(new Event("change"));
  }
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  resultCard.classList.add("hidden");
  statusCard.classList.remove("hidden");
  statusCard.scrollIntoView({ behavior: "smooth", block: "center" });
  setStatus("queued", "Starting upload…", 0);
  submitBtn.disabled = true;
  submitBtn.querySelector(".btn-label").textContent = "Working…";

  const file = videoInput.files?.[0];
  if (!file) return fail("No file selected.");

  if (file.size > 100 * 1024 * 1024) {
    // Large file → chunked upload (bypasses proxy body-size limits)
    chunkedUpload(file).catch((err) => {
      const msg = String(err);
      fail(msg.includes("Failed to fetch")
        ? "Cannot reach the server. Make sure "python app.py" is running, then reload and try again."
        : msg);
    });
  } else {
    // Small file → single-request upload with XHR progress
    directUpload(file);
  }
});

async function chunkedUpload(file) {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  const totalMb = (file.size / (1024 * 1024)).toFixed(0);

  // 1. Init session
  const initRes = await fetch("/api/upload/init", {
    method: "POST", credentials: "same-origin",
  });
  if (!initRes.ok) throw new Error(`Upload init failed: ${initRes.status}`);
  const { upload_id } = await initRes.json();

  // 2. Send chunks sequentially
  for (let i = 0; i < totalChunks; i++) {
    const chunk = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
    const sentMb = Math.min((i * CHUNK_SIZE) / (1024 * 1024), file.size / (1024 * 1024)).toFixed(0);
    const uiPct = Math.round(((i + 1) / totalChunks) * 25);
    setStatus("queued", `Uploading ${sentMb} / ${totalMb} MB (chunk ${i + 1}/${totalChunks})…`, uiPct);
    const res = await fetch(`/api/upload/chunk/${upload_id}/${i}`, {
      method: "PUT", body: chunk, credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Chunk ${i} failed: ${res.status}`);
  }

  // 3. Assemble
  setStatus("queued", "Assembling file on server…", 26);
  const asmRes = await fetch(`/api/upload/assemble/${upload_id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: file.name }),
    credentials: "same-origin",
  });
  if (!asmRes.ok) throw new Error(`Assembly failed: ${asmRes.status}`);

  // 4. Start the edit job (no file attachment — use upload_id)
  setStatus("queued", "Starting AI edit…", 28);
  const fd = new FormData(form);
  fd.delete("video");
  fd.set("upload_id", upload_id);
  const editRes = await fetch("/api/edit", {
    method: "POST", body: fd, credentials: "same-origin",
  });
  if (editRes.status === 401) {
    loginCard.classList.remove("hidden");
    appCard.classList.add("hidden");
    statusCard.classList.add("hidden");
    submitBtn.disabled = false;
    submitBtn.querySelector(".btn-label").textContent = "Edit my video";
    return;
  }
  if (!editRes.ok) throw new Error(`Edit start failed: ${editRes.status} ${await editRes.text()}`);
  const { job_id } = await editRes.json();
  poll(job_id);
}

function directUpload(file) {
  // XMLHttpRequest gives us upload.onprogress; fetch doesn't.
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/edit");
  xhr.withCredentials = true;

  let lastShown = 0;
  xhr.upload.addEventListener("progress", (ev) => {
    if (!ev.lengthComputable) return;
    const loadedMb = (ev.loaded / (1024 * 1024)).toFixed(0);
    const totalMb = (ev.total / (1024 * 1024)).toFixed(0);
    const uiPct = Math.min(25, Math.round((ev.loaded / ev.total) * 25));
    if (uiPct !== lastShown) {
      lastShown = uiPct;
      setStatus("queued", `Uploading ${loadedMb} / ${totalMb} MB`, uiPct);
    }
  });

  xhr.addEventListener("load", () => {
    if (xhr.status === 401) {
      loginCard.classList.remove("hidden");
      appCard.classList.add("hidden");
      statusCard.classList.add("hidden");
      submitBtn.disabled = false;
      submitBtn.querySelector(".btn-label").textContent = "Edit my video";
      return;
    }
    if (xhr.status < 200 || xhr.status >= 300) {
      return fail(`Server: ${xhr.status} ${xhr.responseText}`);
    }
    try {
      const { job_id } = JSON.parse(xhr.responseText);
      setStatus("queued", "Upload complete. Server processing…", 28);
      poll(job_id);
    } catch (err) {
      fail(`Bad server response: ${err.message}`);
    }
  });

  xhr.addEventListener("error", () => fail("Cannot reach the server. Make sure "python app.py" is running, then reload and try again."));
  xhr.addEventListener("abort", () => fail("Upload aborted."));
  xhr.addEventListener("timeout", () => fail("Upload timed out."));

  const fd = new FormData(form);
  xhr.send(fd);
}

async function poll(jobId) {
  let consecutive5xx = 0;
  while (true) {
    await new Promise((r) => setTimeout(r, 1500));
    let res;
    try {
      res = await fetch(`/api/jobs/${jobId}`, { credentials: "same-origin" });
    } catch (err) {
      // Network blip — give it a few tries before giving up.
      if (++consecutive5xx > 5) return fail("Lost the connection to the server.");
      continue;
    }
    if (res.status === 404) {
      return fail(
        "The server restarted and your job was lost. " +
          "Please re-upload your video.",
      );
    }
    if (res.status === 502 || res.status === 503 || res.status === 504) {
      // Bad gateway / unavailable — the container is dead or restarting.
      // Most common cause is OOM during transcription. Don't poll forever.
      if (++consecutive5xx > 8) {
        return fail(
          `The server became unreachable (${res.status}). Most likely it ran ` +
            "out of memory during transcription or rendering. Try a shorter " +
            "video, set WHISPER_MODEL=tiny in your environment, or upgrade " +
            "your hosting plan.",
        );
      }
      continue;
    }
    if (!res.ok) return fail(`Lost the job: ${res.status}`);
    consecutive5xx = 0;
    const job = await res.json();
    setStatus(job.status, job.message || "", job.progress || 0);
    if (job.status === "done") return showResult(jobId, job.result);
    if (job.status === "error") return fail(job.error || "Unknown error", jobId);
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

let _retryJobId = null;

function fail(msg, jobId) {
  submitBtn.disabled = false;
  submitBtn.querySelector(".btn-label").textContent = "Edit my video";
  setStatus("error", msg, 100);

  // Show Retry button when the server restarted mid-job (video still on disk).
  const retryBlock = $("retryBlock");
  if (retryBlock) {
    const canRetry = jobId && msg && msg.includes("Server restarted");
    retryBlock.classList.toggle("hidden", !canRetry);
    if (canRetry) _retryJobId = jobId;
  }
}

$("retryBtn")?.addEventListener("click", async () => {
  if (!_retryJobId) return;
  $("retryBlock")?.classList.add("hidden");
  statusCard.classList.remove("hidden");
  setStatus("queued", "Retrying with existing file…", 5);
  submitBtn.disabled = true;
  submitBtn.querySelector(".btn-label").textContent = "Working…";
  try {
    const res = await fetch(`/api/retry/${_retryJobId}`, {
      method: "POST", credentials: "same-origin",
    });
    if (!res.ok) {
      const txt = await res.text();
      return fail(txt.includes("no longer on disk")
        ? "Source video was deleted — please re-upload."
        : `Retry failed: ${res.status}`);
    }
    const { job_id } = await res.json();
    poll(job_id);
  } catch (err) {
    fail(`Retry error: ${err.message}`);
  }
});

function showResult(jobId, result) {
  submitBtn.disabled = false;
  submitBtn.querySelector(".btn-label").textContent = "Edit another";
  resultCard.classList.remove("hidden");
  resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
  player.src = `/api/download/${jobId}`;
  downloadLink.href = `/api/download/${jobId}`;
  const pkg = result?.packaging || {};
  pkgTitle.textContent = pkg.title || result?.titres_ctr?.[0] || "—";
  pkgThumb.textContent = result?.thumbnail_mot || pkg.thumbnail_word || "—";
  pkgEnd.textContent = pkg.end_caption || "—";

  // Show CTR titles if available
  const titres = result?.titres_ctr || [];
  if (titres.length && $("ctrTitles")) {
    $("ctrTitles").innerHTML = titres.map((t, i) =>
      `<div class="ctr-title"><span class="ctr-num">${i + 1}</span>${t}</div>`
    ).join("");
    $("ctrBlock")?.classList.remove("hidden");
  }

  planJson.textContent = JSON.stringify(result?.plan ?? {}, null, 2);
}
