"""Prompt templates for financial analysis use cases.

Each prompt is designed for a specific query type and enforces:
- Citation requirement (forces the model to ground answers in sources)
- Confidence expression
- Financial domain specificity
- Output structure for downstream evaluation
"""

from __future__ import annotations

from src.models.schemas import QueryType

SYSTEM_PROMPT = """You are a senior financial analyst AI assistant with expertise in SEC filings,
earnings reports, and investment analysis. You provide accurate, well-sourced financial insights.

CRITICAL RULES:
1. ONLY use information from the provided source documents. NEVER fabricate data.
2. Every factual claim MUST include a citation in [Source N] format.
3. If the source documents don't contain enough information, say so explicitly.
4. Express confidence levels: HIGH (directly stated in sources), MEDIUM (inferred from sources),
   LOW (limited source support).
5. For numerical data (revenue, EPS, ratios), quote exact figures from sources.
6. Flag any inconsistencies between different source documents.
7. NEVER provide investment advice or recommendations."""


def build_rag_prompt(
    query: str,
    context_chunks: list[str],
    query_type: QueryType,
) -> list[dict[str, str]]:
    """Build the full prompt with context injection and query-type-specific instructions.

    Args:
        query: User's question.
        context_chunks: Retrieved document chunks to use as context.
        query_type: Type of financial query for specialized instructions.

    Returns:
        List of message dicts in OpenAI chat format.
    """
    # Format context with numbered sources for citation
    formatted_context = _format_context(context_chunks)

    # Get query-type-specific instructions
    type_instructions = QUERY_TYPE_INSTRUCTIONS.get(query_type, "")

    user_prompt = f"""## SOURCE DOCUMENTS
{formatted_context}

## QUERY TYPE
{query_type.value}

## SPECIFIC INSTRUCTIONS
{type_instructions}

## USER QUESTION
{query}

## RESPONSE FORMAT
Provide a structured response with:
1. **Summary**: A concise answer (2-3 sentences)
2. **Detailed Analysis**: Thorough analysis with [Source N] citations for every factual claim
3. **Key Figures**: Any relevant numerical data from the sources
4. **Confidence Assessment**: Your confidence level (HIGH/MEDIUM/LOW) with reasoning
5. **Caveats**: Any limitations or missing information

Begin your response:"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def _format_context(chunks: list[str]) -> str:
    """Format context chunks with numbered source markers."""
    if not chunks:
        return "[No source documents available]"

    formatted_parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        formatted_parts.append(f"[Source {i}]\n{chunk}\n")

    return "\n---\n".join(formatted_parts)


# Query-type-specific prompt additions
QUERY_TYPE_INSTRUCTIONS: dict[QueryType, str] = {
    QueryType.RISK_SUMMARY: """Focus on:
- Identified risk factors from SEC filings
- Quantified financial exposure where available
- Comparison with prior period risk disclosures
- Regulatory and compliance risks
- Market and competitive risks
Cite specific risk factor items from 10-K/10-Q filings.""",

    QueryType.FINANCIAL_ANALYSIS: """Focus on:
- Revenue trends and growth rates
- Profitability metrics (gross margin, operating margin, net margin)
- Cash flow analysis
- Balance sheet health (debt/equity, current ratio)
- Comparison with prior periods
Provide exact figures with citations. Use tables for numerical comparisons.""",

    QueryType.MARKET_IMPACT: """Focus on:
- How specific events affect the company's financial position
- Revenue impact assessment
- Supply chain or operational disruptions
- Competitive landscape changes
- Forward-looking implications based on filed guidance
Ground all analysis in source documents. Avoid speculation.""",

    QueryType.SEC_FILING_QA: """Focus on:
- Direct answers from SEC filing content
- Exact quotes where appropriate
- Section references (e.g., "Item 1A - Risk Factors")
- Filing-specific details (dates, amendments, exhibits)
Be precise and reference specific filing sections.""",

    QueryType.INVESTMENT_FAQ: """Focus on:
- Factual information only (no recommendations)
- Company fundamentals from filings
- Historical performance data
- Management discussion highlights
- Disclosed outlook and guidance
IMPORTANT: Do NOT provide investment advice. Present facts only.""",

    QueryType.GENERAL: """Provide a thorough answer grounded in the source documents.
Cite all factual claims. Express confidence level based on source coverage.""",
}


# Evaluation prompt for hallucination detection (used by evaluation layer)
HALLUCINATION_CHECK_PROMPT = """You are an expert fact-checker for financial documents.
Your task is to evaluate whether a generated response is factually grounded in the provided source documents.

## SOURCE DOCUMENTS
{context}

## GENERATED RESPONSE
{response}

## ORIGINAL QUESTION
{query}

## EVALUATION CRITERIA
For each factual claim in the response, determine:
1. SUPPORTED: The claim is directly stated in or logically derivable from the sources
2. UNSUPPORTED: The claim has no basis in the provided sources
3. CONTRADICTED: The claim contradicts information in the sources

## OUTPUT FORMAT (JSON)
{{
    "claims": [
        {{"claim": "...", "verdict": "SUPPORTED|UNSUPPORTED|CONTRADICTED", "evidence": "...", "source_ref": "Source N"}}
    ],
    "hallucination_score": 0.0-1.0,
    "factual_grounding_score": 0.0-1.0,
    "reasoning": "..."
}}

Evaluate now:"""


CONSISTENCY_CHECK_PROMPT = """Compare these two responses to the same financial query and evaluate their semantic consistency.

## QUERY
{query}

## RESPONSE A
{response_a}

## RESPONSE B
{response_b}

## EVALUATION
Rate the semantic consistency from 0.0 (completely different) to 1.0 (identical meaning).
Focus on: numerical agreement, directional agreement (up/down/stable), qualitative consistency.

Output JSON:
{{
    "consistency_score": 0.0-1.0,
    "discrepancies": ["..."],
    "reasoning": "..."
}}"""
