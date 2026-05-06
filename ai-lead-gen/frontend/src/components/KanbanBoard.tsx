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

const STAGES: { id: Stage; label: string; color: string; dot: string }[] = [
  { id: "new",       label: "New",       color: "border-slate-700", dot: "bg-slate-500" },
  { id: "contacted", label: "Contacted", color: "border-sky-800",   dot: "bg-sky-500" },
  { id: "replied",   label: "Replied",   color: "border-violet-800",dot: "bg-violet-500" },
  { id: "booked",    label: "Booked",    color: "border-emerald-800",dot: "bg-emerald-500" },
  { id: "closed",    label: "Closed",    color: "border-rose-900",  dot: "bg-rose-600" },
];

function Column({
  stage,
  leads,
  onCardClick,
}: {
  stage: (typeof STAGES)[0];
  leads: Lead[];
  onCardClick: (lead: Lead) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id });
  const total = leads.length;
  const avgScore = total
    ? (leads.reduce((s, l) => s + (l.qualification_score || 0), 0) / total).toFixed(1)
    : null;

  return (
    <div className={`flex flex-col rounded-2xl border ${stage.color} bg-slate-900/50 min-w-[255px] w-[255px] flex-shrink-0`}>
      {/* Column header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${stage.dot}`} />
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">{stage.label}</span>
        </div>
        <div className="flex items-center gap-2">
          {avgScore && <span className="text-[10px] text-slate-600 font-mono">{avgScore} avg</span>}
          <span className="text-xs text-slate-600 bg-slate-800 px-2 py-0.5 rounded-full">{total}</span>
        </div>
      </div>

      {/* Drop zone */}
      <div
        ref={setNodeRef}
        className={`flex-1 p-3 space-y-2 min-h-[140px] transition-colors rounded-b-2xl ${
          isOver ? "bg-slate-800/40 ring-1 ring-inset ring-sky-800/50" : ""
        }`}
      >
        <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
          {leads.map((lead) => (
            <LeadCard key={lead.id} lead={lead} onClick={() => onCardClick(lead)} />
          ))}
        </SortableContext>
        {leads.length === 0 && (
          <div className="h-20 rounded-xl border border-dashed border-slate-800 flex items-center justify-center">
            <p className="text-[10px] text-slate-700">Drop leads here</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface Props {
  leads: Lead[];
}

export default function KanbanBoard({ leads }: Props) {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const updateStage = useMutation({
    mutationFn: ({ id, stage }: { id: number; stage: Stage }) =>
      leadsApi.update(id, { stage }),
    onMutate: async ({ id, stage }) => {
      await qc.cancelQueries({ queryKey: ["leads"] });
      const prev = qc.getQueryData<Lead[]>(["leads"]);
      qc.setQueryData<Lead[]>(["leads"], (old) =>
        old?.map((l) => (l.id === id ? { ...l, stage } : l)) ?? []
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => ctx?.prev && qc.setQueryData(["leads"], ctx.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: ["leads"] }),
  });

  const activeLead = activeId ? leads.find((l) => l.id === activeId) ?? null : null;

  function handleDragStart(e: DragStartEvent) {
    setActiveId(e.active.id as number);
  }

  function handleDragEnd(e: DragEndEvent) {
    setActiveId(null);
    const { active, over } = e;
    if (!over) return;
    const lead = leads.find((l) => l.id === active.id);
    if (!lead) return;
    const newStage =
      STAGES.find((s) => s.id === over.id)?.id ??
      leads.find((l) => l.id === over.id)?.stage;
    if (newStage && newStage !== lead.stage) {
      updateStage.mutate({ id: lead.id, stage: newStage });
    }
  }

  const byStage = (stage: Stage) => leads.filter((l) => l.stage === stage);

  return (
    <>
      <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin h-full">
          {STAGES.map((stage) => (
            <Column
              key={stage.id}
              stage={stage}
              leads={byStage(stage.id)}
              onCardClick={setSelectedLead}
            />
          ))}
        </div>
        <DragOverlay dropAnimation={null}>
          {activeLead && (
            <div className="rotate-1 opacity-90 w-[255px]">
              <LeadCard lead={activeLead} onClick={() => {}} />
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {selectedLead && (
        <LeadModal
          lead={leads.find((l) => l.id === selectedLead.id) ?? selectedLead}
          onClose={() => setSelectedLead(null)}
        />
      )}
    </>
  );
}
