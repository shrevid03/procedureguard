#!/usr/bin/env python3
"""
02_upload_to_blob.py  — Layer 1 (input archive)

Uploads everything in ./data/sop_documents/ to the Blob container created by
00_provision_azure.sh. These blobs become the data source for the AI Search
indexer in script 03.
"""
import json
import os
from pathlib import Path

from azure.storage.blob import BlobServiceClient

CONN = os.environ["STORAGE_CONNECTION_STRING"]
CONTAINER = os.environ["STORAGE_CONTAINER"]
SOP_DIR = Path("./data/sop_documents")


def main() -> None:
    if not SOP_DIR.exists():
        raise SystemExit("Run 01_download_and_inspect.py first (no ./data/sop_documents).")

    svc = BlobServiceClient.from_connection_string(CONN)
    container = svc.get_container_client(CONTAINER)

    uploaded = []
    for f in sorted(SOP_DIR.iterdir()):
        if not f.is_file():
            continue
        blob_name = f"sop/{f.name}"
        with f.open("rb") as data:
            container.upload_blob(name=blob_name, data=data, overwrite=True)
        uploaded.append(blob_name)
        print(f"   uploaded {blob_name}")

    Path("uploaded_blobs.json").write_text(json.dumps(uploaded, indent=2))
    print(f"\n[ok] uploaded {len(uploaded)} SOP document(s) to container '{CONTAINER}'.")
    if not uploaded:
        print("[!] Nothing uploaded. Put SOP PDFs in ./data/sop_documents/ first.")


if __name__ == "__main__":
    main()
