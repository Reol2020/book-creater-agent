"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, ScrollText, Trash2, Save, FileText } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  projectsApi,
  type Chapter,
} from "@/lib/api/endpoints/projects";
import { useDataChanged } from "@/lib/hooks/use-data-changed";
import { cn } from "@/lib/utils";

interface Props {
  projectId: string;
}

export function ChaptersPanel({ projectId }: Props) {
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);

  async function reload(selectId?: string) {
    setLoading(true);
    try {
      const list = await projectsApi.listChapters(projectId);
      setChapters(list);
      if (selectId) setActiveId(selectId);
      else if (!activeId && list.length > 0) setActiveId(list[0].id);
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

  useDataChanged(projectId, ["tree", "doc"], () => reload());

  const active = useMemo(
    () => chapters.find((c) => c.id === activeId) ?? null,
    [chapters, activeId],
  );

  async function onCreate() {
    try {
      const idx = chapters.length + 1;
      const c = await projectsApi.createChapter(projectId, {
        title: `第 ${idx} 章`,
        order_index: idx,
      });
      toast.success("已新增章节");
      await reload(c.id);
    } catch (e) {
      toast.error("新增失败", { description: String(e) });
    }
  }

  async function onDelete(c: Chapter) {
    if (!window.confirm(`确认删除「${c.title || "未命名章节"}」?`)) return;
    try {
      await projectsApi.removeChapter(projectId, c.id);
      toast.success("已删除");
      const remaining = chapters.filter((x) => x.id !== c.id);
      setChapters(remaining);
      setActiveId(remaining[0]?.id ?? null);
    } catch (e) {
      toast.error("删除失败", { description: String(e) });
    }
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* 章节列表 */}
      <div className="flex w-72 shrink-0 flex-col border-r border-border/60 bg-background">
        <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
          <div className="text-sm font-medium">
            章节
            <span className="ml-1.5 text-xs text-muted-foreground">
              {chapters.length}
            </span>
          </div>
          <Button size="sm" variant="ghost" onClick={onCreate}>
            <Plus className="mr-1 h-3.5 w-3.5" />
            新增
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {loading && (
            <div className="p-4 text-xs text-muted-foreground">加载中…</div>
          )}
          {!loading && chapters.length === 0 && (
            <div className="p-4 text-xs text-muted-foreground leading-relaxed">
              还没有章节,点击右上角「新增」开始写作。
            </div>
          )}
          {chapters.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setActiveId(c.id)}
              className={cn(
                "group flex w-full items-center gap-2 border-b border-border/40 px-4 py-3 text-left text-sm transition-colors",
                c.id === activeId
                  ? "bg-primary/5"
                  : "hover:bg-accent/40",
              )}
            >
              <FileText
                className={cn(
                  "h-4 w-4 shrink-0",
                  c.id === activeId ? "text-primary" : "text-muted-foreground",
                )}
              />
              <div className="flex-1 truncate">
                <div className="truncate font-medium">
                  {c.title || "未命名章节"}
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {c.word_count.toLocaleString()} 字
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 编辑器 */}
      <div className="flex-1 overflow-hidden">
        {active ? (
          <ChapterEditor
            key={active.id}
            chapter={active}
            projectId={projectId}
            onSaved={(c) => {
              setChapters((prev) =>
                prev.map((x) => (x.id === c.id ? c : x)),
              );
            }}
            onDelete={() => onDelete(active)}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-8">
            <EmptyState
              icon={<ScrollText className="h-5 w-5" />}
              title="选择左侧章节开始撰写"
              description="或者点击「新增」创建第一章"
              action={
                <Button onClick={onCreate}>
                  <Plus className="mr-1.5 h-4 w-4" />
                  新增章节
                </Button>
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}

function ChapterEditor({
  chapter,
  projectId,
  onSaved,
  onDelete,
}: {
  chapter: Chapter;
  projectId: string;
  onSaved: (c: Chapter) => void;
  onDelete: () => void;
}) {
  const [title, setTitle] = useState(chapter.title);
  const [summary, setSummary] = useState(chapter.summary);
  const [content, setContent] = useState(chapter.content);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setTitle(chapter.title);
    setSummary(chapter.summary);
    setContent(chapter.content);
    setDirty(false);
  }, [chapter.id]);

  async function onSave() {
    setSaving(true);
    try {
      const updated = await projectsApi.updateChapter(projectId, chapter.id, {
        title,
        summary,
        content,
        order_index: chapter.order_index,
      });
      onSaved(updated);
      setDirty(false);
      toast.success("已保存");
    } catch (e) {
      toast.error("保存失败", { description: String(e) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border/60 px-6 py-3">
        <Input
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            setDirty(true);
          }}
          placeholder="章节标题"
          className="border-0 px-0 text-base font-semibold shadow-none focus-visible:ring-0"
        />
        <span className="text-xs text-muted-foreground tabular-nums">
          {content.length.toLocaleString()} 字
        </span>
        <Button size="sm" variant="ghost" onClick={onDelete}>
          <Trash2 className="mr-1 h-3.5 w-3.5" />
          删除
        </Button>
        <Button size="sm" onClick={onSave} disabled={!dirty || saving}>
          <Save className="mr-1 h-3.5 w-3.5" />
          {saving ? "保存中" : dirty ? "保存" : "已保存"}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] flex-1 overflow-hidden">
        <div className="border-r border-border/60 bg-muted/20 p-5 overflow-y-auto scrollbar-thin">
          <Label className="text-xs uppercase tracking-wide text-muted-foreground">
            本章梗概
          </Label>
          <Textarea
            value={summary}
            onChange={(e) => {
              setSummary(e.target.value);
              setDirty(true);
            }}
            placeholder="这一章要发生什么、推进哪条线、点到哪个伏笔……"
            rows={12}
            className="mt-2 resize-none border-0 bg-background text-sm leading-relaxed shadow-sm"
          />
          <p className="mt-3 text-xs text-muted-foreground leading-relaxed">
            梗概会在 AI 续写本章时作为上下文。
          </p>
        </div>

        <div className="overflow-y-auto scrollbar-thin">
          <Textarea
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              setDirty(true);
            }}
            placeholder="开始正文写作……"
            className="h-full min-h-[400px] resize-none rounded-none border-0 bg-background px-8 py-6 text-[15px] leading-[1.9] shadow-none focus-visible:ring-0"
          />
        </div>
      </div>
    </div>
  );
}
