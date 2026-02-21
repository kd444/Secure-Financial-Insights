"use client"

import { useState } from "react"
import { Search, Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { QueryRequest, QueryType, FilingType } from "@/lib/types"

const queryTypes: { value: QueryType; label: string }[] = [
  { value: "risk_summary", label: "Risk Summary" },
  { value: "financial_analysis", label: "Financial Analysis" },
  { value: "market_impact", label: "Market Impact" },
  { value: "sec_filing_qa", label: "SEC Filing Q&A" },
  { value: "investment_faq", label: "Investment FAQ" },
  { value: "general", label: "General" },
]

const filingTypes: { value: FilingType; label: string }[] = [
  { value: "10-K", label: "10-K" },
  { value: "10-Q", label: "10-Q" },
  { value: "8-K", label: "8-K" },
  { value: "earnings", label: "Earnings" },
  { value: "annual_report", label: "Annual Report" },
  { value: "other", label: "Other" },
]

interface Props {
  onSubmit: (data: QueryRequest) => void
  isLoading: boolean
}

export function QueryInputPanel({ onSubmit, isLoading }: Props) {
  const [query, setQuery] = useState("")
  const [queryType, setQueryType] = useState<QueryType>("financial_analysis")
  const [companyFilter, setCompanyFilter] = useState("")
  const [filingTypeFilter, setFilingTypeFilter] = useState<string>("")
  const [topK, setTopK] = useState(5)
  const [includeEval, setIncludeEval] = useState(true)

  const handleSubmit = () => {
    if (query.length < 5) return
    onSubmit({
      query,
      query_type: queryType,
      company_filter: companyFilter || null,
      filing_type_filter: (filingTypeFilter as FilingType) || null,
      top_k: topK,
      include_evaluation: includeEval,
      stream: false,
    })
  }

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-card-foreground">
          <Search className="size-4 text-primary" />
          Query Configuration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">Query</Label>
          <Textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your financial analysis query..."
            className="min-h-[120px] resize-none border-border bg-secondary text-sm text-foreground placeholder:text-muted-foreground"
          />
          {query.length > 0 && query.length < 5 && (
            <p className="text-xs text-destructive">
              Query must be at least 5 characters
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">Query Type</Label>
          <Select
            value={queryType}
            onValueChange={(v) => setQueryType(v as QueryType)}
          >
            <SelectTrigger className="w-full border-border bg-secondary text-sm text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {queryTypes.map((t) => (
                <SelectItem key={t.value} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">
              Company Filter
            </Label>
            <Input
              value={companyFilter}
              onChange={(e) => setCompanyFilter(e.target.value.toUpperCase())}
              placeholder="e.g. AAPL"
              className="border-border bg-secondary font-mono text-sm text-foreground placeholder:text-muted-foreground"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">
              Filing Type
            </Label>
            <Select
              value={filingTypeFilter}
              onValueChange={setFilingTypeFilter}
            >
              <SelectTrigger className="w-full border-border bg-secondary text-sm text-foreground">
                <SelectValue placeholder="Optional" />
              </SelectTrigger>
              <SelectContent>
                {filingTypes.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs text-muted-foreground">
              Top K Results
            </Label>
            <span className="font-mono text-xs text-primary">{topK}</span>
          </div>
          <Slider
            value={[topK]}
            onValueChange={(v) => setTopK(v[0])}
            min={1}
            max={20}
            step={1}
            className="py-1"
          />
        </div>

        <div className="flex items-center justify-between rounded-md border border-border bg-secondary/50 px-3 py-2">
          <Label className="text-xs text-muted-foreground">
            Include Evaluation
          </Label>
          <Switch checked={includeEval} onCheckedChange={setIncludeEval} />
        </div>

        <Button
          onClick={handleSubmit}
          disabled={isLoading || query.length < 5}
          className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 size-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Search className="mr-2 size-4" />
              Analyze
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
