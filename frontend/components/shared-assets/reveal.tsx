"use client";

import type { ElementType, ReactNode } from "react";
import { useInView } from "@/hooks/use-in-view";
import { cx } from "@/lib/utils/cx";

interface RevealProps {
  children: ReactNode;
  className?: string;
  /** Animation delay in ms, for staggering a group of items. */
  delay?: number;
  as?: ElementType;
}

/** Fades and slides a section into place the first time it scrolls into view. */
export function Reveal({ children, className, delay = 0, as: Tag = "div" }: RevealProps) {
  const { ref, inView } = useInView<HTMLDivElement>();

  return (
    <Tag
      ref={ref}
      style={inView ? { animationDelay: `${delay}ms` } : undefined}
      className={cx(
        inView
          ? "animate-in fade-in slide-in-from-bottom-6 fill-mode-both duration-700 ease-out"
          : "opacity-0",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
