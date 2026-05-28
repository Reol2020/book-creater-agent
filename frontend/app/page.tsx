"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  Sparkles,
  BookOpen,
  ArrowRight,
  CalendarClock,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { AppHeader } from "@/components/app-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { projectsApi, type Project } from "@/lib/api/endpoints/projects";
import { useProjectsCache } from "@/lib/store/projects-cache";

export default function HomePage() {
  const router = useRouter();
  const cachedList = useProjectsCache((s) => s.list);
  const loadList = useProjectsCache((s) => s.loadList);
  const removeFromCache = useProjectsCache((s) => s.removeOne);
  const [open, setOpen] = useState(false);

  // 进入主页:有缓存就立即拿到旧列表,同时后台刷新;无缓存阻塞拉一次。
  useEffect(() => {
    loadList().catch((e) =>
      toast.error("加载项目列表失败", { description: String(e) }),
    );
  }, [loadList]);

  const projects = cachedList;

  async function onDelete(id: string, name: string) {
    if (!window.confirm(`确认删除项目「${name}」?此操作不可撤销。`)) return;
    try {
      await projectsApi.remove(id);
      toast.success(`已删除 ${name}`);
      removeFromCache(id);
    } catch (e) {
      toast.error("删除失败", { description: String(e) });
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader />

      <main className="flex-1">
        {/* Hero */}
        <section className="border-b border-border/60 bg-gradient-to-br from-background via-background to-accent/40">
          <div className="mx-auto max-w-6xl px-6 py-14">
            <div className="flex items-center gap-2 text-xs font-medium text-primary mb-3">
              <Sparkles className="h-3.5 w-3.5" />
              AI 驱动的中文长篇小说创作工坊
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
              <span className="gradient-text">从灵感到成稿</span>,
              <span className="text-foreground">让创作专注于故事本身</span>
            </h1>
            <p className="mt-3 max-w-2xl text-sm sm:text-base text-muted-foreground leading-relaxed">
              管理多个长篇项目,设计人物与世界观,在 AI
              助手帮助下写出每一章节。
              所有数据保存在本机,可离线使用,可随时备份。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button size="lg" onClick={() => setOpen(true)}>
                <Plus className="mr-1.5 h-4 w-4" />
                创建新项目
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/settings">配置 LLM</Link>
              </Button>
            </div>
          </div>
        </section>

        {/* 项目列表 */}
        <section className="mx-auto max-w-6xl px-6 py-10">
          <div className="mb-5 flex items-end justify-between">
            <div>
              <h2 className="text-xl font-semibold">我的项目</h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {projects === null
                  ? "加载中…"
                  : projects.length === 0
                    ? "还没有项目,开始你的第一部作品吧"
                    : `共 ${projects.length} 个项目`}
              </p>
            </div>
          </div>

          {projects && projects.length === 0 && (
            <EmptyState
              icon={<BookOpen className="h-5 w-5" />}
              title="开始你的第一个故事"
              description="给作品起个名字,可以稍后再补充类型、简介与世界观。"
              action={
                <Button onClick={() => setOpen(true)}>
                  <Plus className="mr-1.5 h-4 w-4" />
                  创建项目
                </Button>
              }
            />
          )}

          {projects && projects.length > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((p) => (
                <Card
                  key={p.id}
                  className="card-hover group relative overflow-hidden"
                >
                  <Link
                    href={`/workspace?id=${p.id}`}
                    className="absolute inset-0 z-10"
                    aria-label={`打开 ${p.name}`}
                  />
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="line-clamp-1 text-base">
                        {p.name}
                      </CardTitle>
                      <button
                        type="button"
                        className="relative z-20 rounded-md p-1 text-muted-foreground opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                        onClick={(e) => {
                          e.preventDefault();
                          onDelete(p.id, p.name);
                        }}
                        aria-label="删除"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                    {p.genre && (
                      <span className="mt-1 inline-block w-fit rounded-full bg-accent px-2 py-0.5 text-[11px] text-accent-foreground">
                        {p.genre}
                      </span>
                    )}
                  </CardHeader>
                  <CardContent className="pt-0">
                    <p className="line-clamp-3 min-h-[3.75rem] text-sm text-muted-foreground">
                      {p.synopsis || "暂无简介,点击进入项目补充信息"}
                    </p>
                    <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <CalendarClock className="h-3 w-3" />
                        {new Date(p.updated_at).toLocaleDateString()}
                      </span>
                      <span className="inline-flex items-center gap-1 text-primary opacity-0 transition-opacity group-hover:opacity-100">
                        进入工作区
                        <ArrowRight className="h-3 w-3" />
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </section>
      </main>

      <CreateProjectDialog
        open={open}
        onOpenChange={setOpen}
      />
    </div>
  );
}

function CreateProjectDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const router = useRouter();
  const setOne = useProjectsCache((s) => s.setOne);
  const [name, setName] = useState("");
  const [genre, setGenre] = useState("");
  const [synopsis, setSynopsis] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setName("");
    setGenre("");
    setSynopsis("");
  }

  async function onSubmit() {
    if (!name.trim()) {
      toast.error("项目名不能为空");
      return;
    }
    setSubmitting(true);
    try {
      const p = await projectsApi.create({
        name: name.trim(),
        genre: genre.trim(),
        synopsis: synopsis.trim(),
      });
      toast.success(`项目「${p.name}」已创建`);
      setOne(p);
      reset();
      onOpenChange(false);
      // 客户端跳转,而不是 window.location.href 整页 reload
      router.push(`/workspace?id=${p.id}`);
    } catch (e) {
      toast.error("创建失败", { description: String(e) });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>创建新项目</DialogTitle>
          <DialogDescription>
            填写基本信息,后续可在工作区随时修改
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-1.5">
            <Label htmlFor="proj-name">项目名 *</Label>
            <Input
              id="proj-name"
              placeholder="例如:仙路尽头"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="proj-genre">类型</Label>
            <Input
              id="proj-genre"
              placeholder="玄幻 / 都市 / 历史 ……"
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="proj-synopsis">简介</Label>
            <Textarea
              id="proj-synopsis"
              placeholder="一句话或一段话描述你的故事(可选)"
              value={synopsis}
              onChange={(e) => setSynopsis(e.target.value)}
              rows={4}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            取消
          </Button>
          <Button onClick={onSubmit} disabled={submitting || !name.trim()}>
            {submitting ? "创建中…" : "创建并进入"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
