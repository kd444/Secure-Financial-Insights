"use client"

import { useQuery } from "@tanstack/react-query"
import { Settings, Server, Cpu, Database, RefreshCw } from "lucide-react"
import { AppShell } from "@/components/app-shell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { apiClient } from "@/lib/api"
import { cn } from "@/lib/utils"

export default function SettingsPage() {
  const {
    data: health,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.getHealth(),
    retry: 1,
  })

  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            Settings
          </h2>
          <p className="text-sm text-muted-foreground">
            System configuration and connection status
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* API Configuration */}
          <Card className="border-border bg-card">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-card-foreground">
                <Server className="size-4 text-primary" />
                API Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">
                  Backend URL
                </Label>
                <Input
                  value={apiUrl}
                  readOnly
                  className="border-border bg-secondary font-mono text-sm text-foreground"
                />
                <p className="text-xs text-muted-foreground">
                  Set via NEXT_PUBLIC_API_URL environment variable
                </p>
              </div>
            </CardContent>
          </Card>

          {/* System Status */}
          <Card className="border-border bg-card">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-sm font-medium text-card-foreground">
                  <Cpu className="size-4 text-primary" />
                  System Status
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => refetch()}
                  disabled={isFetching}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  <RefreshCw
                    className={cn(
                      "mr-1 size-3",
                      isFetching && "animate-spin"
                    )}
                  />
                  Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : health ? (
                <>
                  <div className="flex items-center justify-between rounded-md border border-border bg-secondary/30 px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Database className="size-4 text-muted-foreground" />
                      <div>
                        <p className="text-xs font-medium text-card-foreground">
                          Vector Store
                        </p>
                        <p className="font-mono text-xs text-muted-foreground">
                          {health.components.vector_store.chunks_count ?? 0}{" "}
                          chunks
                        </p>
                      </div>
                    </div>
                    <StatusDot
                      status={health.components.vector_store.status}
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-md border border-border bg-secondary/30 px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Cpu className="size-4 text-muted-foreground" />
                      <div>
                        <p className="text-xs font-medium text-card-foreground">
                          LLM API
                        </p>
                        <p className="font-mono text-xs text-muted-foreground">
                          Language model endpoint
                        </p>
                      </div>
                    </div>
                    <StatusDot status={health.components.llm_api.status} />
                  </div>

                  <p className="pt-1 font-mono text-xs text-muted-foreground">
                    Last checked:{" "}
                    {new Date(health.timestamp).toLocaleString()}
                  </p>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <Server className="mb-3 size-8 text-destructive/50" />
                  <p className="text-sm text-muted-foreground">
                    Unable to connect to backend
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => refetch()}
                    className="mt-2 text-xs text-primary"
                  >
                    Retry Connection
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* About */}
        <Card className="border-border bg-card">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-card-foreground">
              <Settings className="size-4 text-primary" />
              About
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>
                <span className="font-medium text-card-foreground">
                  Secure Financial Insights Copilot
                </span>{" "}
                is an enterprise AI-powered platform for analyzing SEC filings,
                financial documents, and generating risk assessments with
                built-in hallucination detection.
              </p>
              <div className="flex flex-wrap gap-4 pt-2 font-mono text-xs">
                <span>Next.js 16</span>
                <span>FastAPI Backend</span>
                <span>RAG Pipeline</span>
                <span>LLM Evaluation</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}

function StatusDot({ status }: { status: string }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "font-mono text-xs",
          status === "healthy"
            ? "text-success"
            : status === "degraded"
            ? "text-warning"
            : "text-destructive"
        )}
      >
        {status}
      </span>
      <div
        className={cn(
          "size-2 rounded-full",
          status === "healthy"
            ? "bg-success"
            : status === "degraded"
            ? "bg-warning"
            : "bg-destructive"
        )}
      />
    </div>
  )
}
