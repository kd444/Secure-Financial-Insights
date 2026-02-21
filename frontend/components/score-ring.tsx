"use client"

import { cn } from "@/lib/utils"

interface ScoreRingProps {
  value: number
  label: string
  size?: number
  strokeWidth?: number
  invertColor?: boolean
}

function getColor(value: number, invert: boolean) {
  const v = invert ? 1 - value : value
  if (v >= 0.7) return "text-success"
  if (v >= 0.3) return "text-warning"
  return "text-destructive"
}

function getStrokeColor(value: number, invert: boolean) {
  const v = invert ? 1 - value : value
  if (v >= 0.7) return "stroke-success"
  if (v >= 0.3) return "stroke-warning"
  return "stroke-destructive"
}

export function ScoreRing({
  value,
  label,
  size = 100,
  strokeWidth = 8,
  invertColor = false,
}: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - value * circumference

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="-rotate-90"
          aria-hidden="true"
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            className="stroke-secondary"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={cn(
              "transition-all duration-700 ease-out",
              getStrokeColor(value, invertColor)
            )}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={cn(
              "font-mono text-lg font-bold",
              getColor(value, invertColor)
            )}
          >
            {(value * 100).toFixed(0)}
          </span>
        </div>
      </div>
      <span className="text-center text-xs font-medium text-muted-foreground">
        {label}
      </span>
    </div>
  )
}
