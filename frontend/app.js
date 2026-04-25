const form = document.getElementById("form");
const submitBtn = document.getElementById("submit");
const dropLabel = document.getElementById("dropLabel");
const videoInput = document.getElementById("video");
const statusCard = document.getElementById("statusCard");
const statusLabel = document.getElementById("statusLabel");
const statusMsg = document.getElementById("statusMsg");
const barFill = document.getElementById("barFill");
const resultCard = document.getElementById("resultCard");
const player = document.getElementById("player");
const downloadLink = document.getElementById("downloadLink");
const pkgTitle = document.getElementById("pkgTitle");
const pkgThumb = document.getElementById("pkgThumb");
const pkgEnd = document.getElementById("pkgEnd");
const planJson = document.getElementById("planJson");

videoInput.addEventListener("change", () => {
  const f = videoInput.files?.[0];
  if (f) dropLabel.textContent = `${f.name} — ${(f.size / (1024 * 1024)).toFixed(1)} MB`;
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  resultCard.classList.add("hidden");
  statusCard.classList.remove("hidden");
  setStatus("queued", "Uploading…", 5);
  submitBtn.disabled = true;

  const fd = new FormData(form);
  let res;
  try {
    res = await fetch("/api/edit", { method: "POST", body: fd });
  } catch (err) {
    return fail(`Upload failed: ${err.message}`);
  }
  if (!res.ok) return fail(`Server: ${res.status} ${await res.text()}`);
  const { job_id } = await res.json();
  poll(job_id);
});

async function poll(jobId) {
  while (true) {
    await new Promise((r) => setTimeout(r, 1500));
    const res = await fetch(`/api/jobs/${jobId}`);
    if (!res.ok) return fail(`Lost the job: ${res.status}`);
    const job = await res.json();
    setStatus(job.status, job.message || "", job.progress || 0);
    if (job.status === "done") return showResult(jobId, job.result);
    if (job.status === "error") return fail(job.error || "Unknown error");
  }
}

function setStatus(status, message, progress) {
  const labels = {
    queued: "Queued",
    transcribing: "Transcribing",
    planning: "Planning the edit",
    rendering: "Rendering",
    done: "Done",
    error: "Error",
  };
  statusLabel.textContent = labels[status] || status;
  statusMsg.textContent = message;
  barFill.style.width = `${progress}%`;
  if (status === "error") barFill.style.background = "var(--err)";
  else barFill.style.background = "var(--accent)";
}

function fail(msg) {
  submitBtn.disabled = false;
  setStatus("error", msg, 100);
}

function showResult(jobId, result) {
  submitBtn.disabled = false;
  resultCard.classList.remove("hidden");
  player.src = `/api/download/${jobId}`;
  downloadLink.href = `/api/download/${jobId}`;
  const pkg = result?.packaging || {};
  pkgTitle.textContent = pkg.title || "—";
  pkgThumb.textContent = pkg.thumbnail_word || "—";
  pkgEnd.textContent = pkg.end_caption || "—";
  planJson.textContent = JSON.stringify(result?.plan ?? {}, null, 2);
}
