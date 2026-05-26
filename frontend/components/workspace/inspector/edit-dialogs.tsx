"use client";

import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  projectsApi,
  type Chapter,
  type Project,
} from "@/lib/api/endpoints/projects";
import {
  charactersApi,
  type Character,
} from "@/lib/api/endpoints/characters";
import { worldApi, type WorldEntry } from "@/lib/api/endpoints/world";

// ----- Project / Overview --------------------------------------------------

export function OverviewDialog({
  open,
  onOpenChange,
  project,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  project: Project;
  onSaved: (p: Project) => void;
}) {
  const [name, setName] = useState(project.name);
  const [genre, setGenre] = useState(project.genre);
  const [synopsis, setSynopsis] = useState(project.synopsis);
  const [style, setStyle] = useState(project.style);
  const [outline, setOutline] = useState(project.outline);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(project.name);
    setGenre(project.genre);
    setSynopsis(project.synopsis);
    setStyle(project.style);
    setOutline(project.outline);
  }, [open, project]);

  async function onSave() {
    if (!name.trim()) {
      toast.error("项目名不能为空");
      return;
    }
    setSaving(true);
    try {
      const updated = await projectsApi.update(project.id, {
        name: name.trim(),
        genre,
        synopsis,
        style,
        outline,
      });
      onSaved(updated);
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
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>编辑项目概览</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 max-h-[70vh] overflow-y-auto pr-1 scrollbar-thin">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="grid gap-1.5">
              <Label>项目名 *</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label>类型</Label>
              <Input
                value={genre}
                placeholder="玄幻 / 都市 / 科幻 …"
                onChange={(e) => setGenre(e.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label>简介</Label>
            <Textarea
              value={synopsis}
              rows={4}
              placeholder="一段话概括故事核心冲突与主题"
              onChange={(e) => setSynopsis(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label>写作风格</Label>
            <Textarea
              value={style}
              rows={4}
              placeholder="语言、节奏、视角偏好"
              onChange={(e) => setStyle(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label>整体大纲</Label>
            <Textarea
              value={outline}
              rows={10}
              className="font-mono text-[13px] leading-relaxed"
              placeholder="可使用 markdown 列表分阶段记录"
              onChange={(e) => setOutline(e.target.value)}
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

// ----- Chapter --------------------------------------------------------------

export function ChapterDialog({
  open,
  onOpenChange,
  projectId,
  chapter,
  onSaved,
  onDeleted,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  projectId: string;
  chapter: Chapter | null;
  onSaved: (c: Chapter) => void;
  onDeleted: (id: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open || !chapter) return;
    setTitle(chapter.title);
    setSummary(chapter.summary);
    setContent(chapter.content);
  }, [open, chapter]);

  if (!chapter) return null;

  async function onSave() {
    setSaving(true);
    try {
      const updated = await projectsApi.updateChapter(projectId, chapter!.id, {
        title,
        summary,
        content,
        order_index: chapter!.order_index,
      });
      onSaved(updated);
      onOpenChange(false);
      toast.success("已保存");
    } catch (e) {
      toast.error("保存失败", { description: String(e) });
    } finally {
      setSaving(false);
    }
  }

  async function onDelete() {
    if (!window.confirm(`确认删除「${chapter!.title || "未命名章节"}」?`)) return;
    try {
      await projectsApi.removeChapter(projectId, chapter!.id);
      onDeleted(chapter!.id);
      onOpenChange(false);
      toast.success("已删除");
    } catch (e) {
      toast.error("删除失败", { description: String(e) });
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>编辑章节</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 max-h-[70vh] overflow-y-auto pr-1 scrollbar-thin">
          <div className="grid gap-1.5">
            <Label>标题</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label>本章梗概</Label>
            <Textarea
              value={summary}
              rows={4}
              placeholder="这一章要发生什么、推进哪条线、点到哪个伏笔……"
              onChange={(e) => setSummary(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <div className="flex items-center justify-between">
              <Label>正文</Label>
              <span className="text-xs text-muted-foreground tabular-nums">
                {content.length.toLocaleString()} 字
              </span>
            </div>
            <Textarea
              value={content}
              className="min-h-[320px] text-[14px] leading-[1.85]"
              placeholder="开始正文写作……"
              onChange={(e) => setContent(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter className="justify-between sm:justify-between">
          <Button variant="ghost" onClick={onDelete} className="text-destructive hover:text-destructive">
            <Trash2 className="mr-1.5 h-4 w-4" />
            删除
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button onClick={onSave} disabled={saving}>
              {saving ? "保存中…" : "保存"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ----- Character ------------------------------------------------------------

export function CharacterDialog({
  open,
  onOpenChange,
  projectId,
  initial,
  onSaved,
  onDeleted,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  projectId: string;
  initial: Character | null;
  onSaved: (c: Character) => void;
  onDeleted?: (id: string) => void;
}) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [profile, setProfile] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(initial?.name ?? "");
    setRole(initial?.role ?? "");
    setProfile(initial?.profile ?? "");
  }, [open, initial]);

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

  async function onDelete() {
    if (!initial?.id) return;
    if (!window.confirm(`删除人物「${initial.name}」?`)) return;
    try {
      await charactersApi.remove(projectId, initial.id);
      onDeleted?.(initial.id);
      onOpenChange(false);
      toast.success("已删除");
    } catch (e) {
      toast.error("删除失败", { description: String(e) });
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
              placeholder="外貌 / 身世 / 性格 / 动机 / 关系网 …"
              onChange={(e) => setProfile(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter className="justify-between sm:justify-between">
          {initial?.id ? (
            <Button variant="ghost" onClick={onDelete} className="text-destructive hover:text-destructive">
              <Trash2 className="mr-1.5 h-4 w-4" />
              删除
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button onClick={onSave} disabled={saving || !name.trim()}>
              {saving ? "保存中…" : "保存"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ----- World ----------------------------------------------------------------

export function WorldDialog({
  open,
  onOpenChange,
  projectId,
  initial,
  onSaved,
  onDeleted,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  projectId: string;
  initial: WorldEntry | null;
  onSaved: (w: WorldEntry) => void;
  onDeleted?: (id: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setTitle(initial?.title ?? "");
    setCategory(initial?.category ?? "");
    setContent(initial?.content ?? "");
  }, [open, initial]);

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

  async function onDelete() {
    if (!initial?.id) return;
    if (!window.confirm(`删除条目「${initial.title}」?`)) return;
    try {
      await worldApi.remove(projectId, initial.id);
      onDeleted?.(initial.id);
      onOpenChange(false);
      toast.success("已删除");
    } catch (e) {
      toast.error("删除失败", { description: String(e) });
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
        <DialogFooter className="justify-between sm:justify-between">
          {initial?.id ? (
            <Button variant="ghost" onClick={onDelete} className="text-destructive hover:text-destructive">
              <Trash2 className="mr-1.5 h-4 w-4" />
              删除
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button onClick={onSave} disabled={saving || !title.trim()}>
              {saving ? "保存中…" : "保存"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
