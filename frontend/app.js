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
  document.querySelectorAll('a[href="#login"]').forEach((a) => { a.href = "#tool"; });
  appCard.scrollIntoView({ behavior: "smooth", block: "start" });
});

videoInput.addEventListener("change", () => {
  const f = videoInput.files?.[0];
  if (!f) return;
  dropLabel.textContent = `${f.name} — ${(f.size / (1024 * 1024)).toFixed(1)} MB`;
  drop.classList.add("has-file");
  if (f.size > 500 * 1024 * 1024) {
    const mb = (f.size / (1024 * 1024)).toFixed(0);
    if (!confirm(
      `This file is ${mb} MB — over the recommended 500 MB.\n\n` +
      `Upload alone may take 10+ minutes, then transcription + render ` +
      `on a shared CPU can take 1–3 hours.\n\nContinue anyway?`
    )) {
      videoInput.value = "";
      dropLabel.textContent = "Click or drop your raw video here";
      drop.classList.remove("has-file");
    }
  }
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

  // XMLHttpRequest gives us upload.onprogress; fetch doesn't.
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/edit");
  xhr.withCredentials = true;

  let lastShown = 0;
  xhr.upload.addEventListener("progress", (ev) => {
    if (!ev.lengthComputable) return;
    const loadedMb = ev.loaded / (1024 * 1024);
    const totalMb = ev.total / (1024 * 1024);
    const pctReal = ev.loaded / ev.total;
    // Reserve 0–25% of the visual bar for upload (transcribe/plan/render fill the rest).
    const uiPct = Math.min(25, Math.round(pctReal * 25));
    if (uiPct !== lastShown) {
      lastShown = uiPct;
      setStatus(
        "queued",
        `Uploading ${loadedMb.toFixed(0)} / ${totalMb.toFixed(0)} MB`,
        uiPct,
      );
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

  xhr.addEventListener("error", () => fail("Network error during upload."));
  xhr.addEventListener("abort", () => fail("Upload aborted."));
  xhr.addEventListener("timeout", () => fail("Upload timed out."));

  const fd = new FormData(form);
  xhr.send(fd);
});

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
