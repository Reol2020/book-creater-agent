"use client";

import { useState } from "react";
import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Project } from "@/lib/api/endpoints/projects";
import { InspectorSection } from "./section";
import { OverviewDialog } from "./edit-dialogs";

interface Props {
  project: Project;
  isOpen: boolean;
  onUpdated: (p: Project) => void;
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      {value ? (
        <div
          className={
            "mt-1 whitespace-pre-wrap text-[13px] leading-relaxed text-foreground/90 " +
            (mono ? "font-mono text-[12px]" : "")
          }
        >
          {value.length > 240 ? value.slice(0, 240) + "…" : value}
        </div>
      ) : (
        <div className="mt-1 text-[13px] text-muted-foreground/70 italic">未填写</div>
      )}
    </div>
  );
}

export function OverviewInspectorSection({ project, isOpen, onUpdated }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <InspectorSection sectionKey="overview" title="概览" isOpen={isOpen}>
        <div className="space-y-3">
          <Field label="类型" value={project.genre} />
          <Field label="简介" value={project.synopsis} />
          <Field label="风格" value={project.style} />
          <Field label="大纲" value={project.outline} mono />
          <Button
            size="sm"
            variant="outline"
            className="w-full"
            onClick={() => setOpen(true)}
          >
            <Pencil className="mr-1.5 h-3.5 w-3.5" />
            完整编辑
          </Button>
        </div>
      </InspectorSection>

      <OverviewDialog
        open={open}
        onOpenChange={setOpen}
        project={project}
        onSaved={onUpdated}
      />
    </>
  );
}
