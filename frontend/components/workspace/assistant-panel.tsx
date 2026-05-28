"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Send, Bot, User, Loader2, AlertCircle, Sparkles,
  Wrench, CheckCircle2, XCircle, Settings2,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { chatApi, type ChatMessage, type ConfirmPolicy } from "@/lib/api/endpoints/chat";
import { useActiveProfile } from "@/lib/store/active-profile";
import type { Project } from "@/lib/api/endpoints/projects";
import { cn } from "@/lib/utils";

interface Props {
  project: Project;
}

// ---- Turn 类型(可被 user / assistant text / tool 调用混排)
type Turn =
  | { kind: "user"; text: string }
  | { kind: "assistant"; text: string; pending?: boolean }
  | {
      kind: "tool";
      id: string;
      name: string;
      args: Record<string, unknown>;
      side_effect: string;
      status: "running" | "ok" | "fail";
      result?: string;
    };

const QUICK_ACTIONS: { label: string; prompt: string }[] = [
  { label: "写大纲", prompt: "请基于现有简介帮我写一份完整大纲,逐章列出。" },
  { label: "反提取人物", prompt: "阅读现有章节与设定,补全主要人物到项目中。" },
  { label: "续写下一章", prompt: "请续写下一章,延续大纲与人物设定,目标 2000 字。" },
  { label: "润色当前章节", prompt: "对当前最新章节做一次润色,保留原意但提升语感。" },
];

const POLICIES: { value: ConfirmPolicy; label: string; desc: string }[] = [
  { value: "default", label: "默认", desc: "新增自动 / 改删确认" },
  { value: "auto", label: "全自动", desc: "无需确认,直接执行" },
  { value: "confirm-all", label: "全确认", desc: "每次都让我看一眼" },
];

export function AssistantPanel({ project }: Props) {
  const { profile, refresh } = useActiveProfile();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [policy, setPolicy] = useState<ConfirmPolicy>("default");
  const [showPolicy, setShowPolicy] = useState(false);
  // 正在生成的 tool input 进度(长章节正文流)。tool_call 事件到达后清空,
  // 实现"正在写 add_chapter · 已生成 1234 字"的活体反馈。
  const [progress, setProgress] = useState<{
    name: string;
    chars: number;
    startedAt: number;
  } | null>(null);
  // 用户按发送 → 收到第一个 token/tool_progress 之间的等待。LLM TTFT 在长上下文 +
  // Mify/Bedrock 路由下可能 10~30s,期间 pending 气泡光显示"思考中…"看不出活体,
  // 用户会怀疑卡死。这里追踪等待开始时间,Bubble 用它显示已等候秒数。
  const [waitStartedAt, setWaitStartedAt] = useState<number | null>(null);
  // 后端心跳:上游(LLM/网关)静默 ≥4s 时,后端会主动发 heartbeat 事件证明
  // "我还在等流"。Mify 网关会把 input_json_delta 缓冲 30-60s,这段时间没有
  // tool_progress 事件,但 heartbeat 仍在跳 → 用户能看到"后端活跃 · Ns 前"。
  const [lastHeartbeatAt, setLastHeartbeatAt] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns, progress]);

  // 进度卡片需要"已用 Xs"实时跳秒。chars 是后端 ~0.8s 一次推的,
  // 之间用 1s tick 让秒数持续滚动。waitStartedAt 同理。
  const [, forceTick] = useState(0);
  useEffect(() => {
    if (!progress && waitStartedAt === null && lastHeartbeatAt === null) return;
    const t = setInterval(() => forceTick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [progress?.startedAt, waitStartedAt, lastHeartbeatAt]);

  function appendAssistantText(t: string) {
    // 流式下 token 可能是 1-3 个字。只要 last 是 assistant 就 append,
    // 不要因为"第一个 token 让 pending=false"而把后续 token 拆到新气泡里。
    setTurns((prev) => {
      const copy = [...prev];
      const last = copy[copy.length - 1];
      if (last && last.kind === "assistant") {
        copy[copy.length - 1] = { ...last, text: last.text + t };
      } else {
        copy.push({ kind: "assistant", text: t });
      }
      return copy;
    });
  }

  function broadcastDataChanged(
    affects: Record<string, boolean> | undefined,
    tool_name?: string,
  ) {
    if (!affects) return;
    if (typeof window === "undefined") return;
    window.dispatchEvent(
      new CustomEvent("data_changed", {
        detail: { project_id: project.id, affects, tool_name },
      }),
    );
  }

  async function send(textArg?: string) {
    const text = (textArg ?? input).trim();
    if (!text || streaming) return;
    if (!profile) {
      toast.error("尚未启用 LLM 配置", { description: "请先到设置页启用一个连接" });
      return;
    }

    setError(null);

    // 构造 wire messages:把已有 turns 中 user/assistant 的 text 拼到对话历史
    const history: ChatMessage[] = [];
    for (const t of turns) {
      if (t.kind === "user") history.push({ role: "user", content: t.text });
      else if (t.kind === "assistant" && t.text) history.push({ role: "assistant", content: t.text });
    }
    history.push({ role: "user", content: text });

    setTurns((prev) => [
      ...prev,
      { kind: "user", text },
      { kind: "assistant", text: "", pending: true },
    ]);
    setInput("");
    setStreaming(true);
    setWaitStartedAt(Date.now());

    const ac = new AbortController();
    abortRef.current = ac;

    try {
      await chatApi.agentStream(
        {
          messages: history,
          project_id: project.id,
          confirm_policy: policy,
        },
        {
          signal: ac.signal,
          onEvent: (e) => {
            const data = e.data as Record<string, unknown>;
            if (e.event === "token") {
              setWaitStartedAt(null);  // 收到第一个字 → TTFT 等待结束
              appendAssistantText(String(data.text ?? ""));
            } else if (e.event === "tool_progress") {
              setWaitStartedAt(null);  // tool_use 也算"已开始"
              const phase = String(data.phase ?? "delta");
              if (phase === "end") {
                // 留给 tool_call 事件清(那时入参已完整)
                return;
              }
              setProgress((prev) => {
                const name = String(data.name ?? prev?.name ?? "");
                const chars = Number(data.chars ?? 0);
                const startedAt = prev?.name === name ? prev.startedAt : Date.now();
                return { name, chars, startedAt };
              });
            } else if (e.event === "tool_call") {
              setProgress(null);
              setTurns((prev) => [
                ...prev,
                {
                  kind: "tool",
                  id: String(data.id),
                  name: String(data.name),
                  args: (data.arguments as Record<string, unknown>) ?? {},
                  side_effect: String(data.side_effect ?? ""),
                  status: "running",
                },
              ]);
            } else if (e.event === "tool_result") {
              const id = String(data.id);
              let resolvedToolName: string | undefined;
              setTurns((prev) => {
                const next = prev.map((t) => {
                  if (t.kind === "tool" && t.id === id) {
                    resolvedToolName = t.name;
                    return {
                      ...t,
                      status: (data.ok ? "ok" : "fail") as "ok" | "fail",
                      result: String(data.text ?? ""),
                    };
                  }
                  return t;
                });
                return next;
              });
              if (data.ok) {
                broadcastDataChanged(
                  data.affects as Record<string, boolean> | undefined,
                  resolvedToolName,
                );
              }
              // 让 assistant 后续 token 进入新 bubble
              setTurns((prev) => [...prev, { kind: "assistant", text: "", pending: true }]);
            } else if (e.event === "heartbeat") {
              // 后端在等上游(网关缓冲),进度卡靠这个信号显示"后端活跃 · Ns 前"
              setLastHeartbeatAt(Date.now());
            } else if (e.event === "error") {
              const d = data as { title?: string; detail?: string };
              setError(`${d.title ?? "出错了"}: ${d.detail ?? ""}`);
            } else if (e.event === "done") {
              // 把最后一个空的 assistant 占位移除
              setTurns((prev) => {
                const last = prev[prev.length - 1];
                if (last && last.kind === "assistant" && !last.text) return prev.slice(0, -1);
                return prev;
              });
            }
          },
          onError: (err) => setError(String(err)),
          onDone: () => {
            setStreaming(false);
            setProgress(null);
            setWaitStartedAt(null);
            setLastHeartbeatAt(null);
            abortRef.current = null;
          },
        },
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setStreaming(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !(e.nativeEvent as { isComposing?: boolean }).isComposing) {
      e.preventDefault();
      send();
    }
  }

  function abort() {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setProgress(null);
    setWaitStartedAt(null);
    setLastHeartbeatAt(null);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-end gap-1 border-b border-border/60 px-4 py-1.5">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowPolicy((v) => !v)}
          title="确认策略"
          className="h-7"
        >
          <Settings2 className="mr-1.5 h-3.5 w-3.5" />
          {POLICIES.find((p) => p.value === policy)?.label}
        </Button>
        {turns.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setTurns([])}
            className="h-7"
          >
            清空
          </Button>
        )}
      </div>

      {showPolicy && (
        <div className="border-b border-border/60 bg-muted/30 px-6 py-3">
          <div className="mx-auto max-w-3xl flex flex-wrap gap-2">
            {POLICIES.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => {
                  setPolicy(p.value);
                  setShowPolicy(false);
                }}
                className={cn(
                  "rounded-md border px-3 py-1.5 text-left text-xs transition-all",
                  policy === p.value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-background hover:bg-accent",
                )}
              >
                <div className="font-medium">{p.label}</div>
                <div className="text-muted-foreground">{p.desc}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {!profile && (
        <div className="m-4 flex items-start gap-3 rounded-xl border border-warning/30 bg-warning/5 p-4">
          <AlertCircle className="mt-0.5 h-4 w-4 text-warning" />
          <div className="text-sm flex-1">
            <div className="font-medium">尚未启用 LLM 连接</div>
            <p className="mt-0.5 text-muted-foreground">
              到{" "}
              <Link href="/settings" className="text-primary underline-offset-2 hover:underline">
                设置页
              </Link>{" "}
              添加 Anthropic / OpenAI API Key 并启用,即可开始对话。
            </p>
          </div>
        </div>
      )}

      <div ref={scrollerRef} className="flex-1 overflow-y-auto scrollbar-thin px-6 py-6">
        {turns.length === 0 ? (
          <Welcome onPick={(t) => send(t)} />
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {turns.map((t, i) => (
              <TurnView
                key={i}
                turn={t}
                // 只把等待时间传给最末尾的 pending assistant 气泡
                waitStartedAt={
                  i === turns.length - 1 && t.kind === "assistant" && t.pending && !t.text
                    ? waitStartedAt
                    : null
                }
                lastHeartbeatAt={
                  i === turns.length - 1 && t.kind === "assistant" && t.pending && !t.text
                    ? lastHeartbeatAt
                    : null
                }
              />
            ))}
            {progress && <ProgressCard progress={progress} lastHeartbeatAt={lastHeartbeatAt} />}
          </div>
        )}
        {error && (
          <div className="mx-auto mt-4 max-w-3xl rounded-md border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">
            {error}
          </div>
        )}
      </div>

      <div className="border-t border-border/60 bg-background/60 backdrop-blur px-6 py-3">
        <div className="mx-auto max-w-3xl">
          {turns.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {QUICK_ACTIONS.map((a) => (
                <button
                  key={a.label}
                  type="button"
                  disabled={streaming || !profile}
                  onClick={() => send(a.prompt)}
                  className="rounded-full border border-border/60 bg-background px-3 py-1 text-xs text-muted-foreground transition hover:border-primary/40 hover:text-foreground disabled:opacity-50"
                >
                  {a.label}
                </button>
              ))}
            </div>
          )}
          <div className="relative rounded-2xl border border-input bg-background p-2 shadow-sm focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-ring/20 transition-all">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="发消息给 AI 助手…  Enter 发送,Shift+Enter 换行"
              rows={2}
              disabled={!profile || streaming}
              className="min-h-[60px] resize-none border-0 bg-transparent shadow-none focus-visible:ring-0 px-2"
            />
            <div className="flex items-center justify-between px-2 pb-1">
              <span className="text-xs text-muted-foreground">
                {profile ? `当前模型 · ${profile.model}` : "未启用 LLM"}
              </span>
              {streaming ? (
                <Button size="sm" variant="outline" onClick={abort}>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                  停止
                </Button>
              ) : (
                <Button size="sm" onClick={() => send()} disabled={!input.trim() || !profile}>
                  <Send className="mr-1.5 h-3.5 w-3.5" />
                  发送
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TurnView({
  turn, waitStartedAt, lastHeartbeatAt,
}: { turn: Turn; waitStartedAt?: number | null; lastHeartbeatAt?: number | null }) {
  if (turn.kind === "tool") return <ToolCard t={turn} />;
  return (
    <Bubble
      role={turn.kind}
      text={turn.text}
      pending={"pending" in turn ? turn.pending : false}
      waitStartedAt={waitStartedAt ?? null}
      lastHeartbeatAt={lastHeartbeatAt ?? null}
    />
  );
}

function Bubble({
  role, text, pending, waitStartedAt, lastHeartbeatAt,
}: {
  role: "user" | "assistant"; text: string; pending?: boolean;
  waitStartedAt?: number | null; lastHeartbeatAt?: number | null;
}) {
  const isUser = role === "user";
  if (!text && !pending) return null;
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
        )}
      >
        {pending && !text ? (
          <PendingHint
            waitStartedAt={waitStartedAt ?? null}
            lastHeartbeatAt={lastHeartbeatAt ?? null}
          />
        ) : (
          text
        )}
      </div>
    </div>
  );
}

function ToolCard({ t }: { t: Extract<Turn, { kind: "tool" }> }) {
  const Icon =
    t.status === "running" ? Loader2 : t.status === "ok" ? CheckCircle2 : XCircle;
  const color =
    t.status === "running" ? "text-muted-foreground"
      : t.status === "ok" ? "text-emerald-600 dark:text-emerald-400"
      : "text-destructive";
  const sideLabel: Record<string, string> = {
    create: "新增", update: "修改", delete: "删除", read: "读取", compose: "编排",
  };
  return (
    <div className="rounded-xl border border-border/60 bg-card/40 p-3">
      <div className="flex items-center gap-2 text-sm">
        <Icon className={cn("h-4 w-4 shrink-0", color, t.status === "running" && "animate-spin")} />
        <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="font-mono text-xs">{t.name}</span>
        {t.side_effect && (
          <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
            {sideLabel[t.side_effect] ?? t.side_effect}
          </span>
        )}
      </div>
      {Object.keys(t.args).length > 0 && (
        <pre className="mt-2 overflow-x-auto rounded bg-muted/50 p-2 text-[11px] leading-snug text-muted-foreground">
          {JSON.stringify(t.args, null, 2)}
        </pre>
      )}
      {t.result && (
        <div className={cn("mt-2 text-xs", color)}>{t.result}</div>
      )}
    </div>
  );
}

function PendingHint({
  waitStartedAt, lastHeartbeatAt,
}: { waitStartedAt: number | null; lastHeartbeatAt: number | null }) {
  // pending 气泡:首字到达前的占位。waitStartedAt 在 send() 时写入,
  // 收到首个 token / tool_progress 时清空,这里据此显示已等候秒数。
  // > 5s 加一句首字延迟提示;> 30s 提示可点停止。父组件已经在 streaming 期间
  // 每 1s 触发 forceTick,这里读 Date.now() 即可。
  // lastHeartbeatAt:后端心跳时间戳,可证明"后端没死,在等上游"。
  const elapsed = waitStartedAt
    ? Math.max(0, Math.floor((Date.now() - waitStartedAt) / 1000))
    : 0;
  const hbAge = lastHeartbeatAt
    ? Math.max(0, Math.floor((Date.now() - lastHeartbeatAt) / 1000))
    : null;
  return (
    <div className="space-y-1">
      <span className="inline-flex items-center gap-2 text-muted-foreground italic">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        思考中…
        {waitStartedAt !== null && <span className="not-italic text-xs">{elapsed}s</span>}
        {hbAge !== null && (
          <span className="not-italic text-[10px] rounded bg-emerald-500/10 px-1.5 py-0.5 text-emerald-600 dark:text-emerald-400">
            ● 后端活跃 · {hbAge}s 前
          </span>
        )}
      </span>
      {elapsed >= 5 && elapsed < 30 && (
        <div className="text-xs text-muted-foreground/80 not-italic">
          长上下文 / 长章节请求首字延迟通常 5-30s,后端正在处理。
        </div>
      )}
      {elapsed >= 30 && (
        <div className="text-xs text-amber-600 dark:text-amber-400 not-italic">
          已等候 {elapsed}s,如果一直无响应可点右下角「停止」重试。
        </div>
      )}
    </div>
  );
}

function ProgressCard({
  progress, lastHeartbeatAt,
}: {
  progress: { name: string; chars: number; startedAt: number };
  lastHeartbeatAt: number | null;
}) {
  const elapsedSec = Math.max(0, Math.floor((Date.now() - progress.startedAt) / 1000));
  const hbAge = lastHeartbeatAt
    ? Math.max(0, Math.floor((Date.now() - lastHeartbeatAt) / 1000))
    : null;
  const friendly: Record<string, string> = {
    add_chapter: "新增章节",
    update_chapter: "更新章节",
    set_synopsis: "更新简介",
    set_outline: "更新大纲",
    set_style: "更新风格",
    set_genre: "更新题材",
    upsert_character: "更新人物",
    delete_character: "删除人物",
    upsert_world: "更新世界观",
    delete_world: "删除世界观",
  };
  const label = friendly[progress.name] ?? progress.name;
  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-3">
      <div className="flex items-center gap-2 text-sm">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="font-medium">正在写入 · {label}</span>
        <span className="ml-auto font-mono text-base tabular-nums text-primary">{elapsedSec}s</span>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>已生成约 {progress.chars} 字</span>
        {hbAge !== null && (
          <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-600 dark:text-emerald-400">
            ● 后端活跃 · {hbAge}s 前
          </span>
        )}
        <span className="ml-auto italic">字数分批接收(网关缓冲),写完会自动落到右侧项目</span>
      </div>
    </div>
  );
}

function Welcome({ onPick }: { onPick: (t: string) => void }) {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center gap-2 text-primary">
        <Sparkles className="h-4 w-4" />
        <span className="text-sm font-medium">想从哪里开始?</span>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {QUICK_ACTIONS.map((a) => (
          <button
            key={a.label}
            type="button"
            onClick={() => onPick(a.prompt)}
            className="rounded-xl border border-border/60 bg-card px-4 py-3 text-left text-sm transition-all hover:border-primary/30 hover:bg-accent/30"
          >
            <div className="font-medium">{a.label}</div>
            <div className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
              {a.prompt}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
