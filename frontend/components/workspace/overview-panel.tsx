"use client";

import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { projectsApi, type Project } from "@/lib/api/endpoints/projects";

interface Props {
  project: Project;
  onUpdated: (p: Project) => void;
}

export function OverviewPanel({ project, onUpdated }: Props) {
  const [name, setName] = useState(project.name);
  const [genre, setGenre] = useState(project.genre);
  const [synopsis, setSynopsis] = useState(project.synopsis);
  const [style, setStyle] = useState(project.style);
  const [outline, setOutline] = useState(project.outline);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setName(project.name);
    setGenre(project.genre);
    setSynopsis(project.synopsis);
    setStyle(project.style);
    setOutline(project.outline);
    setDirty(false);
  }, [project.id]);

  function bind<T extends string>(
    setter: (v: T) => void,
  ): (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void {
    return (e) => {
      setter(e.target.value as T);
      setDirty(true);
    };
  }

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
      onUpdated(updated);
      setDirty(false);
      toast.success("已保存");
    } catch (e) {
      toast.error("保存失败", { description: String(e) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6 md:p-8">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">项目概览</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            这些信息将作为 AI 助手生成内容时的核心上下文
          </p>
        </div>
        <Button onClick={onSave} disabled={!dirty || saving}>
          <Save className="mr-1.5 h-4 w-4" />
          {saving ? "保存中…" : dirty ? "保存修改" : "已保存"}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">基本信息</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5">
          <div className="grid gap-1.5">
            <Label>项目名 *</Label>
            <Input value={name} onChange={bind(setName)} />
          </div>
          <div className="grid gap-1.5">
            <Label>类型</Label>
            <Input
              value={genre}
              placeholder="玄幻 / 都市 / 科幻 / 历史 …"
              onChange={bind(setGenre)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label>简介</Label>
            <Textarea
              value={synopsis}
              placeholder="一段话概括你的故事核心冲突与主题"
              rows={4}
              onChange={bind(setSynopsis)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">写作风格</CardTitle>
          <p className="text-xs text-muted-foreground">
            描述你期望的语言、节奏、视角等(AI 续写时会参考)
          </p>
        </CardHeader>
        <CardContent>
          <Textarea
            value={style}
            placeholder="例如:第三人称限知视角,语言克制,节奏偏慢,注重心理描写"
            rows={4}
            onChange={bind(setStyle)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">整体大纲</CardTitle>
          <p className="text-xs text-muted-foreground">
            主线剧情 / 阶段目标 / 关键冲突 / 已埋伏笔
          </p>
        </CardHeader>
        <CardContent>
          <Textarea
            value={outline}
            placeholder="可使用 markdown 列表分阶段记录"
            rows={10}
            className="font-mono text-[13px] leading-relaxed"
            onChange={bind(setOutline)}
          />
        </CardContent>
      </Card>
    </div>
  );
}
