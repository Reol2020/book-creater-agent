"use client";

import { useEffect } from "react";
import { AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import {
  type InspectorSectionKey,
  useInspectorChanges,
} from "@/lib/store/inspector-changes";
import { cn } from "@/lib/utils";

interface SectionProps {
  sectionKey: InspectorSectionKey;
  title: string;
  count?: number;
  /** 当前是否展开,展开时清除 unread dot */
  isOpen: boolean;
  children: React.ReactNode;
}

export function InspectorSection({
  sectionKey,
  title,
  count,
  isOpen,
  children,
}: SectionProps) {
  const { unread, clear } = useInspectorChanges();
  const hasUnread = unread.has(sectionKey);

  // 展开时清除该 section 的 unread dot
  useEffect(() => {
    if (isOpen && hasUnread) clear(sectionKey);
  }, [isOpen, hasUnread, sectionKey, clear]);

  return (
    <AccordionItem value={sectionKey}>
      <AccordionTrigger className="px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{title}</span>
          {typeof count === "number" && (
            <span className="text-xs text-muted-foreground">{count}</span>
          )}
          {hasUnread && (
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full bg-emerald-500",
                "animate-pulse",
              )}
              title="AI 刚刚改动了这里"
            />
          )}
        </div>
      </AccordionTrigger>
      <AccordionContent className="px-4 pb-3">{children}</AccordionContent>
    </AccordionItem>
  );
}
