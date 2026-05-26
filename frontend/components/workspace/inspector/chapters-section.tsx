"use client";

import { useEffect, useState } from "react";
import { FileText, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { projectsApi, type Chapter } from "@/lib/api/endpoints/projects";
import { useDataChanged } from "@/lib/hooks/use-data-changed";
import { InspectorSection } from "./section";
import { ChapterDialog } from "./edit-dialogs";

interface Props {
  projectId: string;
  isOpen: boolean;
}

export function ChaptersInspectorSection({ projectId, isOpen }: Props) {
  const [items, setItems] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Chapter | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      setItems(await projectsApi.listChapters(projectId));
    } catch (e) {
      toast.error("加载章节失败", { description: String(e) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useDataChanged(projectId, ["tree", "doc"], reload);

  async function onCreate() {
    try {
      const idx = items.length + 1;
      const c = await projectsApi.createChapter(projectId, {
        title: `第 ${idx} 章`,
        order_index: idx,
      });
      setItems((prev) => [...prev, c]);
      setEditing(c);
      setDialogOpen(true);
    } catch (e) {
      toast.error("新增失败", { description: String(e) });
    }
  }

  return (
    <>
      <InspectorSection
        sectionKey="chapters"
        title="章节"
        count={items.length}
        isOpen={isOpen}
      >
        <div className="space-y-1">
          {loading && (
            <div className="text-xs text-muted-foreground">加载中…</div>
          )}
          {!loading && items.length === 0 && (
            <div className="text-xs text-muted-foreground/80 leading-relaxed">
              还没有章节
            </div>
          )}
          {items.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => {
                setEditing(c);
                setDialogOpen(true);
              }}
              className="group flex w-full items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left text-sm transition-colors hover:border-border hover:bg-accent/40"
            >
              <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1 truncate">
                {c.title || "未命名章节"}
              </span>
              <span className="text-[11px] tabular-nums text-muted-foreground">
                {c.word_count.toLocaleString()}
              </span>
            </button>
          ))}
          <Button
            size="sm"
            variant="ghost"
            className="mt-1 w-full justify-start text-muted-foreground"
            onClick={onCreate}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            新增章节
          </Button>
        </div>
      </InspectorSection>

      <ChapterDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        projectId={projectId}
        chapter={editing}
        onSaved={(c) =>
          setItems((prev) => prev.map((x) => (x.id === c.id ? c : x)))
        }
        onDeleted={(id) => setItems((prev) => prev.filter((x) => x.id !== id))}
      />
    </>
  );
}
