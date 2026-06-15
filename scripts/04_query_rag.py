#!/usr/bin/env python3
"""
04_query_rag.py  — Layer 3 (the retrieval Agent 1 and Agent 3 depend on)

Demonstrates the two retrieval modes ProcedureGuard's agents use against the
multimodal index:

  Agent 1 (SOP ingestion)  -> retrieve_step_context(): pulls full step context
                              INCLUDING verbalized diagram captions, to build a
                              richer compliance checklist.

  Agent 3 (Q&A chat)        -> answer_question(): hybrid (vector + keyword) search,
                              returns evidence with image paths for the dashboard's
                              evidence viewer.

Usage:
    python 04_query_rag.py "How are the heatbed screws tightened?"
"""
import os
import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery

SEARCH = os.environ["SEARCH_ENDPOINT"]
KEY = os.environ["SEARCH_ADMIN_KEY"]
INDEX = os.environ["SEARCH_INDEX_NAME"]

client = SearchClient(SEARCH, INDEX, AzureKeyCredential(KEY))


def retrieve_step_context(step_query: str, top: int = 5) -> list[dict]:
    """Agent 1: hybrid search; surfaces both text steps and diagram captions."""
    vq = VectorizableTextQuery(text=step_query, k_nearest_neighbors=top,
                               fields="content_embedding")
    results = client.search(
        search_text=step_query,           # keyword half of hybrid
        vector_queries=[vq],              # vector half (auto-embedded by the vectorizer)
        select=["content_text", "content_type", "content_path", "document_title"],
        top=top,
    )
    return [
        {
            "type": r["content_type"],                 # 'text' or 'image_caption'
            "text": r["content_text"],
            "diagram_image_path": r.get("content_path"),  # for evidence viewer
            "source": r.get("document_title"),
            "score": r["@search.score"],
        }
        for r in results
    ]


def answer_question(question: str, top: int = 5) -> None:
    """Agent 3: semantic hybrid search, prints grounded evidence."""
    vq = VectorizableTextQuery(text=question, k_nearest_neighbors=top,
                               fields="content_embedding")
    results = client.search(
        search_text=question,
        vector_queries=[vq],
        query_type="semantic",
        semantic_configuration_name="sop-semantic-config",
        select=["content_text", "content_type", "content_path", "document_title"],
        top=top,
    )
    print(f"\n=== Evidence for: {question!r} ===")
    for i, r in enumerate(results, 1):
        kind = r["content_type"]
        tag = "[DIAGRAM]" if kind == "image_caption" else "[TEXT]"
        print(f"\n{i}. {tag}  source={r.get('document_title')}")
        print(f"   {r['content_text'][:300]}")
        if r.get("content_path"):
            print(f"   image: {r['content_path']}   <- show this in the evidence viewer")


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "How is the assembly step performed?"
    print(">> Agent 1 style step-context retrieval:")
    for hit in retrieve_step_context(q):
        marker = "(diagram)" if hit["type"] == "image_caption" else "(text)"
        print(f"   {marker} score={hit['score']:.3f}  {hit['text'][:120]}")
    answer_question(q)
