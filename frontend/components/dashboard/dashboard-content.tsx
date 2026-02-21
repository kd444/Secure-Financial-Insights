"use client"

import { useQuery } from "@tanstack/react-query"
import {
  Database,
  Search,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { StatusBadge } from "@/components/status-badge"
import { apiClient } from "@/lib/api"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { EvalDistributionChart } from "./eval-distribution-chart"

export function DashboardContent() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 30000,
    retry: 1,
  })

  const {
    recentQueries,
    queriesToday,
    avgConfidence,
    avgHallucination,
  } = useAppStore()

  const chunksCount =
    health?.components?.vector_store?.chunks_count ?? 0

  const passCount = recentQueries.filter((q) => q.status === "passed").length
  const flagCount = recentQueries.filter((q) => q.status === "flagged").length
  const failCount = recentQueries.filter((q) => q.status === "failed").length

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">
          Dashboard
        </h2>
        <p className="text-sm text-muted-foreground">
          System overview and recent query activity
        </p>
      </div>

      {/* System Health */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-card-foreground">
            <Clock className="size-4 text-primary" />
            System Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          {healthLoading ? (
            <div className="flex gap-4">
              <Skeleton className="h-8 w-32" />
              <Skeleton className="h-8 w-32" />
            </div>
          ) : (
            <div className="flex flex-wrap gap-4">
              {health?.components &&
                Object.entries(health.components).map(([key, comp]) => (
                  <div
                    key={key}
                    className="flex items-center gap-2 rounded-md border border-border bg-secondary/50 px-3 py-2"
                  >
                    <div
                      className={cn(
                        "size-2 rounded-full",
                        comp.status === "healthy"
                          ? "bg-success"
                          : comp.status === "degraded"
                          ? "bg-warning"
                          : "bg-destructive"
                      )}
                    />
                    <span className="font-mono text-xs text-card-foreground">
                      {key.replace("_", " ")}
                    </span>
                    <span
                      className={cn(
                        "font-mono text-xs",
                        comp.status === "healthy"
                          ? "text-success"
                          : comp.status === "degraded"
                          ? "text-warning"
                          : "text-destructive"
                      )}
                    >
                      {comp.status}
                    </span>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={Database}
          label="Documents Indexed"
          value={chunksCount.toLocaleString()}
          subtext="vector chunks"
        />
        <StatCard
          icon={Search}
          label="Queries Today"
          value={queriesToday.toString()}
          subtext="total queries"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg Confidence"
          value={
            queriesToday > 0
              ? (avgConfidence * 100).toFixed(1) + "%"
              : "--"
          }
          subtext="confidence score"
        />
        <StatCard
          icon={AlertTriangle}
          label="Avg Hallucination"
          value={
            queriesToday > 0
              ? (avgHallucination * 100).toFixed(1) + "%"
              : "--"
          }
          subtext="hallucination rate"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Queries Table */}
        <Card className="border-border bg-card lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-card-foreground">
              Recent Queries
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recentQueries.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Search className="mb-3 size-8 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No queries yet. Head to the Query page to get started.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead className="text-xs text-muted-foreground">
                        Query
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground">
                        Type
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground">
                        Confidence
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground">
                        Halluc.
                      </TableHead>
                      <TableHead className="text-xs text-muted-foreground">
                        Status
                      </TableHead>
                      <TableHead className="text-right text-xs text-muted-foreground">
                        Latency
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentQueries.slice(0, 10).map((q) => (
                      <TableRow
                        key={q.query_id}
                        className="border-border"
                      >
                        <TableCell className="max-w-[200px] truncate text-xs text-card-foreground">
                          {q.query}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {q.query_type}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-card-foreground">
                          {(q.confidence_score * 100).toFixed(0)}%
                        </TableCell>
                        <TableCell className="font-mono text-xs text-card-foreground">
                          {(q.hallucination_score * 100).toFixed(0)}%
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={q.status} />
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-muted-foreground">
                          {q.latency_ms.toFixed(0)}ms
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Eval Distribution Chart */}
        <Card className="border-border bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-card-foreground">
              Evaluation Quality
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recentQueries.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircle2 className="mb-3 size-8 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">
                  No evaluation data yet.
                </p>
              </div>
            ) : (
              <EvalDistributionChart
                passed={passCount}
                flagged={flagCount}
                failed={failCount}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  subtext,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  subtext: string
}) {
  return (
    <Card className="border-border bg-card">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-md bg-primary/10">
            <Icon className="size-4 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="font-mono text-xl font-bold text-card-foreground">
              {value}
            </p>
            <p className="text-xs text-muted-foreground">{subtext}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
