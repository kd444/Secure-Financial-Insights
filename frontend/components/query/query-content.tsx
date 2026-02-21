"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { apiClient } from "@/lib/api"
import { useAppStore } from "@/lib/store"
import type { QueryRequest, QueryResponse } from "@/lib/types"
import { QueryInputPanel } from "./query-input-panel"
import { QueryResultsPanel } from "./query-results-panel"

export function QueryContent() {
  const [result, setResult] = useState<QueryResponse | null>(null)
  const { addQuery, incrementQueriesToday, updateAverages } = useAppStore()

  const mutation = useMutation({
    mutationFn: (data: QueryRequest) => apiClient.submitQuery(data),
    onSuccess: (data) => {
      setResult(data)
      incrementQueriesToday()

      if (data.evaluation) {
        updateAverages(
          data.evaluation.confidence_score,
          data.evaluation.hallucination_score
        )
        addQuery({
          query_id: data.query_id,
          query: data.query,
          query_type: data.query_type,
          confidence_score: data.evaluation.confidence_score,
          hallucination_score: data.evaluation.hallucination_score,
          status: data.evaluation.status,
          latency_ms: data.latency_ms,
          timestamp: data.timestamp,
        })
      } else {
        addQuery({
          query_id: data.query_id,
          query: data.query,
          query_type: data.query_type,
          confidence_score: 0,
          hallucination_score: 0,
          status: "passed",
          latency_ms: data.latency_ms,
          timestamp: data.timestamp,
        })
      }

      toast.success("Query completed successfully")
    },
    onError: (error) => {
      toast.error(error.message || "Query failed. Please try again.")
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">
          Query
        </h2>
        <p className="text-sm text-muted-foreground">
          Analyze SEC filings and financial documents with AI
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-2">
          <QueryInputPanel
            onSubmit={(data) => mutation.mutate(data)}
            isLoading={mutation.isPending}
          />
        </div>
        <div className="xl:col-span-3">
          <QueryResultsPanel
            result={result}
            isLoading={mutation.isPending}
          />
        </div>
      </div>
    </div>
  )
}
