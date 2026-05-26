"use client";

import { useEffect, useState } from "react";
import { Plus, UserCircle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { charactersApi, type Character } from "@/lib/api/endpoints/characters";
import { useDataChanged } from "@/lib/hooks/use-data-changed";
import { InspectorSection } from "./section";
import { CharacterDialog } from "./edit-dialogs";

interface Props {
  projectId: string;
  isOpen: boolean;
}

export function CharactersInspectorSection({ projectId, isOpen }: Props) {
  const [items, setItems] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Character | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      setItems(await charactersApi.list(projectId));
    } catch (e) {
      toast.error("加载人物失败", { description: String(e) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useDataChanged(projectId, ["tree"], reload);

  function startCreate() {
    setEditing({ id: "", project_id: projectId, name: "", role: "", profile: "" });
    setDialogOpen(true);
  }

  return (
    <>
      <InspectorSection
        sectionKey="characters"
        title="人物"
        count={items.length}
        isOpen={isOpen}
      >
        <div className="space-y-1">
          {loading && (
            <div className="text-xs text-muted-foreground">加载中…</div>
          )}
          {!loading && items.length === 0 && (
            <div className="text-xs text-muted-foreground/80 leading-relaxed">
              还没有人物
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
              className="flex w-full items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left text-sm transition-colors hover:border-border hover:bg-accent/40"
            >
              <UserCircle className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1 truncate font-medium">{c.name}</span>
              {c.role && (
                <span className="truncate text-[11px] text-muted-foreground">
                  {c.role}
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
            新增人物
          </Button>
        </div>
      </InspectorSection>

      <CharacterDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        projectId={projectId}
        initial={editing}
        onSaved={(c) =>
          setItems((prev) => {
            const idx = prev.findIndex((x) => x.id === c.id);
            if (idx >= 0) {
              const copy = [...prev];
              copy[idx] = c;
              return copy;
            }
            return [...prev, c];
          })
        }
        onDeleted={(id) => setItems((prev) => prev.filter((x) => x.id !== id))}
      />
    </>
  );
}
