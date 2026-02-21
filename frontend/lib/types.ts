export type QueryType =
  | "risk_summary"
  | "financial_analysis"
  | "market_impact"
  | "sec_filing_qa"
  | "investment_faq"
  | "general"

export type FilingType = "10-K" | "10-Q" | "8-K" | "earnings" | "annual_report" | "other"

export type EvaluationStatus = "passed" | "flagged" | "failed"

export interface HealthResponse {
  status: string
  components: {
    vector_store: { status: string; chunks_count?: number }
    llm_api: { status: string }
  }
  timestamp: string
}

export interface Citation {
  chunk_id: string
  source_document: string
  section: string
  relevance_score: number
  text_excerpt: string
}

export interface EvaluationResult {
  hallucination_score: number
  factual_grounding_score: number
  semantic_consistency_score: number
  confidence_score: number
  status: EvaluationStatus
  flags: string[]
  evaluation_reasoning: string
}

export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  embedding_tokens: number
  estimated_cost_usd: number
}

export interface QueryRequest {
  query: string
  query_type: QueryType
  company_filter?: string | null
  filing_type_filter?: FilingType | null
  top_k: number
  include_evaluation: boolean
  stream: boolean
}

export interface QueryResponse {
  query_id: string
  query: string
  response: string
  citations: Citation[]
  evaluation: EvaluationResult | null
  query_type: string
  model_used: string
  token_usage: TokenUsage
  latency_ms: number
  timestamp: string
}

export interface SECIngestRequest {
  ticker: string
  filing_type: "10-K" | "10-Q" | "8-K"
  num_filings: number
}

export interface SECIngestResponse {
  ticker: string
  filing_type: string
  documents_processed: number
  total_chunks: number
  processing_time_ms: number
}

export interface DocumentIngestRequest {
  company_ticker: string
  filing_type: FilingType
  content: string
}

export interface DocumentIngestResponse {
  document_id: string
  chunks_created: number
  company: string
  filing_type: string
  processing_time_ms: number
  status: string
}

export interface EvaluationRequest {
  response_text: string
  source_chunks: string[]
  query: string
}

export interface EvaluationMetrics {
  total_queries: number
  avg_hallucination_score: number
  avg_confidence_score: number
  avg_consistency_score: number
  pass_rate: number
  flag_rate: number
  fail_rate: number
  avg_latency_ms: number
}

export interface RecentQuery {
  query_id: string
  query: string
  query_type: string
  confidence_score: number
  hallucination_score: number
  status: EvaluationStatus
  latency_ms: number
  timestamp: string
}

export interface IngestionRecord {
  company: string
  filing_type: string
  chunks_created: number
  processing_time_ms: number
  timestamp: string
}
