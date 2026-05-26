"use client";

import { useEffect, useMemo, useState } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { projectsApi, type Chapter } from "@/lib/api/endpoints/projects";
import { useDataChanged } from "@/lib/hooks/use-data-changed";
import { cn } from "@/lib/utils";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  projectId: string;
  projectName: string;
}

export function ReaderModal({ open, onOpenChange, projectId, projectName }: Props) {
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    try {
      const list = await projectsApi.listChapters(projectId);
      setChapters(list);
      setActiveId((prev) => prev ?? list[0]?.id ?? null);
    } catch (e) {
      toast.error("加载章节失败", { description: String(e) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open) reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, projectId]);

  useDataChanged(projectId, ["tree", "doc"], () => {
    if (open) reload();
  });

  const activeIndex = useMemo(
    () => chapters.findIndex((c) => c.id === activeId),
    [chapters, activeId],
  );
  const active = activeIndex >= 0 ? chapters[activeIndex] : null;

  function go(delta: number) {
    const next = activeIndex + delta;
    if (next < 0 || next >= chapters.length) return;
    setActiveId(chapters[next].id);
  }

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0"
        />
        <DialogPrimitive.Content
          className="fixed inset-0 z-50 flex bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0"
        >
          <DialogPrimitive.Title className="sr-only">
            {projectName} · 阅读模式
          </DialogPrimitive.Title>

          {/* 左侧目录 */}
          <aside className="flex w-60 shrink-0 flex-col border-r border-border/60 bg-muted/20">
            <div className="border-b border-border/60 px-4 py-3">
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                目录
              </div>
              <div className="mt-1 truncate text-sm font-medium" title={projectName}>
                {projectName}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-thin py-1">
              {loading && (
                <div className="px-4 py-3 text-xs text-muted-foreground">加载中…</div>
              )}
              {!loading && chapters.length === 0 && (
                <div className="px-4 py-3 text-xs text-muted-foreground">
                  还没有章节
                </div>
              )}
              {chapters.map((c, i) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setActiveId(c.id)}
                  className={cn(
                    "block w-full px-4 py-2 text-left text-sm transition-colors",
                    c.id === activeId
                      ? "bg-primary/10 text-primary"
                      : "text-foreground/80 hover:bg-accent/40",
                  )}
                >
                  <div className="truncate">
                    <span className="text-muted-foreground tabular-nums">{i + 1}.</span>{" "}
                    {c.title || "未命名章节"}
                  </div>
                  <div className="mt-0.5 text-[11px] text-muted-foreground/70 tabular-nums">
                    {c.word_count.toLocaleString()} 字
                  </div>
                </button>
              ))}
            </div>
          </aside>

          {/* 中间正文 */}
          <main className="relative flex-1 overflow-y-auto scrollbar-thin">
            <DialogPrimitive.Close
              className="fixed right-4 top-4 z-10 inline-flex h-8 w-8 items-center justify-center rounded-md bg-background/80 text-muted-foreground shadow-sm backdrop-blur transition-colors hover:bg-accent hover:text-foreground"
              aria-label="关闭"
            >
              <X className="h-4 w-4" />
            </DialogPrimitive.Close>

            {active ? (
              <article className="mx-auto max-w-2xl px-8 py-16">
                <h1 className="text-2xl font-semibold tracking-tight">
                  {active.title || "未命名章节"}
                </h1>
                {active.summary && (
                  <p className="mt-3 border-l-2 border-border pl-3 text-sm text-muted-foreground leading-relaxed">
                    {active.summary}
                  </p>
                )}
                <div
                  className="mt-8 whitespace-pre-wrap text-[17px] leading-[1.9] text-foreground"
                  style={{ fontFamily: '"Microsoft YaHei", "PingFang SC", system-ui, sans-serif' }}
                >
                  {active.content || (
                    <span className="text-muted-foreground italic">本章尚无内容</span>
                  )}
                </div>

                <div className="mt-12 flex items-center justify-between border-t border-border/60 pt-6">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => go(-1)}
                    disabled={activeIndex <= 0}
                  >
                    <ChevronLeft className="mr-1 h-4 w-4" />
                    上一章
                  </Button>
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {activeIndex + 1} / {chapters.length}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => go(1)}
                    disabled={activeIndex >= chapters.length - 1}
                  >
                    下一章
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </article>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                选择左侧章节开始阅读
              </div>
            )}
          </main>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
