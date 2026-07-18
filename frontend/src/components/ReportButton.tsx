import { useState } from "react";

export default function ReportButton() {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "done">("idle");

  function handleOpen() {
    setMessage("");
    setStatus("idle");
    setOpen(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setStatus("sending");
    try {
      await fetch("/api/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          message: message.trim(),
          url: window.location.href,
          user_agent: navigator.userAgent,
        }),
      });
    } catch {
      // fire-and-forget — show success regardless
    }
    setStatus("done");
    setTimeout(() => setOpen(false), 2500);
  }

  return (
    <>
      <button
        onClick={handleOpen}
        title="Signaler un problème"
        aria-label="Signaler un problème"
        style={{
          position: "fixed",
          bottom: "1.5rem",
          right: "1.5rem",
          zIndex: 9990,
          width: "36px",
          height: "36px",
          borderRadius: "50%",
          background: "rgba(26,26,26,0.92)",
          border: "1px solid rgba(255,255,255,0.1)",
          color: "rgba(245,245,246,0.4)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "15px",
          fontWeight: 700,
          backdropFilter: "blur(8px)",
          boxShadow: "0 2px 12px rgba(0,0,0,0.5)",
          transition: "color 0.15s, border-color 0.15s, background 0.15s",
          lineHeight: 1,
        }}
        onMouseEnter={e => {
          const b = e.currentTarget;
          b.style.color = "#F5F5F6";
          b.style.borderColor = "rgba(255,255,255,0.22)";
          b.style.background = "rgba(36,36,36,0.96)";
        }}
        onMouseLeave={e => {
          const b = e.currentTarget;
          b.style.color = "rgba(245,245,246,0.4)";
          b.style.borderColor = "rgba(255,255,255,0.1)";
          b.style.background = "rgba(26,26,26,0.92)";
        }}
      >
        !
      </button>

      {open && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9991,
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "flex-end",
            padding: "1.5rem",
          }}
          onClick={() => setOpen(false)}
        >
          <div
            style={{
              background: "#1a1a1a",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "14px",
              padding: "18px",
              width: "100%",
              maxWidth: "300px",
              boxShadow: "0 8px 40px rgba(0,0,0,0.7)",
              marginBottom: "3rem",
            }}
            onClick={e => e.stopPropagation()}
          >
            {status === "done" ? (
              <p style={{
                textAlign: "center",
                color: "#F5F5F6",
                fontSize: "14px",
                fontWeight: 600,
                padding: "8px 0",
              }}>
                Merci, on regarde ça.
              </p>
            ) : (
              <form onSubmit={handleSubmit}>
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "10px",
                }}>
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "#F5F5F6" }}>
                    Signaler un problème
                  </span>
                  <button
                    type="button"
                    onClick={() => setOpen(false)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "rgba(245,245,246,0.4)",
                      cursor: "pointer",
                      fontSize: "18px",
                      lineHeight: 1,
                      padding: "0 2px",
                    }}
                  >
                    ×
                  </button>
                </div>

                <textarea
                  autoFocus
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  placeholder="Décrivez le problème…"
                  rows={4}
                  style={{
                    width: "100%",
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "8px",
                    padding: "9px 11px",
                    color: "#F5F5F6",
                    fontSize: "13px",
                    resize: "none",
                    outline: "none",
                    lineHeight: 1.6,
                    marginBottom: "10px",
                    fontFamily: "inherit",
                    display: "block",
                  }}
                />

                <button
                  type="submit"
                  disabled={status === "sending" || !message.trim()}
                  style={{
                    width: "100%",
                    background: status === "sending" || !message.trim()
                      ? "rgba(255,119,81,0.45)"
                      : "#FF7751",
                    color: "#fff",
                    border: "none",
                    borderRadius: "8px",
                    padding: "9px",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: status === "sending" || !message.trim() ? "not-allowed" : "pointer",
                    transition: "background 0.15s",
                  }}
                >
                  {status === "sending" ? "Envoi…" : "Envoyer"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
