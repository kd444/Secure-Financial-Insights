"use client"

import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, ShieldCheck, BarChart3 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { ScoreRing } from "@/components/score-ring"
import { StatusBadge } from "@/components/status-badge"
import { apiClient } from "@/lib/api"
import type { EvaluationResult } from "@/lib/types"
import { MetricsDashboard } from "./metrics-dashboard"

export function EvaluationContent() {
  const [responseText, setResponseText] = useState("")
  const [sourceChunks, setSourceChunks] = useState("")
  const [originalQuery, setOriginalQuery] = useState("")
  const [evalResult, setEvalResult] = useState<EvaluationResult | null>(null)

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ["evaluation-metrics"],
    queryFn: () => apiClient.getEvaluationMetrics(),
    retry: 1,
  })

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.evaluate({
        response_text: responseText,
        source_chunks: sourceChunks
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        query: originalQuery,
      }),
    onSuccess: (data) => {
      setEvalResult(data)
      toast.success("Evaluation completed")
    },
    onError: (error) => {
      toast.error(error.message || "Evaluation failed")
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">
          Evaluation
        </h2>
        <p className="text-sm text-muted-foreground">
          Evaluate LLM responses for hallucination, grounding, and consistency
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        {/* Manual Evaluation Form */}
        <Card className="border-border bg-card">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-card-foreground">
              <ShieldCheck className="size-4 text-primary" />
              Manual Evaluation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                Original Query
              </Label>
              <Textarea
                value={originalQuery}
                onChange={(e) => setOriginalQuery(e.target.value)}
                placeholder="Enter the original query..."
                className="min-h-[80px] resize-none border-border bg-secondary text-sm text-foreground placeholder:text-muted-foreground"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                Response Text
              </Label>
              <Textarea
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                placeholder="Paste the LLM response to evaluate..."
                className="min-h-[120px] resize-none border-border bg-secondary text-sm text-foreground placeholder:text-muted-foreground"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                Source Chunks (one per line)
              </Label>
              <Textarea
                value={sourceChunks}
                onChange={(e) => setSourceChunks(e.target.value)}
                placeholder={"Source chunk 1...\nSource chunk 2...\nSource chunk 3..."}
                className="min-h-[120px] resize-none border-border bg-secondary font-mono text-xs text-foreground placeholder:text-muted-foreground"
              />
            </div>

            <Button
              onClick={() => mutation.mutate()}
              disabled={
                mutation.isPending || !responseText || !originalQuery || !sourceChunks
              }
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  Evaluating...
                </>
              ) : (
                <>
                  <ShieldCheck className="mr-2 size-4" />
                  Evaluate
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Evaluation Result */}
        <div className="space-y-4">
          {evalResult ? (
            <Card className="border-border bg-card">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-card-foreground">
                    Evaluation Result
                  </CardTitle>
                  <StatusBadge status={evalResult.status} />
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex flex-wrap items-center justify-center gap-6 py-2">
                  <ScoreRing
                    value={evalResult.hallucination_score}
                    label="Hallucination"
                    invertColor
                  />
                  <ScoreRing
                    value={evalResult.factual_grounding_score}
                    label="Factual Grounding"
                  />
                  <ScoreRing
                    value={evalResult.semantic_consistency_score}
                    label="Consistency"
                  />
                  <ScoreRing
                    value={evalResult.confidence_score}
                    label="Confidence"
                  />
                </div>

                {evalResult.flags.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">
                      Flags
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {evalResult.flags.map((flag, i) => (
                        <span
                          key={i}
                          className="rounded-md border border-warning/30 bg-warning/10 px-2 py-1 text-xs text-warning"
                        >
                          {flag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">
                    Reasoning
                  </p>
                  <p className="text-xs leading-relaxed text-card-foreground">
                    {evalResult.evaluation_reasoning}
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border bg-card">
              <CardContent className="flex flex-col items-center justify-center py-24 text-center">
                <ShieldCheck className="mb-4 size-12 text-muted-foreground/30" />
                <h3 className="text-lg font-semibold text-card-foreground">
                  No Evaluation Yet
                </h3>
                <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                  Fill in the form and click Evaluate to get detailed scoring.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Metrics Dashboard */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-card-foreground">
            <BarChart3 className="size-4 text-primary" />
            Evaluation Metrics Dashboard
          </CardTitle>
        </CardHeader>
        <CardContent>
          {metricsLoading ? (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : metrics ? (
            <MetricsDashboard metrics={metrics} />
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <BarChart3 className="mb-3 size-8 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                No metrics available. Connect your backend to see evaluation data.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
