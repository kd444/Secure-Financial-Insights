"use client"

import { useRef, useCallback } from "react"
import ReactMarkdown from "react-markdown"
import {
  FileText,
  ChevronDown,
  Cpu,
  Clock,
  Coins,
  AlertCircle,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { ScoreRing } from "@/components/score-ring"
import { StatusBadge } from "@/components/status-badge"
import type { QueryResponse } from "@/lib/types"
import { cn } from "@/lib/utils"

interface Props {
  result: QueryResponse | null
  isLoading: boolean
}

export function QueryResultsPanel({ result, isLoading }: Props) {
  const citationsRef = useRef<HTMLDivElement>(null)

  const scrollToCitation = useCallback((sourceNum: string) => {
    const el = citationsRef.current?.querySelector(
      `[data-citation="${sourceNum}"]`
    )
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
      el.classList.add("ring-2", "ring-primary")
      setTimeout(() => el.classList.remove("ring-2", "ring-primary"), 2000)
    }
  }, [])

  if (isLoading) {
    return (
      <Card className="border-border bg-card">
        <CardHeader className="pb-4">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-4/6" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <div className="flex gap-6 pt-4">
            <Skeleton className="size-24 rounded-full" />
            <Skeleton className="size-24 rounded-full" />
            <Skeleton className="size-24 rounded-full" />
            <Skeleton className="size-24 rounded-full" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!result) {
    return (
      <Card className="border-border bg-card">
        <CardContent className="flex flex-col items-center justify-center py-24 text-center">
          <FileText className="mb-4 size-12 text-muted-foreground/30" />
          <h3 className="text-lg font-semibold text-card-foreground">
            No Results Yet
          </h3>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Configure your query on the left and click Analyze to get AI-powered
            financial insights with evaluation.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Response */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-card-foreground">
            <FileText className="size-4 text-primary" />
            Response
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="prose prose-invert prose-sm max-w-none text-card-foreground prose-headings:text-card-foreground prose-strong:text-card-foreground prose-a:text-primary">
            <ReactMarkdown
              components={{
                p: ({ children }) => {
                  if (typeof children === "string") {
                    return <p>{renderCitations(children, scrollToCitation)}</p>
                  }
                  return <p>{children}</p>
                },
              }}
            >
              {result.response}
            </ReactMarkdown>
          </div>
        </CardContent>
      </Card>

      {/* Evaluation Scores */}
      {result.evaluation && (
        <Card className="border-border bg-card">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-card-foreground">
                <AlertCircle className="size-4 text-primary" />
                Evaluation Scores
              </CardTitle>
              <StatusBadge status={result.evaluation.status} />
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex flex-wrap items-center justify-center gap-6 py-2 lg:gap-8">
              <ScoreRing
                value={result.evaluation.hallucination_score}
                label="Hallucination"
                invertColor
              />
              <ScoreRing
                value={result.evaluation.factual_grounding_score}
                label="Factual Grounding"
              />
              <ScoreRing
                value={result.evaluation.semantic_consistency_score}
                label="Consistency"
              />
              <ScoreRing
                value={result.evaluation.confidence_score}
                label="Confidence"
              />
            </div>

            {result.evaluation.flags.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  Flags
                </p>
                <div className="flex flex-wrap gap-2">
                  {result.evaluation.flags.map((flag, i) => (
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

            <Accordion type="single" collapsible>
              <AccordionItem value="reasoning" className="border-border">
                <AccordionTrigger className="py-2 text-xs text-muted-foreground hover:text-foreground hover:no-underline">
                  Evaluation Reasoning
                </AccordionTrigger>
                <AccordionContent className="text-xs leading-relaxed text-card-foreground">
                  {result.evaluation.evaluation_reasoning}
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Citations */}
      {result.citations.length > 0 && (
        <Card className="border-border bg-card" ref={citationsRef}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-card-foreground">
              Citations ({result.citations.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="multiple" className="space-y-2">
              {result.citations.map((citation, i) => (
                <AccordionItem
                  key={citation.chunk_id}
                  value={citation.chunk_id}
                  data-citation={`${i + 1}`}
                  className="rounded-md border border-border bg-secondary/30 px-3 transition-all"
                >
                  <AccordionTrigger className="py-3 hover:no-underline">
                    <div className="flex flex-1 items-center gap-3 text-left">
                      <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/20 font-mono text-xs text-primary">
                        {i + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium text-card-foreground">
                          {citation.source_document}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {citation.section}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-16">
                          <Progress
                            value={citation.relevance_score * 100}
                            className="h-1.5"
                          />
                        </div>
                        <span className="font-mono text-xs text-muted-foreground">
                          {(citation.relevance_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <blockquote className="border-l-2 border-primary/30 pl-3 text-xs leading-relaxed text-muted-foreground italic">
                      {citation.text_excerpt}
                    </blockquote>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Metadata Footer */}
      <Card className="border-border bg-card">
        <CardContent className="flex flex-wrap items-center gap-6 py-3">
          <MetadataItem
            icon={Cpu}
            label="Model"
            value={result.model_used}
          />
          <MetadataItem
            icon={Clock}
            label="Latency"
            value={`${result.latency_ms.toFixed(0)}ms`}
          />
          <MetadataItem
            icon={FileText}
            label="Tokens"
            value={`${result.token_usage.prompt_tokens} / ${result.token_usage.completion_tokens} / ${result.token_usage.total_tokens}`}
          />
          <MetadataItem
            icon={Coins}
            label="Cost"
            value={`$${result.token_usage.estimated_cost_usd.toFixed(4)}`}
          />
        </CardContent>
      </Card>
    </div>
  )
}

function MetadataItem({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="size-3.5 text-muted-foreground" />
      <span className="text-xs text-muted-foreground">{label}:</span>
      <span className="font-mono text-xs text-card-foreground">{value}</span>
    </div>
  )
}

function renderCitations(
  text: string,
  onCitationClick: (num: string) => void
) {
  const parts = text.split(/(\[Source \d+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/\[Source (\d+)\]/)
    if (match) {
      return (
        <button
          key={i}
          onClick={() => onCitationClick(match[1])}
          className="mx-0.5 inline-flex items-center rounded-full bg-primary/15 px-2 py-0.5 font-mono text-xs font-medium text-primary transition-colors hover:bg-primary/25"
        >
          {part}
        </button>
      )
    }
    return part
  })
}
