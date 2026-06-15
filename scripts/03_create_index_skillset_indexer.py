#!/usr/bin/env python3
"""
03_create_index_skillset_indexer.py  — Layer 2 (data extraction)  *** THE CORE ***

Builds the full Multimodal RAG pipeline in Azure AI Search:
  1. Data source  -> the Blob container with SOP PDFs
  2. Index        -> text + verbalized-diagram captions + 3072-dim vectors + image refs
  3. Skillset     -> Document Layout (text+images) -> GPT-4o verbalization -> embeddings
  4. Indexer      -> runs the skillset over the blobs and populates the index
  5. Poll status until indexing completes

Everything is done over the REST API so it is reproducible in CI (Week 3/4 deliverable).

NOTE ON SKILL TYPES: the verbalization skill type string in skillset.json targets a
preview API. If Azure returns an "unknown skill type" error, build the skillset once via
the portal wizard (Import data new -> Multimodal RAG), export it, save it as skillset.json,
and re-run this script — it just POSTs whatever skillset.json contains.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

SEARCH = os.environ["SEARCH_ENDPOINT"].rstrip("/")
KEY = os.environ["SEARCH_ADMIN_KEY"]
API = os.environ.get("SEARCH_API_VERSION", "2025-08-01-preview")
INDEX = os.environ["SEARCH_INDEX_NAME"]
STORAGE_CONN = os.environ["STORAGE_CONNECTION_STRING"]
CONTAINER = os.environ["STORAGE_CONTAINER"]
AOAI_ENDPOINT = os.environ["AOAI_ENDPOINT"].rstrip("/")
AOAI_KEY = os.environ["AOAI_KEY"]
EMBED_DEPLOY = os.environ.get("AOAI_EMBED_DEPLOYMENT", "text-embedding-3-large")
GPT4O_DEPLOY = os.environ.get("AOAI_GPT4O_DEPLOYMENT", "gpt-4o")

H = {"Content-Type": "application/json", "api-key": KEY}
DS_NAME = "procedureguard-sop-datasource"
SS_NAME = "procedureguard-sop-skillset"
IXR_NAME = "procedureguard-sop-indexer"


def put(kind: str, name: str, body: dict) -> None:
    url = f"{SEARCH}/{kind}/{name}?api-version={API}"
    r = requests.put(url, headers=H, json=body)
    if r.status_code not in (200, 201, 204):
        print(f"[ERR] {kind}/{name}: {r.status_code}\n{r.text}")
        r.raise_for_status()
    print(f"[ok] {kind}/{name}")


def create_data_source() -> None:
    body = {
        "name": DS_NAME,
        "type": "azureblob",
        "credentials": {"connectionString": STORAGE_CONN},
        "container": {"name": CONTAINER, "query": "sop/"},
    }
    put("datasources", DS_NAME, body)


def create_index() -> None:
    body = {
        "name": INDEX,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True,
             "analyzer": "keyword"},
            {"name": "parent_id", "type": "Edm.String", "filterable": True},
            {"name": "content_text", "type": "Edm.String", "searchable": True},
            {"name": "content_type", "type": "Edm.String", "filterable": True,
             "facetable": True},
            {"name": "content_path", "type": "Edm.String", "retrievable": True},
            {"name": "document_title", "type": "Edm.String", "filterable": True,
             "searchable": True},
            {"name": "content_embedding", "type": "Collection(Edm.Single)",
             "searchable": True, "dimensions": 3072,
             "vectorSearchProfile": "vprofile"},
        ],
        "vectorSearch": {
            "algorithms": [{"name": "hnsw-algo", "kind": "hnsw"}],
            "vectorizers": [{
                "name": "aoai-vectorizer",
                "kind": "azureOpenAI",
                "azureOpenAIParameters": {
                    "resourceUri": AOAI_ENDPOINT,
                    "deploymentId": EMBED_DEPLOY,
                    "modelName": "text-embedding-3-large",
                    "apiKey": AOAI_KEY,
                },
            }],
            "profiles": [{
                "name": "vprofile",
                "algorithm": "hnsw-algo",
                "vectorizer": "aoai-vectorizer",
            }],
        },
        "semantic": {
            "configurations": [{
                "name": "sop-semantic-config",
                "prioritizedFields": {
                    "titleField": {"fieldName": "document_title"},
                    "prioritizedContentFields": [{"fieldName": "content_text"}],
                },
            }]
        },
    }
    put("indexes", INDEX, body)


def create_skillset() -> None:
    raw = Path(__file__).with_name("skillset.json").read_text()
    raw = raw.replace("AOAI_ENDPOINT_PLACEHOLDER", AOAI_ENDPOINT)
    raw = raw.replace(
        "AOAI_GPT4O_ENDPOINT_PLACEHOLDER",
        f"{AOAI_ENDPOINT}/openai/deployments/{GPT4O_DEPLOY}/chat/completions"
        f"?api-version=2024-08-01-preview",
    )
    body = json.loads(raw)
    # Inject the AOAI key so the embedding/verbalization skills can authenticate.
    for sk in body["skills"]:
        if sk["@odata.type"].endswith("AzureOpenAIEmbeddingSkill"):
            sk["apiKey"] = AOAI_KEY
        if sk["@odata.type"].endswith("ChatCompletionSkill"):
            sk.setdefault("authIdentity", None)
            sk["apiKey"] = AOAI_KEY
    put("skillsets", SS_NAME, body)


def create_indexer() -> None:
    body = {
        "name": IXR_NAME,
        "dataSourceName": DS_NAME,
        "skillsetName": SS_NAME,
        "targetIndexName": INDEX,
        "parameters": {
            "configuration": {
                "dataToExtract": "contentAndMetadata",
                "allowSkillsetToReadFileData": True,
            }
        },
        "fieldMappings": [
            {"sourceFieldName": "metadata_storage_name",
             "targetFieldName": "document_title"}
        ],
    }
    put("indexers", IXR_NAME, body)


def poll_indexer() -> None:
    url = f"{SEARCH}/indexers/{IXR_NAME}/status?api-version={API}"
    print("\n>> Indexing... (this calls GPT-4o per diagram, can take minutes)")
    while True:
        r = requests.get(url, headers=H)
        r.raise_for_status()
        last = r.json().get("lastResult") or {}
        status = last.get("status", "pending")
        print(f"   status={status}  items={last.get('itemsProcessed', 0)}"
              f"  failed={last.get('itemsFailed', 0)}")
        if status in ("success", "transientFailure"):
            errs = last.get("errors", [])
            if errs:
                print("   errors:")
                for e in errs[:5]:
                    print(f"     - {e.get('errorMessage')}")
            break
        if status == "reset":
            break
        time.sleep(15)


def main() -> None:
    create_data_source()
    create_index()
    create_skillset()
    create_indexer()
    poll_indexer()
    print("\n[done] Multimodal index is built. Run 04_query_rag.py to test retrieval.")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError:
        print("\n[!] A REST call failed (see above). If it was the skillset and the error "
              "mentions an unknown skill type, regenerate skillset.json via the portal "
              "Multimodal RAG wizard, then re-run this script.", file=sys.stderr)
        sys.exit(1)
