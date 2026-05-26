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

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // 老链接 ?id=xxx&tab=yyy 重定向到 ?id=xxx
  useEffect(() => {
    if (id && tabParam) {
      router.replace(`/workspace?id=${id}`);
    }
  }, [id, tabParam, router]);

  useEffect(() => {
    if (!id) {
      setNotFound(true);
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const p = await projectsApi.get(id);
        if (!cancelled) setProject(p);
      } catch (e) {
        if (!cancelled) {
          setNotFound(true);
          toast.error("项目不存在或已删除", { description: String(e) });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // 当 AssistantPanel 通过 tool 修改了项目元字段(简介/大纲/题材/风格),刷新顶层 project
  useDataChanged(id ?? "", ["meta"], async () => {
    if (!id) return;
    try {
      setProject(await projectsApi.get(id));
    } catch {
      // ignore
    }
  });

  if (loading) return <LoadingScreen />;

  if (notFound || !project) {
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

  return <WorkspaceShell project={project} onProjectUpdated={setProject} />;
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
