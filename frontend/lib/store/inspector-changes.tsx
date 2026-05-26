"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type InspectorSectionKey = "overview" | "chapters" | "characters" | "world";

interface ChangeEventDetail {
  project_id?: string;
  affects?: Record<string, boolean>;
  tool_name?: string;
}

const TOOL_TO_SECTION: Record<string, InspectorSectionKey> = {
  set_synopsis: "overview",
  set_outline: "overview",
  set_style: "overview",
  set_genre: "overview",
  add_chapter: "chapters",
  update_chapter: "chapters",
  delete_chapter: "chapters",
  upsert_character: "characters",
  delete_character: "characters",
  upsert_world: "world",
  delete_world: "world",
};

const AFFECTS_FALLBACK: Record<string, InspectorSectionKey | "all-tree"> = {
  meta: "overview",
  doc: "chapters",
  tree: "all-tree",
};

interface InspectorChangesValue {
  unread: Set<InspectorSectionKey>;
  mark: (key: InspectorSectionKey) => void;
  clear: (key: InspectorSectionKey) => void;
}

const InspectorChangesContext = createContext<InspectorChangesValue | null>(null);

export function InspectorChangesProvider({
  projectId,
  children,
}: {
  projectId: string;
  children: React.ReactNode;
}) {
  const [unread, setUnread] = useState<Set<InspectorSectionKey>>(() => new Set());

  const mark = useCallback((key: InspectorSectionKey) => {
    setUnread((prev) => {
      if (prev.has(key)) return prev;
      const next = new Set(prev);
      next.add(key);
      return next;
    });
  }, []);

  const clear = useCallback((key: InspectorSectionKey) => {
    setUnread((prev) => {
      if (!prev.has(key)) return prev;
      const next = new Set(prev);
      next.delete(key);
      return next;
    });
  }, []);

  useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<ChangeEventDetail>).detail;
      if (!detail || detail.project_id !== projectId) return;

      const tool = detail.tool_name;
      if (tool && TOOL_TO_SECTION[tool]) {
        mark(TOOL_TO_SECTION[tool]);
        return;
      }

      const affects = detail.affects ?? {};
      for (const [k, v] of Object.entries(affects)) {
        if (!v) continue;
        const target = AFFECTS_FALLBACK[k];
        if (target === "all-tree") {
          // tree 命中无 tool_name 时,稳妥起见三个都打 dot
          mark("chapters");
          mark("characters");
          mark("world");
        } else if (target) {
          mark(target);
        }
      }
    }
    window.addEventListener("data_changed", handler);
    return () => window.removeEventListener("data_changed", handler);
  }, [projectId, mark]);

  // 项目切换时清空
  useEffect(() => {
    setUnread(new Set());
  }, [projectId]);

  const value = useMemo(() => ({ unread, mark, clear }), [unread, mark, clear]);

  return (
    <InspectorChangesContext.Provider value={value}>
      {children}
    </InspectorChangesContext.Provider>
  );
}

export function useInspectorChanges() {
  const ctx = useContext(InspectorChangesContext);
  if (!ctx) {
    throw new Error("useInspectorChanges must be used within InspectorChangesProvider");
  }
  return ctx;
}
