"use client";

import { useEffect, useRef, useState } from "react";
import {
  Plus,
  CheckCircle2,
  KeyRound,
  Trash2,
  Sparkles,
  Pencil,
  ShieldCheck,
  Eye,
  EyeOff,
  Loader2,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { AppHeader } from "@/components/app-header";
import { Badge } from "@/components/ui/badge";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  settingsApi,
  type LlmAuthType,
  type LlmProfile,
  type LlmProfileDraft,
} from "@/lib/api/endpoints/settings";
import { PROVIDER_PRESETS } from "@/lib/providers";
import { useActiveProfile } from "@/lib/store/active-profile";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const [items, setItems] = useState<LlmProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<LlmProfile | null>(null);
  const [open, setOpen] = useState(false);
  const { profile: active, refresh: refreshActive } = useActiveProfile();

  async function reload() {
    setLoading(true);
    try {
      setItems(await settingsApi.list());
      await refreshActive();
    } catch (e) {
      toast.error("加载失败", { description: String(e) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function activate(p: LlmProfile) {
    try {
      await settingsApi.activate(p.id);
      toast.success(`已启用「${p.name}」`);
      await refreshActive();
    } catch (e) {
      toast.error("启用失败", { description: String(e) });
    }
  }

  async function remove(p: LlmProfile) {
    if (!window.confirm(`删除连接「${p.name}」?`)) return;
    try {
      await settingsApi.remove(p.id);
      setItems((prev) => prev.filter((x) => x.id !== p.id));
      if (active?.id === p.id) await refreshActive();
      toast.success("已删除");
    } catch (e) {
      toast.error("删除失败", { description: String(e) });
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">LLM 连接</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              支持 Anthropic / OpenAI 兼容网关 / 本地 Ollama,启用其中一个用于生成
            </p>
          </div>
          <Button
            onClick={() => {
              setEditing(null);
              setOpen(true);
            }}
          >
            <Plus className="mr-1.5 h-4 w-4" />
            新增连接
          </Button>
        </div>

        {loading && <p className="text-sm text-muted-foreground">加载中…</p>}

        {!loading && items.length === 0 && (
          <EmptyState
            icon={<KeyRound className="h-5 w-5" />}
            title="还没有 LLM 连接"
            description="添加一个 API Key 才能使用 AI 助手与续写功能"
            action={
              <Button
                onClick={() => {
                  setEditing(null);
                  setOpen(true);
                }}
              >
                <Plus className="mr-1.5 h-4 w-4" />
                添加连接
              </Button>
            }
          />
        )}

        <div className="space-y-3">
          {items.map((p) => {
            const isActive = active?.id === p.id;
            const verifiedDate = p.verified_at ? new Date(p.verified_at) : null;
            return (
              <Card key={p.id} className="card-hover">
                <CardContent className="flex items-center gap-4 p-5">
                  <div
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium truncate">{p.name}</span>
                      {isActive && (
                        <Badge variant="success" className="gap-1">
                          <CheckCircle2 className="h-3 w-3" />
                          已启用
                        </Badge>
                      )}
                      {verifiedDate && (
                        <Badge variant="outline" className="gap-1 text-success">
                          <ShieldCheck className="h-3 w-3" />
                          已验证
                        </Badge>
                      )}
                      <Badge variant="muted">{p.provider}</Badge>
                    </div>
                    <div className="mt-0.5 truncate text-xs text-muted-foreground">
                      <span className="font-mono">{p.model}</span>
                      {p.base_url && (
                        <span className="ml-2">· {p.base_url}</span>
                      )}
                      <span className="ml-2">
                        · {p.auth_type === "bearer" ? "Bearer" : "x-api-key"}
                      </span>
                      {verifiedDate && (
                        <span className="ml-2">
                          · 验证于 {verifiedDate.toLocaleString("zh-CN")}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {!isActive && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => activate(p)}
                      >
                        启用
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setEditing(p);
                        setOpen(true);
                      }}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-muted-foreground hover:text-destructive"
                      onClick={() => remove(p)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <p className="mt-10 text-xs text-muted-foreground leading-relaxed">
          <strong className="text-foreground/80">小贴士:</strong>{" "}
          可以把 Claude-Code 的 env JSON、OpenAI 的 env 配置、curl 命令直接粘贴到「粘贴
          JSON / curl」标签页,系统会自动识别并填好表单。
          所有数据保存在本机 SQLite,不会上传到任何服务器。
        </p>
      </main>

      <ProfileDialog
        open={open}
        onOpenChange={setOpen}
        initial={editing}
        onSaved={reload}
      />
    </div>
  );
}

// ============================================================ Dialog
type DialogTab = "quick" | "json" | "curl" | "advanced";

interface FormState {
  id?: string;
  name: string;
  provider: string;
  model: string;
  api_key: string;
  base_url: string;
  auth_type: LlmAuthType;
  max_tokens: number;
  temperature: number;
  extra_headers: Array<{ k: string; v: string }>;
}

function emptyForm(): FormState {
  return {
    name: "",
    provider: "anthropic",
    model: "claude-sonnet-4-5",
    api_key: "",
    base_url: "",
    auth_type: "api_key",
    max_tokens: 16384,
    temperature: 0.7,
    extra_headers: [],
  };
}

function formFromProfile(p: LlmProfile): FormState {
  return {
    id: p.id,
    name: p.name,
    provider: p.provider,
    model: p.model,
    api_key: p.api_key,
    base_url: p.base_url,
    auth_type: p.auth_type,
    max_tokens: p.max_tokens,
    temperature: p.temperature,
    extra_headers: Object.entries(p.extra_headers || {}).map(([k, v]) => ({
      k,
      v,
    })),
  };
}

function formToDraft(f: FormState): LlmProfileDraft {
  const headers: Record<string, string> = {};
  for (const { k, v } of f.extra_headers) {
    if (k.trim()) headers[k.trim()] = v;
  }
  return {
    id: f.id,
    name: f.name.trim(),
    provider: f.provider,
    model: f.model.trim(),
    api_key: f.api_key,
    base_url: f.base_url.trim(),
    auth_type: f.auth_type,
    max_tokens: f.max_tokens,
    temperature: f.temperature,
    extra_headers: headers,
  };
}

function ProfileDialog({
  open,
  onOpenChange,
  initial,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  initial: LlmProfile | null;
  onSaved: () => void;
}) {
  const [tab, setTab] = useState<DialogTab>("quick");
  const [form, setForm] = useState<FormState>(emptyForm);
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importText, setImportText] = useState("");
  const [importing, setImporting] = useState(false);

  // 测试连接 状态
  const [testing, setTesting] = useState(false);
  const [testStage, setTestStage] = useState<
    | { kind: "idle" }
    | { kind: "waiting"; sec: number }
    | { kind: "receiving"; sec: number; chars: number }
    | { kind: "ok"; latencyMs: number; chars: number }
    | { kind: "fail"; title: string; detail: string }
  >({ kind: "idle" });
  const testAbortRef = useRef<AbortController | null>(null);
  const testStartRef = useRef<number>(0);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (open) {
      setTab(initial ? "advanced" : "quick");
      setForm(initial ? formFromProfile(initial) : emptyForm());
      setImportText("");
      setShowKey(false);
      setTestStage({ kind: "idle" });
    } else {
      // 关弹窗取消测试
      testAbortRef.current?.abort();
      testAbortRef.current = null;
      if (tickRef.current) clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, [open, initial]);

  function applyPreset(presetId: string) {
    const p = PROVIDER_PRESETS.find((x) => x.id === presetId);
    if (!p) return;
    setForm((f) => ({
      ...f,
      provider: p.provider,
      model: p.model,
      base_url: p.base_url,
      auth_type: p.auth_type,
      name: f.name || p.label,
    }));
  }

  async function doImport() {
    if (!importText.trim()) {
      toast.error("请粘贴 JSON 或 curl 文本");
      return;
    }
    setImporting(true);
    try {
      const draft = await settingsApi.importText(importText, form.name);
      setForm((f) => ({
        ...formFromProfile(draft as LlmProfile),
        id: f.id, // 保留正在编辑的 id(覆盖现有连接的字段)
      }));
      setTab("advanced");
      toast.success("已识别,可在「高级」继续校对");
    } catch (e) {
      toast.error("解析失败", { description: String(e) });
    } finally {
      setImporting(false);
    }
  }

  async function doTest() {
    if (!form.api_key && form.provider === "anthropic") {
      toast.error("缺少 API Key,无法测试");
      return;
    }
    if (!form.model.trim()) {
      toast.error("请先填写模型");
      return;
    }
    // 取消上一次
    testAbortRef.current?.abort();
    if (tickRef.current) clearInterval(tickRef.current);
    const ac = new AbortController();
    testAbortRef.current = ac;
    testStartRef.current = performance.now();
    setTesting(true);
    setTestStage({ kind: "waiting", sec: 0 });
    tickRef.current = setInterval(() => {
      const sec = (performance.now() - testStartRef.current) / 1000;
      setTestStage((s) => {
        if (s.kind === "waiting") return { kind: "waiting", sec };
        if (s.kind === "receiving")
          return { kind: "receiving", sec, chars: s.chars };
        return s;
      });
    }, 200);

    let ok = false;
    let lastError: { title: string; detail: string } | null = null;

    await settingsApi.testStream(formToDraft(form), {
      signal: ac.signal,
      onEvent: (ev) => {
        if (ev.event === "first_token") {
          setTestStage({ kind: "receiving", sec: 0, chars: 0 });
        } else if (ev.event === "chunk") {
          const total = Number(ev.data.total_chars ?? 0);
          setTestStage((s) => ({
            kind: "receiving",
            sec: s.kind === "receiving" ? s.sec : 0,
            chars: total,
          }));
        } else if (ev.event === "done") {
          ok = true;
          setTestStage({
            kind: "ok",
            latencyMs: Number(ev.data.latency_ms ?? 0),
            chars: Number(ev.data.chars ?? 0),
          });
        } else if (ev.event === "timeout") {
          lastError = {
            title: "测试超时",
            detail: `${ev.data.after_sec ?? 30} 秒内没有响应。可能原因:base_url 不通 / API Key 失效 / 网关响应过慢`,
          };
          setTestStage({ kind: "fail", ...lastError });
        } else if (ev.event === "error") {
          lastError = {
            title: String(ev.data.title ?? "失败"),
            detail: String(ev.data.detail ?? ""),
          };
          setTestStage({ kind: "fail", ...lastError });
        }
      },
      onError: (e) => {
        if (!lastError) {
          setTestStage({
            kind: "fail",
            title: "请求失败",
            detail: String(e),
          });
        }
      },
      onDone: () => {
        if (tickRef.current) clearInterval(tickRef.current);
        tickRef.current = null;
        setTesting(false);
      },
    });

    if (ok) {
      toast.success("连接测试通过");
      // 已保存的 profile 才会写 verified_at,新建的需用户先保存
    }
  }

  async function onSave() {
    if (!form.name.trim()) return toast.error("名称不能为空");
    if (!form.model.trim()) return toast.error("模型不能为空");
    setSaving(true);
    try {
      await settingsApi.upsert(formToDraft(form));
      toast.success(form.id ? "已更新" : "已添加");
      onOpenChange(false);
      onSaved();
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
          <DialogTitle>
            {initial ? "编辑连接" : "新增 LLM 连接"}
          </DialogTitle>
        </DialogHeader>

        <Tabs value={tab} onValueChange={(v) => setTab(v as DialogTab)}>
          <TabsList>
            <TabsTrigger value="quick">快速</TabsTrigger>
            <TabsTrigger value="json">粘贴 JSON</TabsTrigger>
            <TabsTrigger value="curl">粘贴 curl</TabsTrigger>
            <TabsTrigger value="advanced">高级</TabsTrigger>
          </TabsList>

          {/* ============================================================ Quick */}
          <TabsContent value="quick">
            <div className="grid gap-4 pt-1">
              <div className="grid gap-1.5">
                <Label>预设</Label>
                <select
                  className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
                  defaultValue=""
                  onChange={(e) => applyPreset(e.target.value)}
                >
                  <option value="" disabled>
                    选择一个预设…
                  </option>
                  {PROVIDER_PRESETS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                      {p.hint ? ` — ${p.hint}` : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid gap-1.5">
                <Label>显示名 *</Label>
                <Input
                  placeholder="例如:工作号 Claude"
                  value={form.name}
                  onChange={(e) =>
                    setForm({ ...form, name: e.target.value })
                  }
                />
              </div>
              <div className="grid gap-1.5">
                <Label>模型 *</Label>
                <Input
                  value={form.model}
                  onChange={(e) =>
                    setForm({ ...form, model: e.target.value })
                  }
                />
              </div>
              <ApiKeyField
                value={form.api_key}
                onChange={(v) => setForm({ ...form, api_key: v })}
                show={showKey}
                onToggle={() => setShowKey((x) => !x)}
              />
              {form.base_url && (
                <p className="text-xs text-muted-foreground">
                  base_url 已由预设填入:
                  <code className="ml-1 rounded bg-muted px-1">
                    {form.base_url}
                  </code>{" "}
                  (可在「高级」修改)
                </p>
              )}
            </div>
          </TabsContent>

          {/* ============================================================ JSON */}
          <TabsContent value="json">
            <div className="grid gap-3 pt-1">
              <Label>粘贴 env JSON 或原生 LlmProfile JSON</Label>
              <Textarea
                rows={10}
                value={importText}
                onChange={(e) => setImportText(e.target.value)}
                placeholder={`{\n  "env": {\n    "ANTHROPIC_AUTH_TOKEN": "sk-...",\n    "ANTHROPIC_BASE_URL": "https://your-gateway.com",\n    "ANTHROPIC_MODEL": "claude-sonnet-4-5"\n  }\n}`}
                className="font-mono text-xs"
              />
              <div className="flex items-center gap-2">
                <Button onClick={doImport} disabled={importing}>
                  {importing ? "解析中…" : "识别并填表"}
                </Button>
                <p className="text-xs text-muted-foreground">
                  支持 Claude-Code env、扁平 env、OpenAI env、原生 JSON 四种
                </p>
              </div>
            </div>
          </TabsContent>

          {/* ============================================================ curl */}
          <TabsContent value="curl">
            <div className="grid gap-3 pt-1">
              <Label>粘贴 curl 命令</Label>
              <Textarea
                rows={10}
                value={importText}
                onChange={(e) => setImportText(e.target.value)}
                placeholder={`curl https://api.anthropic.com/v1/messages \\\n  -H "x-api-key: sk-ant-..." \\\n  -H "anthropic-version: 2023-06-01" \\\n  -H "content-type: application/json" \\\n  -d '{"model":"claude-sonnet-4-5","max_tokens":100,"messages":[...]}'`}
                className="font-mono text-xs"
              />
              <div className="flex items-center gap-2">
                <Button onClick={doImport} disabled={importing}>
                  {importing ? "解析中…" : "识别并填表"}
                </Button>
                <p className="text-xs text-muted-foreground">
                  自动从 URL/headers/body 抽取 base_url、key、model
                </p>
              </div>
            </div>
          </TabsContent>

          {/* ============================================================ Advanced */}
          <TabsContent value="advanced">
            <div className="grid gap-3 pt-1">
              <div className="grid gap-1.5">
                <Label>显示名 *</Label>
                <Input
                  value={form.name}
                  onChange={(e) =>
                    setForm({ ...form, name: e.target.value })
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-1.5">
                  <Label>Provider *</Label>
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
                    value={form.provider}
                    onChange={(e) =>
                      setForm({ ...form, provider: e.target.value })
                    }
                  >
                    <option value="anthropic">Anthropic</option>
                    <option value="openai">OpenAI / 兼容</option>
                  </select>
                </div>
                <div className="grid gap-1.5">
                  <Label>认证</Label>
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-sm"
                    value={form.auth_type}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        auth_type: e.target.value as LlmAuthType,
                      })
                    }
                  >
                    <option value="api_key">x-api-key (官方直连)</option>
                    <option value="bearer">Bearer (网关 / Bedrock)</option>
                  </select>
                </div>
              </div>

              <div className="grid gap-1.5">
                <Label>模型 *</Label>
                <Input
                  value={form.model}
                  onChange={(e) =>
                    setForm({ ...form, model: e.target.value })
                  }
                />
              </div>

              <ApiKeyField
                value={form.api_key}
                onChange={(v) => setForm({ ...form, api_key: v })}
                show={showKey}
                onToggle={() => setShowKey((x) => !x)}
              />

              <div className="grid gap-1.5">
                <Label>Base URL</Label>
                <Input
                  placeholder="留空使用官方"
                  value={form.base_url}
                  onChange={(e) =>
                    setForm({ ...form, base_url: e.target.value })
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-1.5">
                  <Label>Max Tokens</Label>
                  <Input
                    type="number"
                    value={form.max_tokens}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        max_tokens: parseInt(e.target.value) || 0,
                      })
                    }
                  />
                </div>
                <div className="grid gap-1.5">
                  <Label>Temperature</Label>
                  <Input
                    type="number"
                    step="0.1"
                    min={0}
                    max={2}
                    value={form.temperature}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        temperature: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </div>
              </div>

              <ExtraHeadersEditor
                items={form.extra_headers}
                onChange={(extra_headers) =>
                  setForm({ ...form, extra_headers })
                }
              />
            </div>
          </TabsContent>
        </Tabs>

        {/* ============================================================ Test status */}
        <TestStatusBar stage={testStage} />

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={doTest}
            disabled={testing}
            className="mr-auto"
          >
            {testing ? (
              <>
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                测试中…
              </>
            ) : (
              "测试连接"
            )}
          </Button>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={onSave} disabled={saving}>
            {saving ? "保存中…" : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ApiKeyField({
  value,
  onChange,
  show,
  onToggle,
}: {
  value: string;
  onChange: (v: string) => void;
  show: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="grid gap-1.5">
      <Label>API Key *</Label>
      <div className="relative">
        <Input
          type={show ? "text" : "password"}
          placeholder="sk-…"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="pr-10"
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute inset-y-0 right-0 inline-flex items-center px-3 text-muted-foreground hover:text-foreground"
        >
          {show ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}

function ExtraHeadersEditor({
  items,
  onChange,
}: {
  items: Array<{ k: string; v: string }>;
  onChange: (items: Array<{ k: string; v: string }>) => void;
}) {
  return (
    <div className="grid gap-1.5">
      <div className="flex items-center justify-between">
        <Label>额外请求头(可选)</Label>
        <button
          type="button"
          onClick={() => onChange([...items, { k: "", v: "" }])}
          className="text-xs text-primary hover:underline"
        >
          + 添加一行
        </button>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          某些网关需要额外的 header(如 anthropic-version、X-Custom-Routing)
        </p>
      ) : (
        <div className="grid gap-2">
          {items.map((it, i) => (
            <div key={i} className="flex items-center gap-2">
              <Input
                placeholder="header name"
                value={it.k}
                onChange={(e) => {
                  const next = [...items];
                  next[i] = { ...next[i], k: e.target.value };
                  onChange(next);
                }}
                className="font-mono text-xs"
              />
              <Input
                placeholder="value"
                value={it.v}
                onChange={(e) => {
                  const next = [...items];
                  next[i] = { ...next[i], v: e.target.value };
                  onChange(next);
                }}
                className="font-mono text-xs"
              />
              <button
                type="button"
                onClick={() => onChange(items.filter((_, j) => j !== i))}
                className="text-muted-foreground hover:text-destructive"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TestStatusBar({
  stage,
}: {
  stage:
    | { kind: "idle" }
    | { kind: "waiting"; sec: number }
    | { kind: "receiving"; sec: number; chars: number }
    | { kind: "ok"; latencyMs: number; chars: number }
    | { kind: "fail"; title: string; detail: string };
}) {
  if (stage.kind === "idle") return null;
  if (stage.kind === "waiting")
    return (
      <div className="rounded-md border border-border/60 bg-muted/30 px-3 py-2 text-sm">
        <Loader2 className="mr-1.5 inline h-3.5 w-3.5 animate-spin text-muted-foreground" />
        等待首个 token… {stage.sec.toFixed(1)}s
      </div>
    );
  if (stage.kind === "receiving")
    return (
      <div className="rounded-md border border-primary/30 bg-primary/5 px-3 py-2 text-sm">
        <Loader2 className="mr-1.5 inline h-3.5 w-3.5 animate-spin text-primary" />
        接收中 · 已收 {stage.chars} 字 ({stage.sec.toFixed(1)}s)
      </div>
    );
  if (stage.kind === "ok")
    return (
      <div className="rounded-md border border-success/30 bg-success/5 px-3 py-2 text-sm text-success">
        <CheckCircle2 className="mr-1.5 inline h-3.5 w-3.5" />
        连接成功 · {stage.chars} 字 / {(stage.latencyMs / 1000).toFixed(1)}s
      </div>
    );
  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
      <div className="font-medium">✗ {stage.title}</div>
      <div className="mt-0.5 text-xs whitespace-pre-wrap break-words leading-relaxed opacity-90 max-h-32 overflow-y-auto">
        {stage.detail}
      </div>
    </div>
  );
}
