"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Cell,
} from "recharts"

interface Props {
  passed: number
  flagged: number
  failed: number
}

export function EvalDistributionChart({ passed, flagged, failed }: Props) {
  const data = [
    { name: "Passed", value: passed, fill: "oklch(0.65 0.20 145)" },
    { name: "Flagged", value: flagged, fill: "oklch(0.75 0.15 85)" },
    { name: "Failed", value: failed, fill: "oklch(0.55 0.22 25)" },
  ]

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} barSize={32}>
        <CartesianGrid
          strokeDasharray="3 3"
          vertical={false}
          stroke="oklch(0.28 0.008 260)"
        />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: "oklch(0.60 0.01 250)" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 11, fill: "oklch(0.60 0.01 250)" }}
          axisLine={false}
          tickLine={false}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
