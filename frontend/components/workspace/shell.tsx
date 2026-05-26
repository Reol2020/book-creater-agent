"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, PanelRightClose, PanelRightOpen } from "lucide-react";

import { AppHeader } from "@/components/app-header";
import { Button } from "@/components/ui/button";
import type { Project } from "@/lib/api/endpoints/projects";
import { InspectorChangesProvider } from "@/lib/store/inspector-changes";
import { cn } from "@/lib/utils";

import { AssistantPanel } from "./assistant-panel";
import { Inspector } from "./inspector";
import { ReaderModal } from "./reader/reader-modal";

const COLLAPSE_STORAGE_KEY = "workspace.inspector.collapsed";

interface Props {
  project: Project;
  onProjectUpdated: (p: Project) => void;
}

export function WorkspaceShell({ project, onProjectUpdated }: Props) {
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const [readerOpen, setReaderOpen] = useState(false);

  // 初始化:小屏默认折叠;localStorage 记忆
  useEffect(() => {
    const saved = window.localStorage.getItem(COLLAPSE_STORAGE_KEY);
    if (saved === "1") setCollapsed(true);
    else if (saved === "0") setCollapsed(false);
    else if (window.innerWidth < 768) setCollapsed(true);
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      window.localStorage.setItem(COLLAPSE_STORAGE_KEY, next ? "1" : "0");
      return next;
    });
  }

  return (
    <InspectorChangesProvider projectId={project.id}>
      <div className="flex h-screen flex-col">
        <AppHeader
          middle={
            <div className="flex items-center gap-2 min-w-0">
              <Link
                href="/"
                className="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                aria-label="返回主页"
              >
                <ArrowLeft className="h-4 w-4" />
              </Link>
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{project.name}</div>
                {project.genre && (
                  <div className="truncate text-xs text-muted-foreground">
                    {project.genre}
                  </div>
                )}
              </div>
              <div className="ml-3 flex items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setReaderOpen(true)}
                  className="h-7"
                >
                  <BookOpen className="mr-1.5 h-3.5 w-3.5" />
                  阅读
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={toggleCollapsed}
                  className="h-7"
                  title={collapsed ? "展开 Inspector" : "折叠 Inspector"}
                >
                  {collapsed ? (
                    <PanelRightOpen className="h-3.5 w-3.5" />
                  ) : (
                    <PanelRightClose className="h-3.5 w-3.5" />
                  )}
                </Button>
              </div>
            </div>
          }
        />

        <div className={cn("flex flex-1 overflow-hidden")}>
          <main className="flex min-w-0 flex-1 flex-col">
            <AssistantPanel project={project} />
          </main>
          <Inspector
            project={project}
            collapsed={collapsed}
            onProjectUpdated={onProjectUpdated}
            onExpand={() => {
              setCollapsed(false);
              window.localStorage.setItem(COLLAPSE_STORAGE_KEY, "0");
            }}
          />
        </div>

        <ReaderModal
          open={readerOpen}
          onOpenChange={setReaderOpen}
          projectId={project.id}
          projectName={project.name}
        />
      </div>
    </InspectorChangesProvider>
  );
}
