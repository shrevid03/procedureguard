# ProcedureGuard — Azure AI Search + Multimodal RAG (SOP pipeline)

This repo implements **Layer 2 (SOP pipeline)** and the retrieval that feeds **Layer 3
(Agent 1 + Agent 3)** of the ProcedureGuard architecture, using the
`openmarciea/openmarciea-again` dataset.

It is built to run on **your machine** — where you have Azure CLI, network access, and an
Azure subscription. Every script is idempotent-ish and prints what it is doing.

---

## First: where does this sit in the architecture?

Your architecture has **two parallel pipelines** in Layer 2:

| Pipeline | Input | Azure service | This repo? |
|---|---|---|---|
| **SOP pipeline** | SOP **PDF** (assembly manual) | Doc Intelligence + **Azure AI Search Multimodal RAG** | ✅ YES — this is what we build |
| **Video pipeline** | Manufacturing **MP4** | Azure AI **Content Understanding** | ❌ separate (covered elsewhere) |

**Multimodal RAG only applies to the SOP document side.** It indexes the text *and* the
diagrams, torque tables, and safety symbols inside the assembly manual PDF so that Agent 1
(checklist generation) and Agent 3 (Q&A chat) can retrieve and reason over visual SOP
content — not just plain text.

The `openmarciea-again` dataset is the OPENMARCIE pair from your architecture doc:
the **Prusa 3D-printer assembly manual (PDF = the SOP)** + **assembly videos (MP4)**.
- The **PDF(s)** → go through this Multimodal RAG pipeline.
- The **MP4(s)** → go to Content Understanding (not here). Script 01 separates them for you.

---

## What gets built (mapped to your architecture)

```
Layer 1 INPUT          → Blob Storage container `sop-docs`   (script 02)
Layer 2 DATA EXTRACTION→ AI Search skillset:                 (script 03)
                          - Document Layout skill  (text + inline images)
                          - Image verbalization    (GPT-4o describes each diagram)
                          - Text + multimodal embeddings (vector search)
                         → Multimodal index `procedureguard-sop-index`
Layer 3 AI AGENTS      → Retrieval functions Agent 1 / Agent 3 call   (script 04)
```

---

## Prerequisites

- Azure subscription with permission to create resources
- Azure CLI logged in: `az login`
- Python 3.10+
- A Kaggle account + API token (`~/.kaggle/kaggle.json`) for `kagglehub`
- Quota for **Azure OpenAI** (`gpt-4o` + `text-embedding-3-large`) in your region

---

## Run order

```bash
# 0. Provision all Azure resources (edit variables at top first)
bash scripts/00_provision_azure.sh

# This writes a .env file with all endpoints + keys. Load it:
set -a && source .env && set +a

# 1. Download the Kaggle dataset and separate PDFs (SOP) from MP4s (video)
python scripts/01_download_and_inspect.py

# 2. Upload the SOP PDFs to Blob Storage (Layer 1)
python scripts/02_upload_to_blob.py

# 3. Create the multimodal index + skillset + indexer, then run it (Layer 2)
python scripts/03_create_index_skillset_indexer.py

# 4. Query the index the way Agent 1 / Agent 3 would (Layer 3)
python scripts/04_query_rag.py "How is the heatbed cable routed during assembly?"
```

---

## Two ways to build the index (read this)

Microsoft ships a **portal wizard** ("Import data (new)" → **Multimodal RAG**) that
auto-generates a *verified* skillset for you. It is the lowest-risk path and I recommend it
for your first run. Script 03 builds the same thing via REST so you can version-control it
and re-run it in CI (your Week 3/4 deliverable), but if a skill `@odata.type` or
`api-version` has moved since this was written, **fall back to the wizard**, then export the
generated skillset JSON (`az rest` / portal) and diff it against `scripts/skillset.json`.

The wizard path is documented here:
https://learn.microsoft.com/en-us/azure/search/search-get-started-portal-image-search

---

## The two multimodal techniques (and why we use both)

1. **Image verbalization** — during indexing, GPT-4o writes a text description of every
   diagram/figure ("Torque sequence for 4 heatbed screws, tighten in a cross pattern").
   That text is embedded alongside the page text. → powers **Agent 1**'s checklist, because
   the criterion may live only in a diagram.

2. **Multimodal embeddings** — text and image are projected into the **same vector space**,
   so a text query can retrieve a diagram directly. → powers **Agent 3**'s evidence viewer
   ("show me the diagram for step 6").

---

## Cost / cleanup

AI Search (Standard) + Azure OpenAI calls cost money while running. To tear everything down:

```bash
az group delete --name $AZ_RESOURCE_GROUP --yes --no-wait
```

---

## File map

| File | Purpose | Architecture layer |
|---|---|---|
| `scripts/00_provision_azure.sh` | Create RG, Storage, AI Search, Azure OpenAI, multimodal embeddings account | infra |
| `scripts/01_download_and_inspect.py` | kagglehub download + split PDF/MP4 | Layer 1 |
| `scripts/02_upload_to_blob.py` | Upload SOP PDFs to Blob | Layer 1 |
| `scripts/03_create_index_skillset_indexer.py` | Multimodal index + skillset + indexer | Layer 2 |
| `scripts/04_query_rag.py` | Retrieval used by Agent 1 / Agent 3 | Layer 3 |
| `scripts/skillset.json` | Reference skillset (verbalization + embeddings) | Layer 2 |
| `requirements.txt` | Python deps | — |
| `.env.example` | Template for endpoints/keys (00 generates the real `.env`) | — |

---

## Handling the 139 GB of video (important)

The dataset is ~139 GB, almost all assembly **video**. You do **not** download it.

- **Multimodal RAG needs only the SOP PDF** (a few MB). Script 01 lists the dataset,
  then uses kagglehub's single-file download (`dataset_download(DATASET, path="file.pdf")`)
  to pull *only* the document. The videos are listed but skipped.

- **If you later need the videos** for the Content Understanding pipeline, never route
  them through your laptop. Move them cloud-to-cloud:
  - Run a **Kaggle Notebook** (the dataset is already mounted at `/kaggle/input/...` with
    zero download) and `azcopy`/`BlobServiceClient` straight to your Azure Blob container, or
  - Spin up a cheap **Azure VM** with a large data disk in the same region as your storage,
    download there, and upload to Blob over the Azure backbone.

- **Single-file download snippet** (what script 01 does under the hood):
  ```python
  import kagglehub
  pdf_path = kagglehub.dataset_download(
      "openmarciea/openmarciea-again",
      path="prusa_manual.pdf",   # exact file name from the listing
  )
  ```
  The `path=` argument downloads exactly one file — not the whole dataset.

- **Just want to browse first?** List files without downloading anything:
  ```bash
  kaggle datasets files -v openmarciea/openmarciea-again
  ```
