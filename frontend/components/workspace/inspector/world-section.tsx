"use client";

import { useEffect, useState } from "react";
import { Globe2, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { worldApi, type WorldEntry } from "@/lib/api/endpoints/world";
import { useDataChanged } from "@/lib/hooks/use-data-changed";
import { InspectorSection } from "./section";
import { WorldDialog } from "./edit-dialogs";

interface Props {
  projectId: string;
  isOpen: boolean;
}

export function WorldInspectorSection({ projectId, isOpen }: Props) {
  const [items, setItems] = useState<WorldEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [editing, setEditing] = useState<WorldEntry | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      setItems(await worldApi.list(projectId));
      setLoaded(true);
    } catch (e) {
      toast.error("加载世界观失败", { description: String(e) });
    } finally {
      setLoading(false);
    }
  }

  // 懒加载:首次展开时才拉
  useEffect(() => {
    if (isOpen && !loaded && !loading) {
      reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, loaded, projectId]);

  useDataChanged(projectId, ["tree"], async () => {
    if (loaded) await reload();
  });

  function startCreate() {
    setEditing({ id: "", project_id: projectId, title: "", category: "", content: "" });
    setDialogOpen(true);
  }

  return (
    <>
      <InspectorSection
        sectionKey="world"
        title="世界观"
        count={items.length}
        isOpen={isOpen}
      >
        <div className="space-y-1">
          {loading && (
            <div className="text-xs text-muted-foreground">加载中…</div>
          )}
          {!loading && items.length === 0 && (
            <div className="text-xs text-muted-foreground/80 leading-relaxed">
              还没有条目
            </div>
          )}
          {items.map((w) => (
            <button
              key={w.id}
              type="button"
              onClick={() => {
                setEditing(w);
                setDialogOpen(true);
              }}
              className="flex w-full items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left text-sm transition-colors hover:border-border hover:bg-accent/40"
            >
              <Globe2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1 truncate font-medium">{w.title}</span>
              {w.category && (
                <span className="truncate text-[11px] text-muted-foreground">
                  {w.category}
                </span>
              )}
            </button>
          ))}
          <Button
            size="sm"
            variant="ghost"
            className="mt-1 w-full justify-start text-muted-foreground"
            onClick={startCreate}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            新增条目
          </Button>
        </div>
      </InspectorSection>

      <WorldDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        projectId={projectId}
        initial={editing}
        onSaved={(w) =>
          setItems((prev) => {
            const idx = prev.findIndex((x) => x.id === w.id);
            if (idx >= 0) {
              const copy = [...prev];
              copy[idx] = w;
              return copy;
            }
            return [...prev, w];
          })
        }
        onDeleted={(id) => setItems((prev) => prev.filter((x) => x.id !== id))}
      />
    </>
  );
}
