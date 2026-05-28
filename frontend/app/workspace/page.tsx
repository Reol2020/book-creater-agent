"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { AppHeader } from "@/components/app-header";
import { WorkspaceShell } from "@/components/workspace/shell";
import { Button } from "@/components/ui/button";
import { projectsApi, type Project } from "@/lib/api/endpoints/projects";
import { useDataChanged } from "@/lib/hooks/use-data-changed";
import { useProjectsCache } from "@/lib/store/projects-cache";

export default function WorkspacePage() {
  return (
    <Suspense fallback={<LoadingScreen />}>
      <WorkspaceInner />
    </Suspense>
  );
}

function WorkspaceInner() {
  const sp = useSearchParams();
  const router = useRouter();
  const id = sp.get("id");
  const tabParam = sp.get("tab");

  // 直接从缓存拿:从主页点过来时,project 摘要已经在 byId 里 → 立即渲染 shell
  const cached = useProjectsCache((s) => (id ? s.byId[id] : undefined));
  const loadOne = useProjectsCache((s) => s.loadOne);
  const setOne = useProjectsCache((s) => s.setOne);
  const [project, setProject] = useState<Project | null>(cached ?? null);
  const [notFound, setNotFound] = useState(false);

  // 老链接 ?id=xxx&tab=yyy 重定向到 ?id=xxx
  useEffect(() => {
    if (id && tabParam) {
      router.replace(`/workspace?id=${id}`);
    }
  }, [id, tabParam, router]);

  // 后台拉最新(若有缓存,UI 已经先渲染了)
  useEffect(() => {
    if (!id) {
      setNotFound(true);
      return;
    }
    let cancelled = false;
    loadOne(id)
      .then((p) => {
        if (!cancelled) setProject(p);
      })
      .catch((e) => {
        if (!cancelled) {
          setNotFound(true);
          toast.error("项目不存在或已删除", { description: String(e) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id, loadOne]);

  // 当 AssistantPanel 通过 tool 修改了项目元字段,刷新顶层 project + 缓存
  useDataChanged(id ?? "", ["meta"], async () => {
    if (!id) return;
    try {
      const p = await projectsApi.get(id);
      setProject(p);
      setOne(p);
    } catch {
      // ignore
    }
  });

  if (!id || notFound) {
    return (
      <div className="min-h-screen flex flex-col">
        <AppHeader />
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center">
            <h2 className="text-lg font-medium">未找到项目</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              它可能已被删除或链接有误
            </p>
            <Button asChild className="mt-4">
              <Link href="/">
                <ArrowLeft className="mr-1.5 h-4 w-4" />
                返回主页
              </Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!project) return <LoadingScreen />;

  return (
    <WorkspaceShell
      project={project}
      onProjectUpdated={(p) => {
        setProject(p);
        setOne(p);
      }}
    />
  );
}

function LoadingScreen() {
  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader />
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        加载中…
      </div>
    </div>
  );
}
