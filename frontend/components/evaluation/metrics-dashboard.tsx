"use client"

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import type { EvaluationMetrics } from "@/lib/types"

interface Props {
  metrics: EvaluationMetrics
}

const COLORS = [
  "oklch(0.65 0.20 145)",
  "oklch(0.75 0.15 85)",
  "oklch(0.55 0.22 25)",
]

export function MetricsDashboard({ metrics }: Props) {
  const pieData = [
    { name: "Pass", value: metrics.pass_rate },
    { name: "Flag", value: metrics.flag_rate },
    { name: "Fail", value: metrics.fail_rate },
  ]

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="grid grid-cols-2 gap-4 lg:col-span-2">
        <MetricCard
          label="Total Queries"
          value={metrics.total_queries.toLocaleString()}
        />
        <MetricCard
          label="Avg Hallucination"
          value={`${(metrics.avg_hallucination_score * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Avg Confidence"
          value={`${(metrics.avg_confidence_score * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Avg Consistency"
          value={`${(metrics.avg_consistency_score * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Avg Latency"
          value={`${metrics.avg_latency_ms.toFixed(0)}ms`}
        />
        <MetricCard
          label="Pass Rate"
          value={`${(metrics.pass_rate * 100).toFixed(1)}%`}
        />
      </div>

      <div className="flex flex-col items-center justify-center">
        <p className="mb-2 text-xs font-medium text-muted-foreground">
          Pass / Flag / Fail Distribution
        </p>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={4}
              dataKey="value"
              stroke="none"
            >
              {pieData.map((_, index) => (
                <Cell key={index} fill={COLORS[index]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: "oklch(0.18 0.005 260)",
                border: "1px solid oklch(0.28 0.008 260)",
                borderRadius: "6px",
                fontSize: "12px",
                color: "oklch(0.95 0.01 250)",
              }}
              formatter={(value: number) => [
                `${(value * 100).toFixed(1)}%`,
              ]}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-success" />
            Pass
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-warning" />
            Flag
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-destructive" />
            Fail
          </span>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-secondary/30 px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-mono text-lg font-bold text-card-foreground">
        {value}
      </p>
    </div>
  )
}
