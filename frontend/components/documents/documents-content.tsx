"use client"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { FileText, Database } from "lucide-react"
import { useAppStore } from "@/lib/store"
import { SECIngestForm } from "./sec-ingest-form"
import { ManualUploadForm } from "./manual-upload-form"

export function DocumentsContent() {
  const { ingestionHistory } = useAppStore()

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">
          Documents
        </h2>
        <p className="text-sm text-muted-foreground">
          Ingest SEC filings and financial documents into the knowledge base
        </p>
      </div>

      <Tabs defaultValue="sec" className="space-y-4">
        <TabsList className="bg-secondary">
          <TabsTrigger value="sec" className="gap-2 text-xs">
            <Database className="size-3.5" />
            SEC EDGAR
          </TabsTrigger>
          <TabsTrigger value="manual" className="gap-2 text-xs">
            <FileText className="size-3.5" />
            Manual Upload
          </TabsTrigger>
        </TabsList>

        <TabsContent value="sec">
          <SECIngestForm />
        </TabsContent>

        <TabsContent value="manual">
          <ManualUploadForm />
        </TabsContent>
      </Tabs>

      {/* Ingestion History */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-card-foreground">
            Ingestion History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {ingestionHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Database className="mb-3 size-8 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                No documents ingested yet.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="text-xs text-muted-foreground">
                      Company
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground">
                      Filing Type
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground">
                      Chunks
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground">
                      Processing Time
                    </TableHead>
                    <TableHead className="text-right text-xs text-muted-foreground">
                      Timestamp
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ingestionHistory.map((record, i) => (
                    <TableRow key={i} className="border-border">
                      <TableCell className="font-mono text-xs font-medium text-card-foreground">
                        {record.company}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {record.filing_type}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-card-foreground">
                        {record.chunks_created}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {record.processing_time_ms.toFixed(0)}ms
                      </TableCell>
                      <TableCell className="text-right text-xs text-muted-foreground">
                        {new Date(record.timestamp).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
