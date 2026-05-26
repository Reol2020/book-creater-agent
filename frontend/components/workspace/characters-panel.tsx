"use client";

import { useEffect, useState } from "react";
import { Plus, Users, Trash2 } from "lucide-react";
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
import { charactersApi, type Character } from "@/lib/api/endpoints/characters";
import { useDataChanged } from "@/lib/hooks/use-data-changed";

interface Props {
  projectId: string;
}

export function CharactersPanel({ projectId }: Props) {
  const [items, setItems] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Character | null>(null);
  const [open, setOpen] = useState(false);

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
    setOpen(true);
  }

  function startEdit(c: Character) {
    setEditing(c);
    setOpen(true);
  }

  async function onDelete(c: Character) {
    if (!window.confirm(`删除人物「${c.name}」?`)) return;
    try {
      await charactersApi.remove(projectId, c.id);
      setItems((prev) => prev.filter((x) => x.id !== c.id));
      toast.success("已删除");
    } catch (e) {
      toast.error("删除失败", { description: String(e) });
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6 md:p-8">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">人物</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            为每个角色记录身份、性格、目标与冲突,AI 创作时会引用
          </p>
        </div>
        <Button onClick={startCreate}>
          <Plus className="mr-1.5 h-4 w-4" />
          新增人物
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">加载中…</p>}

      {!loading && items.length === 0 && (
        <EmptyState
          icon={<Users className="h-5 w-5" />}
          title="还没有角色"
          description="主角、反派、关键配角都建议建一张卡"
          action={
            <Button onClick={startCreate}>
              <Plus className="mr-1.5 h-4 w-4" />
              添加第一个人物
            </Button>
          }
        />
      )}

      {items.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {items.map((c) => (
            <Card
              key={c.id}
              className="card-hover cursor-pointer"
              onClick={() => startEdit(c)}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-medium truncate">{c.name}</div>
                    {c.role && (
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {c.role}
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(c);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                {c.profile && (
                  <p className="mt-3 line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                    {c.profile}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CharacterDialog
        open={open}
        onOpenChange={setOpen}
        projectId={projectId}
        initial={editing}
        onSaved={(c) => {
          setItems((prev) => {
            const idx = prev.findIndex((x) => x.id === c.id);
            if (idx >= 0) {
              const copy = [...prev];
              copy[idx] = c;
              return copy;
            }
            return [...prev, c];
          });
        }}
      />
    </div>
  );
}

function CharacterDialog({
  open,
  onOpenChange,
  projectId,
  initial,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  projectId: string;
  initial: Character | null;
  onSaved: (c: Character) => void;
}) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [profile, setProfile] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(initial?.name ?? "");
    setRole(initial?.role ?? "");
    setProfile(initial?.profile ?? "");
  }, [initial]);

  async function onSave() {
    if (!name.trim()) {
      toast.error("人物名不能为空");
      return;
    }
    setSaving(true);
    try {
      const saved = await charactersApi.upsert(projectId, {
        id: initial?.id || undefined,
        name: name.trim(),
        role,
        profile,
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
          <DialogTitle>{initial?.id ? "编辑人物" : "新增人物"}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="grid gap-1.5">
              <Label>姓名 *</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label>角色定位</Label>
              <Input
                value={role}
                placeholder="主角 / 反派 / 配角 …"
                onChange={(e) => setRole(e.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label>详细设定</Label>
            <Textarea
              value={profile}
              rows={10}
              placeholder="外貌 / 身世 / 性格 / 动机 / 关系网 / 关键能力 …"
              onChange={(e) => setProfile(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={onSave} disabled={saving || !name.trim()}>
            {saving ? "保存中…" : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
