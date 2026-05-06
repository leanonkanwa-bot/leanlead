import { useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Lead, Stage } from "../lib/api";
import { leadsApi } from "../lib/api";
import LeadCard from "./LeadCard";
import LeadModal from "./LeadModal";

/* ── Stage config ── */
const STAGES: {
  id: Stage;
  label: string;
  border: string;
  dot: string;
  description: string;
}[] = [
  { id: "new",       label: "New",       border: "border-slate-700",   dot: "bg-slate-500",   description: "Just added, not yet contacted" },
  { id: "contacted", label: "Contacted", border: "border-sky-800",     dot: "bg-sky-500",     description: "DM sent, waiting for reply" },
  { id: "replied",   label: "Replied",   border: "border-violet-800",  dot: "bg-violet-500",  description: "Lead has responded" },
  { id: "booked",    label: "Booked",    border: "border-emerald-800", dot: "bg-emerald-500", description: "Call booked on Calendly" },
  { id: "closed",    label: "Closed",    border: "border-rose-900",    dot: "bg-rose-600",    description: "Deal won or lost" },
];

/* ── Column ── */
function Column({
  stage, leads, onCardClick,
}: {
  stage: typeof STAGES[0];
  leads: Lead[];
  onCardClick: (l: Lead) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id });

  const avgScore = leads.length
    ? (leads.reduce((s, l) => s + (l.qualification_score || 0), 0) / leads.length).toFixed(1)
    : null;

  return (
    <div className={`flex flex-col rounded-2xl border ${stage.border} bg-slate-900/50 min-w-[250px] w-[250px] flex-shrink-0`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${stage.dot}`} />
          <span className="text-xs font-bold text-slate-300 uppercase tracking-widest">{stage.label}</span>
        </div>
        <div className="flex items-center gap-2">
          {avgScore && (
            <span className="text-[10px] text-slate-600 font-mono">{avgScore} avg</span>
          )}
          <span className="text-xs bg-slate-800 text-slate-500 px-2 py-0.5 rounded-full">{leads.length}</span>
        </div>
      </div>

      {/* Drop zone */}
      <div
        ref={setNodeRef}
        className={`flex-1 p-3 space-y-2 min-h-[120px] rounded-b-2xl transition-colors ${
          isOver ? "bg-slate-800/40 ring-1 ring-inset ring-sky-800/40" : ""
        }`}
      >
        <SortableContext items={leads.map(l => l.id)} strategy={verticalListSortingStrategy}>
          {leads.map(lead => (
            <LeadCard key={lead.id} lead={lead} onClick={() => onCardClick(lead)} />
          ))}
        </SortableContext>
        {leads.length === 0 && (
          <div className="h-16 rounded-xl border border-dashed border-slate-800 flex items-center justify-center">
            <p className="text-[10px] text-slate-700">{stage.description}</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Board ── */
export default function KanbanBoard({ leads }: { leads: Lead[] }) {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Lead | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const moveStage = useMutation({
    mutationFn: ({ id, stage }: { id: number; stage: Stage }) =>
      leadsApi.update(id, { stage }),
    onMutate: async ({ id, stage }) => {
      await qc.cancelQueries({ queryKey: ["leads"] });
      const prev = qc.getQueryData<Lead[]>(["leads"]);
      qc.setQueryData<Lead[]>(["leads"], old =>
        old?.map(l => l.id === id ? { ...l, stage } : l) ?? []
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => ctx?.prev && qc.setQueryData(["leads"], ctx.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: ["leads"] }),
  });

  const activeLead = activeId ? leads.find(l => l.id === activeId) : null;

  function onDragStart({ active }: DragStartEvent) {
    setActiveId(active.id as number);
  }

  function onDragEnd({ active, over }: DragEndEvent) {
    setActiveId(null);
    if (!over) return;
    const lead = leads.find(l => l.id === active.id);
    if (!lead) return;
    const newStage =
      STAGES.find(s => s.id === over.id)?.id ??
      leads.find(l => l.id === over.id)?.stage;
    if (newStage && newStage !== lead.stage) {
      moveStage.mutate({ id: lead.id, stage: newStage });
    }
  }

  return (
    <>
      <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin h-full items-start">
          {STAGES.map(stage => (
            <Column
              key={stage.id}
              stage={stage}
              leads={leads.filter(l => l.stage === stage.id)}
              onCardClick={setSelected}
            />
          ))}
        </div>
        <DragOverlay dropAnimation={null}>
          {activeLead && (
            <div className="rotate-1 opacity-90 w-[250px]">
              <LeadCard lead={activeLead} onClick={() => {}} />
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {selected && (
        <LeadModal
          lead={leads.find(l => l.id === selected.id) ?? selected}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
