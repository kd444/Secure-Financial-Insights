import type {
  HealthResponse,
  QueryRequest,
  QueryResponse,
  SECIngestRequest,
  SECIngestResponse,
  DocumentIngestRequest,
  DocumentIngestResponse,
  EvaluationRequest,
  EvaluationResult,
  EvaluationMetrics,
} from "./types"

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    })

    if (!res.ok) {
      const errorBody = await res.text().catch(() => "Unknown error")
      throw new Error(
        `API Error ${res.status}: ${errorBody}`
      )
    }

    return res.json()
  }

  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health")
  }

  async submitQuery(data: QueryRequest): Promise<QueryResponse> {
    return this.request<QueryResponse>("/api/v1/query/", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async ingestSEC(data: SECIngestRequest): Promise<SECIngestResponse> {
    return this.request<SECIngestResponse>("/api/v1/documents/ingest/sec", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async ingestDocument(
    data: DocumentIngestRequest
  ): Promise<DocumentIngestResponse> {
    return this.request<DocumentIngestResponse>("/api/v1/documents/ingest", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async uploadFile(file: File): Promise<DocumentIngestResponse> {
    const formData = new FormData()
    formData.append("file", file)

    const url = `${this.baseUrl}/api/v1/documents/upload`
    const res = await fetch(url, {
      method: "POST",
      body: formData,
    })

    if (!res.ok) {
      const errorBody = await res.text().catch(() => "Unknown error")
      throw new Error(`API Error ${res.status}: ${errorBody}`)
    }

    return res.json()
  }

  async evaluate(data: EvaluationRequest): Promise<EvaluationResult> {
    return this.request<EvaluationResult>("/api/v1/evaluation/evaluate", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getEvaluationMetrics(): Promise<EvaluationMetrics> {
    return this.request<EvaluationMetrics>("/api/v1/evaluation/metrics")
  }
}

export const apiClient = new ApiClient(BASE_URL)
