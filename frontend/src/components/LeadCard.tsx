import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Lead } from "../lib/api";

const PLATFORM: Record<string, string> = {
  instagram: "📸", tiktok: "🎵", twitter: "𝕏", linkedin: "💼",
};

function Score({ v }: { v: number }) {
  if (!v) return null;
  const cls = v >= 8 ? "text-emerald-400" : v >= 6 ? "text-amber-400" : "text-red-400";
  const dot = v >= 8 ? "bg-emerald-500" : v >= 6 ? "bg-amber-500" : "bg-red-500";
  return (
    <span className={`flex items-center gap-1 text-[10px] font-mono font-bold ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {v.toFixed(1)}
    </span>
  );
}

export default function LeadCard({ lead, onClick }: { lead: Lead; onClick: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: lead.id });

  const followupDue = lead.stage === "contacted" && lead.messaged_at && !lead.reply_received;

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.3 : 1 }}
      {...attributes} {...listeners}
      onClick={onClick}
      className="bg-slate-800 border border-slate-700 hover:border-slate-500 rounded-xl p-3.5 cursor-pointer select-none transition-all"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white truncate">{lead.name || `@${lead.handle}`}</p>
          <p className="text-[11px] text-slate-500 truncate mt-0.5">
            {PLATFORM[lead.platform] || "👤"} @{lead.handle}
          </p>
        </div>
        <Score v={lead.qualification_score} />
      </div>

      {/* Bio */}
      {lead.bio && (
        <p className="text-[11px] text-slate-400 line-clamp-2 mb-2.5 leading-relaxed">{lead.bio}</p>
      )}

      {/* Pain point tags */}
      {lead.pain_points?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2.5">
          {lead.pain_points.slice(0, 2).map(p => (
            <span key={p} className="text-[9px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded-full">{p}</span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-0.5">
        <span className="text-[10px] text-slate-600">
          {lead.followers > 0 ? `${lead.followers.toLocaleString()} followers` : ""}
        </span>
        <div className="flex gap-2 items-center">
          {followupDue && (
            <span className="text-[9px] bg-amber-950 text-amber-400 border border-amber-900/60 px-1.5 py-0.5 rounded-full">follow-up due</span>
          )}
          {lead.airtable_record_id && <span className="text-[9px] text-emerald-700">✦</span>}
        </div>
      </div>
    </div>
  );
}
