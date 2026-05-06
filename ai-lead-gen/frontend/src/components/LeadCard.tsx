import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Lead } from "../lib/api";

interface Props {
  lead: Lead;
  onClick: () => void;
}

const PLATFORM_ICON: Record<string, string> = {
  instagram: "📸",
  twitter: "𝕏",
  linkedin: "💼",
  tiktok: "🎵",
};

function ScoreDot({ score }: { score: number }) {
  if (!score) return null;
  const bg =
    score >= 8 ? "bg-emerald-500" :
    score >= 6 ? "bg-amber-500" : "bg-red-500";
  const label =
    score >= 8 ? "text-emerald-400" :
    score >= 6 ? "text-amber-400" : "text-red-400";
  return (
    <div className="flex items-center gap-1">
      <div className={`w-1.5 h-1.5 rounded-full ${bg}`} />
      <span className={`text-[10px] font-mono font-bold ${label}`}>{score.toFixed(1)}</span>
    </div>
  );
}

export default function LeadCard({ lead, onClick }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: lead.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  // Follow-up indicator
  const hasFollowupDue =
    lead.stage === "contacted" &&
    lead.messaged_at &&
    !lead.reply_received &&
    !lead.followup_d7_sent_at;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className="bg-slate-800 hover:bg-slate-750 border border-slate-700 hover:border-slate-500 rounded-xl p-3.5 cursor-pointer select-none transition-all group"
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white truncate leading-snug">
            {lead.name || `@${lead.handle}`}
          </p>
          <p className="text-[11px] text-slate-500 truncate mt-0.5">
            {PLATFORM_ICON[lead.platform] || "👤"} @{lead.handle}
          </p>
        </div>
        <ScoreDot score={lead.qualification_score} />
      </div>

      {/* Bio snippet */}
      {lead.bio && (
        <p className="text-[11px] text-slate-400 line-clamp-2 mb-2.5 leading-relaxed">
          {lead.bio}
        </p>
      )}

      {/* Pain point pills */}
      {lead.pain_points?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2.5">
          {lead.pain_points.slice(0, 2).map((p) => (
            <span key={p} className="text-[9px] bg-slate-700/80 text-slate-400 px-1.5 py-0.5 rounded-full">
              {p}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-600">
          {lead.followers > 0 ? `${lead.followers.toLocaleString()} followers` : ""}
        </span>
        <div className="flex items-center gap-2">
          {hasFollowupDue && (
            <span className="text-[9px] bg-amber-900/60 text-amber-400 px-1.5 py-0.5 rounded-full border border-amber-900/80">
              follow-up due
            </span>
          )}
          {lead.airtable_record_id && (
            <span className="text-[9px] text-emerald-700">✦</span>
          )}
        </div>
      </div>
    </div>
  );
}
