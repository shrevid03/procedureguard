#!/usr/bin/env python3
"""Multimodal RAG via GitHub Models (free) - SOP text + diagram captions in one vector index."""
import base64, hashlib, json, os, time
from pathlib import Path
import fitz
import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import OpenAI

SEARCH = os.environ["SEARCH_ENDPOINT"].rstrip("/")
ADMIN_KEY = os.environ["SEARCH_ADMIN_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
BASE_URL = os.environ["GPT4O_BASE_URL"]
VECTOR_INDEX = "procedureguard-multimodal"
API = "2024-07-01"
gpt = OpenAI(api_key=GITHUB_TOKEN, base_url=BASE_URL)
SOP_DIR = Path("./data/sop_documents")
CACHE_DIR = Path("./.mm_cache"); CACHE_DIR.mkdir(exist_ok=True)

def extract_pdf(pdf_path):
    doc = fitz.open(pdf_path); text_chunks = []; images = []
    for page in doc:
        t = page.get_text().strip()
        if t: text_chunks.append(t)
        for img_meta in page.get_images(full=True):
            xref = img_meta[0]; pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha < 4: images.append(pix.tobytes("png"))
            pix = None
    doc.close(); return text_chunks, images

def cache_get(k):
    f = CACHE_DIR / f"{k}.txt"
    return f.read_text() if f.exists() else None
def cache_set(k, v): (CACHE_DIR / f"{k}.txt").write_text(v)

def verbalize_image(img_bytes):
    key = hashlib.sha1(img_bytes).hexdigest()[:16]
    c = cache_get(key)
    if c is not None: return c
    b64 = base64.b64encode(img_bytes).decode()
    resp = gpt.chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":[
        {"type":"text","text":"You are an SOP analyst. Describe this manufacturing diagram precisely: what component, tool, action, torque/spec values, and any safety symbols are shown. Be concise and factual. One paragraph."},
        {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64}"}},
    ]}], temperature=0.1, max_tokens=300)
    out = resp.choices[0].message.content.strip(); cache_set(key, out); return out

def embed(text):
    return gpt.embeddings.create(model="text-embedding-3-large", input=text).data[0].embedding

def create_index():
    h = {"Content-Type":"application/json","api-key":ADMIN_KEY}
    body = {"name":VECTOR_INDEX,"fields":[
        {"name":"id","type":"Edm.String","key":True},
        {"name":"content_text","type":"Edm.String","searchable":True},
        {"name":"content_type","type":"Edm.String","filterable":True,"facetable":True},
        {"name":"source","type":"Edm.String","filterable":True},
        {"name":"content_embedding","type":"Collection(Edm.Single)","searchable":True,"dimensions":3072,"vectorSearchProfile":"vprofile"},
    ],"vectorSearch":{"algorithms":[{"name":"hnsw-algo","kind":"hnsw"}],"profiles":[{"name":"vprofile","algorithm":"hnsw-algo"}]}}
    r = requests.put(f"{SEARCH}/indexes/{VECTOR_INDEX}?api-version={API}", headers=h, json=body)
    if r.status_code not in (200,201,204): print(f"[!] {r.status_code}\n{r.text}"); r.raise_for_status()
    print(f"[ok] index {VECTOR_INDEX} ready")

def upload(docs):
    if not docs: print("[!] nothing to upload"); return
    h = {"Content-Type":"application/json","api-key":ADMIN_KEY}
    body = {"value":[{"@search.action":"mergeOrUpload",**d} for d in docs]}
    r = requests.post(f"{SEARCH}/indexes/{VECTOR_INDEX}/docs/index?api-version={API}", headers=h, json=body)
    if r.status_code not in (200,201): print(f"[!] {r.status_code}\n{r.text}"); r.raise_for_status()
    print(f"[ok] uploaded {len(docs)} document(s)")

def query_demo(question):
    c = SearchClient(SEARCH, VECTOR_INDEX, AzureKeyCredential(ADMIN_KEY))
    vq = VectorizedQuery(vector=embed(question), k_nearest_neighbors=5, fields="content_embedding")
    res = c.search(search_text=question, vector_queries=[vq], select=["content_text","content_type","source"], top=5)
    print(f"\n=== Multimodal hybrid search: {question!r} ===")
    for i, r in enumerate(list(res), 1):
        tag = "[DIAGRAM]" if r["content_type"]=="image_caption" else "[TEXT]"
        snip = (r.get("content_text") or "").replace("\n"," ")[:240]
        print(f"\n{i}. {tag}  source={r['source']}  score={r['@search.score']:.2f}\n   {snip}")

def main():
    pdfs = sorted(SOP_DIR.glob("*.pdf"))
    if not pdfs: raise SystemExit(f"No PDFs in {SOP_DIR}")
    print(f">> Found {len(pdfs)} PDF(s)")
    create_index(); docs = []
    for pdf in pdfs:
        print(f"\n>> Processing {pdf.name}")
        text_chunks, images = extract_pdf(pdf)
        print(f"   {len(text_chunks)} text chunk(s), {len(images)} image(s)")
        for i, chunk in enumerate(text_chunks):
            print(f"   embedding text chunk {i+1}/{len(text_chunks)} ...")
            docs.append({"id":f"{pdf.stem}-text-{i}","content_text":chunk,"content_type":"text","source":pdf.name,"content_embedding":embed(chunk)})
            time.sleep(6)
        for i, img in enumerate(images):
            print(f"   verbalising image {i+1}/{len(images)} (GPT-4o vision) ...")
            cap = verbalize_image(img); print(f"      \"{cap[:90]}...\""); time.sleep(6)
            docs.append({"id":f"{pdf.stem}-img-{i}","content_text":cap,"content_type":"image_caption","source":pdf.name,"content_embedding":embed(cap)})
            time.sleep(6)
    upload(docs)
    query_demo("how is the front axle secured with nuts")

if __name__ == "__main__": main()
