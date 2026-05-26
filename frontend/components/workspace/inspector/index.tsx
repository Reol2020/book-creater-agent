"use client";

import { useState } from "react";
import { FileText, Globe2, LayoutPanelLeft, UserCircle } from "lucide-react";

import { Accordion } from "@/components/ui/accordion";
import type { Project } from "@/lib/api/endpoints/projects";
import {
  type InspectorSectionKey,
  useInspectorChanges,
} from "@/lib/store/inspector-changes";
import { cn } from "@/lib/utils";

import { OverviewInspectorSection } from "./overview-section";
import { ChaptersInspectorSection } from "./chapters-section";
import { CharactersInspectorSection } from "./characters-section";
import { WorldInspectorSection } from "./world-section";

interface Props {
  project: Project;
  collapsed: boolean;
  onProjectUpdated: (p: Project) => void;
  onExpand: () => void;
}

const DEFAULT_OPEN: InspectorSectionKey[] = ["overview", "chapters"];

export function Inspector({
  project,
  collapsed,
  onProjectUpdated,
  onExpand,
}: Props) {
  const [openKeys, setOpenKeys] = useState<string[]>(DEFAULT_OPEN);

  if (collapsed) {
    return <CollapsedRail onExpand={onExpand} />;
  }

  return (
    <aside className="flex h-full w-[360px] shrink-0 flex-col border-l border-border/60 bg-muted/10">
      <div className="border-b border-border/60 px-4 py-2.5">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
          <LayoutPanelLeft className="h-3.5 w-3.5" />
          项目状态
        </div>
      </div>
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <Accordion
          type="multiple"
          value={openKeys}
          onValueChange={setOpenKeys}
        >
          <OverviewInspectorSection
            project={project}
            isOpen={openKeys.includes("overview")}
            onUpdated={onProjectUpdated}
          />
          <ChaptersInspectorSection
            projectId={project.id}
            isOpen={openKeys.includes("chapters")}
          />
          <CharactersInspectorSection
            projectId={project.id}
            isOpen={openKeys.includes("characters")}
          />
          <WorldInspectorSection
            projectId={project.id}
            isOpen={openKeys.includes("world")}
          />
        </Accordion>
      </div>
    </aside>
  );
}

function CollapsedRail({ onExpand }: { onExpand: () => void }) {
  const { unread } = useInspectorChanges();

  const items: { key: InspectorSectionKey; icon: React.ReactNode; label: string }[] = [
    { key: "overview", icon: <LayoutPanelLeft className="h-4 w-4" />, label: "概览" },
    { key: "chapters", icon: <FileText className="h-4 w-4" />, label: "章节" },
    { key: "characters", icon: <UserCircle className="h-4 w-4" />, label: "人物" },
    { key: "world", icon: <Globe2 className="h-4 w-4" />, label: "世界观" },
  ];

  return (
    <aside className="flex h-full w-9 shrink-0 flex-col items-center gap-1 border-l border-border/60 bg-muted/10 py-3">
      {items.map((it) => (
        <button
          key={it.key}
          type="button"
          onClick={onExpand}
          title={it.label + (unread.has(it.key) ? " · 有更新" : "")}
          className={cn(
            "relative flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground",
          )}
        >
          {it.icon}
          {unread.has(it.key) && (
            <span className="absolute right-0.5 top-0.5 h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          )}
        </button>
      ))}
    </aside>
  );
}
