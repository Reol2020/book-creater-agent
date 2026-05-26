"use client";

import { useEffect, useRef } from "react";

/**
 * 监听 AssistantPanel 在工具调用成功后派发的 `data_changed` 事件,
 * 命中当前 panel 关心的影响面就触发一次 reload。
 *
 * affects 标签:
 *  - tree : 项目树类(章节/人物/世界观条目的增删)
 *  - doc  : 章节正文
 *  - meta : project 元字段(name/genre/style/synopsis/outline)
 *
 * ⚠ 防雪崩:agent 一轮可能连续调多次工具,事件密集到来。
 * 内部用 RAF + 短 timeout 合并到一次 reload(参考桌面版 18.1 刷新雪崩教训)。
 */
export type AffectsKey = "tree" | "doc" | "meta";

const COALESCE_MS = 120;

export function useDataChanged(
  projectId: string,
  affects: AffectsKey[],
  reload: () => void,
) {
  const reloadRef = useRef(reload);
  reloadRef.current = reload;

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;

    function schedule() {
      if (timer) return;
      timer = setTimeout(() => {
        timer = null;
        reloadRef.current();
      }, COALESCE_MS);
    }

    function handler(e: Event) {
      const detail = (e as CustomEvent).detail as {
        project_id?: string;
        affects?: Record<string, boolean>;
      };
      if (!detail || detail.project_id !== projectId) return;
      const changed = detail.affects || {};
      if (affects.some((k) => changed[k])) schedule();
    }

    window.addEventListener("data_changed", handler);
    return () => {
      window.removeEventListener("data_changed", handler);
      if (timer) clearTimeout(timer);
    };
    // affects 数组按值深比较没必要 —— 调用方传字面量,引用稳定
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);
}
