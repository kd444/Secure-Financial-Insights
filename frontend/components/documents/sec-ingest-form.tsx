"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Download, CheckCircle2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { apiClient } from "@/lib/api"
import { useAppStore } from "@/lib/store"
import type { SECIngestResponse } from "@/lib/types"

export function SECIngestForm() {
  const [ticker, setTicker] = useState("")
  const [filingType, setFilingType] = useState<"10-K" | "10-Q" | "8-K">("10-K")
  const [numFilings, setNumFilings] = useState(3)
  const [lastResult, setLastResult] = useState<SECIngestResponse | null>(null)
  const { addIngestion } = useAppStore()

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.ingestSEC({ ticker, filing_type: filingType, num_filings: numFilings }),
    onSuccess: (data) => {
      setLastResult(data)
      addIngestion({
        company: data.ticker,
        filing_type: data.filing_type,
        chunks_created: data.total_chunks,
        processing_time_ms: data.processing_time_ms,
        timestamp: new Date().toISOString(),
      })
      toast.success(
        `Ingested ${data.documents_processed} documents (${data.total_chunks} chunks)`
      )
    },
    onError: (error) => {
      toast.error(error.message || "SEC ingestion failed")
    },
  })

  return (
    <div className="space-y-4">
      <Card className="border-border bg-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-medium text-card-foreground">
            Download from SEC EDGAR
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                Ticker Symbol
              </Label>
              <Input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="AAPL"
                className="border-border bg-secondary font-mono text-sm text-foreground placeholder:text-muted-foreground"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                Filing Type
              </Label>
              <Select
                value={filingType}
                onValueChange={(v) => setFilingType(v as "10-K" | "10-Q" | "8-K")}
              >
                <SelectTrigger className="w-full border-border bg-secondary text-sm text-foreground">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10-K">10-K</SelectItem>
                  <SelectItem value="10-Q">10-Q</SelectItem>
                  <SelectItem value="8-K">8-K</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                Number of Filings
              </Label>
              <Input
                type="number"
                min={1}
                max={10}
                value={numFilings}
                onChange={(e) =>
                  setNumFilings(
                    Math.min(10, Math.max(1, parseInt(e.target.value) || 1))
                  )
                }
                className="border-border bg-secondary font-mono text-sm text-foreground"
              />
            </div>
          </div>

          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !ticker}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Downloading...
              </>
            ) : (
              <>
                <Download className="mr-2 size-4" />
                {"Download & Ingest from SEC EDGAR"}
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {lastResult && (
        <Card className="border-success/30 bg-success/5">
          <CardContent className="flex items-start gap-3 py-4">
            <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">
                Ingestion Complete
              </p>
              <div className="flex flex-wrap gap-4 font-mono text-xs text-muted-foreground">
                <span>Ticker: {lastResult.ticker}</span>
                <span>Type: {lastResult.filing_type}</span>
                <span>Docs: {lastResult.documents_processed}</span>
                <span>Chunks: {lastResult.total_chunks}</span>
                <span>
                  Time: {lastResult.processing_time_ms.toFixed(0)}ms
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
