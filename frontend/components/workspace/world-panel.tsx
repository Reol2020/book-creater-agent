"use client";

import { useEffect, useState } from "react";
import { Plus, Globe2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { worldApi, type WorldEntry } from "@/lib/api/endpoints/world";
import { useDataChanged } from "@/lib/hooks/use-data-changed";

interface Props {
  projectId: string;
}

export function WorldPanel({ projectId }: Props) {
  const [items, setItems] = useState<WorldEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<WorldEntry | null>(null);
  const [open, setOpen] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      setItems(await worldApi.list(projectId));
    } catch (e) {
      toast.error("加载世界观失败", { description: String(e) });
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
    setEditing({ id: "", project_id: projectId, title: "", category: "", content: "" });
    setOpen(true);
  }

  async function onDelete(w: WorldEntry) {
    if (!window.confirm(`删除条目「${w.title}」?`)) return;
    try {
      await worldApi.remove(projectId, w.id);
      setItems((prev) => prev.filter((x) => x.id !== w.id));
      toast.success("已删除");
    } catch (e) {
      toast.error("删除失败", { description: String(e) });
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6 md:p-8">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">世界观</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            地理 / 势力 / 体系 / 历史 / 设定细节,可分类整理
          </p>
        </div>
        <Button onClick={startCreate}>
          <Plus className="mr-1.5 h-4 w-4" />
          新增条目
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">加载中…</p>}

      {!loading && items.length === 0 && (
        <EmptyState
          icon={<Globe2 className="h-5 w-5" />}
          title="还没有世界观条目"
          description="可以从核心设定开始,例如能量体系、主要势力分布"
          action={
            <Button onClick={startCreate}>
              <Plus className="mr-1.5 h-4 w-4" />
              添加第一条
            </Button>
          }
        />
      )}

      {items.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {items.map((w) => (
            <Card
              key={w.id}
              className="card-hover cursor-pointer"
              onClick={() => {
                setEditing(w);
                setOpen(true);
              }}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-medium truncate">{w.title}</div>
                    {w.category && (
                      <div className="mt-0.5 inline-block rounded-full bg-accent px-2 py-0.5 text-[11px] text-accent-foreground">
                        {w.category}
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(w);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                {w.content && (
                  <p className="mt-3 line-clamp-3 text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                    {w.content}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <WorldEntryDialog
        open={open}
        onOpenChange={setOpen}
        projectId={projectId}
        initial={editing}
        onSaved={(w) => {
          setItems((prev) => {
            const idx = prev.findIndex((x) => x.id === w.id);
            if (idx >= 0) {
              const copy = [...prev];
              copy[idx] = w;
              return copy;
            }
            return [...prev, w];
          });
        }}
      />
    </div>
  );
}

function WorldEntryDialog({
  open,
  onOpenChange,
  projectId,
  initial,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  projectId: string;
  initial: WorldEntry | null;
  onSaved: (w: WorldEntry) => void;
}) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setTitle(initial?.title ?? "");
    setCategory(initial?.category ?? "");
    setContent(initial?.content ?? "");
  }, [initial]);

  async function onSave() {
    if (!title.trim()) {
      toast.error("标题不能为空");
      return;
    }
    setSaving(true);
    try {
      const saved = await worldApi.upsert(projectId, {
        id: initial?.id || undefined,
        title: title.trim(),
        category,
        content,
      });
      onSaved(saved);
      onOpenChange(false);
      toast.success("已保存");
    } catch (e) {
      toast.error("保存失败", { description: String(e) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{initial?.id ? "编辑条目" : "新增条目"}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="grid gap-1.5">
              <Label>标题 *</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label>分类</Label>
              <Input
                value={category}
                placeholder="设定 / 地理 / 势力 / 体系 …"
                onChange={(e) => setCategory(e.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label>正文</Label>
            <Textarea
              value={content}
              rows={12}
              placeholder="详细描述,可使用 markdown"
              onChange={(e) => setContent(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={onSave} disabled={saving || !title.trim()}>
            {saving ? "保存中…" : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
