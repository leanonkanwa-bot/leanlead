import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Lead } from "../lib/api";

interface Props {
  lead: Lead;
  onClick: () => void;
}

const platformIcon: Record<string, string> = {
  instagram: "📸",
  twitter: "🐦",
  linkedin: "💼",
  tiktok: "🎵",
};

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 8 ? "bg-emerald-900 text-emerald-400" :
    score >= 5 ? "bg-amber-900 text-amber-400" :
    "bg-red-900 text-red-400";
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-mono font-bold ${color}`}>
      {score.toFixed(1)}
    </span>
  );
}

export default function LeadCard({ lead, onClick }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: lead.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className="bg-slate-800 border border-slate-700 hover:border-slate-500 rounded-xl p-4 cursor-pointer select-none transition-colors group"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-white truncate">{lead.name || "—"}</p>
          <p className="text-xs text-slate-500 truncate">
            {platformIcon[lead.platform] || "👤"} @{lead.handle}
          </p>
        </div>
        {lead.qualification_score > 0 && <ScoreBadge score={lead.qualification_score} />}
      </div>

      {/* Bio snippet */}
      {lead.bio && (
        <p className="text-xs text-slate-400 line-clamp-2 mb-3">{lead.bio}</p>
      )}

      {/* Pain points */}
      {lead.pain_points?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {lead.pain_points.slice(0, 2).map((p) => (
            <span key={p} className="text-[10px] bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded-full">
              {p}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-[11px] text-slate-600 mt-1">
        <span>{lead.followers > 0 ? `${lead.followers.toLocaleString()} followers` : ""}</span>
        {lead.airtable_record_id && <span className="text-emerald-700">✦ Airtable</span>}
      </div>
    </div>
  );
}
