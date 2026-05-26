"use client";

import Link from "next/link";
import { useEffect } from "react";
import {
  BookOpenText,
  Settings as SettingsIcon,
  CircleDot,
  Circle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useActiveProfile } from "@/lib/store/active-profile";
import { cn } from "@/lib/utils";

interface AppHeaderProps {
  /** 中间区域:面包屑或工作区标题 */
  middle?: React.ReactNode;
  className?: string;
}

export function AppHeader({ middle, className }: AppHeaderProps) {
  const { profile, refresh } = useActiveProfile();

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex h-14 items-center gap-4 border-b border-border/60 bg-background/85 px-6 backdrop-blur",
        className,
      )}
    >
      <Link
        href="/"
        className="flex items-center gap-2 font-medium tracking-tight"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <BookOpenText className="h-4 w-4" />
        </span>
        <span className="text-sm">Book Creater Agent</span>
      </Link>

      <div className="flex-1 truncate">{middle}</div>

      <Link href="/settings" className="hidden sm:block">
        {profile ? (
          <Badge variant="success" className="gap-1.5">
            <CircleDot className="h-3 w-3" />
            <span className="font-normal text-foreground/70">已启用</span>
            <span className="font-medium">{profile.name}</span>
            <span className="text-foreground/50">·</span>
            <span className="font-mono text-[11px]">{profile.model}</span>
          </Badge>
        ) : (
          <Badge variant="outline" className="gap-1.5">
            <Circle className="h-3 w-3" />
            未启用 LLM,点击配置
          </Badge>
        )}
      </Link>

      <Button asChild variant="ghost" size="icon" className="h-8 w-8">
        <Link href="/settings" aria-label="设置">
          <SettingsIcon className="h-4 w-4" />
        </Link>
      </Button>
    </header>
  );
}
