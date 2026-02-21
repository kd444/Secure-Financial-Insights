"use client"

import { cn } from "@/lib/utils"
import type { EvaluationStatus } from "@/lib/types"

const statusConfig: Record<
  EvaluationStatus,
  { label: string; className: string }
> = {
  passed: {
    label: "PASSED",
    className: "bg-success/15 text-success border-success/30",
  },
  flagged: {
    label: "FLAGGED",
    className: "bg-warning/15 text-warning border-warning/30",
  },
  failed: {
    label: "FAILED",
    className: "bg-destructive/15 text-destructive border-destructive/30",
  },
}

export function StatusBadge({ status }: { status: EvaluationStatus }) {
  const config = statusConfig[status]
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-xs font-semibold",
        config.className
      )}
    >
      {config.label}
    </span>
  )
}
