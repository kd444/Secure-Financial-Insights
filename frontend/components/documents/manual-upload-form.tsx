"use client"

import { useState, useCallback } from "react"
import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { Loader2, Upload, FileUp } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
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
import type { FilingType } from "@/lib/types"
import { cn } from "@/lib/utils"

const filingTypes: { value: FilingType; label: string }[] = [
  { value: "10-K", label: "10-K" },
  { value: "10-Q", label: "10-Q" },
  { value: "8-K", label: "8-K" },
  { value: "earnings", label: "Earnings" },
  { value: "annual_report", label: "Annual Report" },
  { value: "other", label: "Other" },
]

export function ManualUploadForm() {
  const [content, setContent] = useState("")
  const [companyTicker, setCompanyTicker] = useState("")
  const [filingType, setFilingType] = useState<FilingType>("10-K")
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const { addIngestion } = useAppStore()

  const textMutation = useMutation({
    mutationFn: () =>
      apiClient.ingestDocument({
        company_ticker: companyTicker,
        filing_type: filingType,
        content,
      }),
    onSuccess: (data) => {
      addIngestion({
        company: data.company,
        filing_type: data.filing_type,
        chunks_created: data.chunks_created,
        processing_time_ms: data.processing_time_ms,
        timestamp: new Date().toISOString(),
      })
      toast.success(`Document ingested: ${data.chunks_created} chunks created`)
      setContent("")
    },
    onError: (error) => {
      toast.error(error.message || "Document ingestion failed")
    },
  })

  const fileMutation = useMutation({
    mutationFn: (file: File) => apiClient.uploadFile(file),
    onSuccess: (data) => {
      addIngestion({
        company: data.company,
        filing_type: data.filing_type,
        chunks_created: data.chunks_created,
        processing_time_ms: data.processing_time_ms,
        timestamp: new Date().toISOString(),
      })
      toast.success(`File uploaded: ${data.chunks_created} chunks created`)
      setSelectedFile(null)
    },
    onError: (error) => {
      toast.error(error.message || "File upload failed")
    },
  })

  const handleDrag = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (e.type === "dragenter" || e.type === "dragover") {
        setDragActive(true)
      } else if (e.type === "dragleave") {
        setDragActive(false)
      }
    },
    []
  )

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files?.[0]) {
      setSelectedFile(e.dataTransfer.files[0])
    }
  }, [])

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.[0]) {
        setSelectedFile(e.target.files[0])
      }
    },
    []
  )

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* Text Paste */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-medium text-card-foreground">
            Paste Document Text
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                Company Ticker
              </Label>
              <Input
                value={companyTicker}
                onChange={(e) => setCompanyTicker(e.target.value.toUpperCase())}
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
                onValueChange={(v) => setFilingType(v as FilingType)}
              >
                <SelectTrigger className="w-full border-border bg-secondary text-sm text-foreground">
                  <SelectValue />
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
            <Label className="text-xs text-muted-foreground">Content</Label>
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste document text here..."
              className="min-h-[160px] resize-none border-border bg-secondary text-sm text-foreground placeholder:text-muted-foreground"
            />
          </div>

          <Button
            onClick={() => textMutation.mutate()}
            disabled={textMutation.isPending || !content || !companyTicker}
            className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {textMutation.isPending ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Ingesting...
              </>
            ) : (
              <>
                <Upload className="mr-2 size-4" />
                Ingest Document
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* File Upload */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-medium text-card-foreground">
            Upload File
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={cn(
              "flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-12 text-center transition-colors",
              dragActive
                ? "border-primary bg-primary/5"
                : "border-border bg-secondary/30"
            )}
          >
            <FileUp
              className={cn(
                "mb-3 size-8",
                dragActive ? "text-primary" : "text-muted-foreground/50"
              )}
            />
            <p className="text-sm text-muted-foreground">
              Drag and drop a file here, or
            </p>
            <label className="mt-2 cursor-pointer text-sm font-medium text-primary hover:underline">
              browse files
              <input
                type="file"
                className="hidden"
                accept=".txt,.html,.htm,.pdf"
                onChange={handleFileChange}
              />
            </label>
            <p className="mt-1 text-xs text-muted-foreground/70">
              .txt, .html, .htm, .pdf
            </p>
          </div>

          {selectedFile && (
            <div className="flex items-center justify-between rounded-md border border-border bg-secondary/50 px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-foreground">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => fileMutation.mutate(selectedFile)}
                disabled={fileMutation.isPending}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {fileMutation.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  "Upload"
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
