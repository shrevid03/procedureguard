#!/usr/bin/env python3
"""
01_download_and_inspect.py  — Layer 1 (input)  [SELECTIVE / LOW-DISK VERSION]

The openmarciea-again dataset is ~139 GB, almost all of it assembly MP4 video.
Multimodal RAG only needs the SOP DOCUMENT (the PDF) — a few MB. So we:

  1. LIST every file in the dataset  (no download — just metadata)
  2. Identify the SOP documents (PDF / docx / images)
  3. Download ONLY those, one file at a time, via kagglehub's single-file `path=`

The 139 GB of video is NEVER downloaded to your laptop. If you later need the
videos for the Content Understanding pipeline, move them cloud-to-cloud
(see README -> "Handling the 139 GB of video").
"""
import json
import shutil
from pathlib import Path

import kagglehub
from kaggle.api.kaggle_api_extended import KaggleApi

DATASET = "openmarciea/openmarciea-again"
SOP_EXTS = (".pdf", ".docx", ".doc", ".txt", ".md")
IMG_EXTS = (".png", ".jpg", ".jpeg", ".tiff")
VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm")

SOP_DIR = Path("./data/sop_documents")


def main() -> None:
    SOP_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1. List files WITHOUT downloading -----------------------------------
    api = KaggleApi()
    api.authenticate()  # uses ~/.kaggle/kaggle.json
    listing = api.dataset_list_files(DATASET).files
    print(f">> Dataset has {len(listing)} files. Categorising (no download yet)...\n")

    sop_names, image_names, video_names, other_names = [], [], [], []
    total_video_bytes = 0
    for f in listing:
        name = str(f.name)
        lower = name.lower()
        size = getattr(f, "size", None) or getattr(f, "totalBytes", 0) or 0
        if lower.endswith(SOP_EXTS):
            sop_names.append(name)
        elif lower.endswith(IMG_EXTS):
            image_names.append(name)
        elif lower.endswith(VIDEO_EXTS):
            video_names.append(name)
            try:
                total_video_bytes += int(size)
            except (TypeError, ValueError):
                pass
        else:
            other_names.append(name)

    print(f"   SOP documents (PDF/doc): {len(sop_names)}")
    for n in sop_names:
        print(f"       {n}")
    print(f"   Loose images: {len(image_names)}")
    print(f"   Videos (NOT downloading): {len(video_names)}"
          f"  (~{total_video_bytes / 1e9:.1f} GB)")
    if other_names:
        print(f"   Other: {len(other_names)}")

    # --- 2. Download ONLY the SOP documents (+ a few sample images) ----------
    to_pull = list(sop_names)
    # If there's no PDF, grab up to 30 loose images so you still have SOP visuals.
    if not sop_names and image_names:
        print("\n[!] No PDF found. Pulling up to 30 loose images as SOP visuals instead.")
        to_pull = image_names[:30]

    downloaded = []
    for name in to_pull:
        print(f"\n>> downloading single file: {name}")
        # kagglehub `path=` downloads exactly one file and returns its local path
        local = kagglehub.dataset_download(DATASET, path=name)
        dst = SOP_DIR / Path(name).name
        shutil.copy2(local, dst)
        downloaded.append(str(dst))
        print(f"   -> {dst}")

    manifest = {
        "dataset": DATASET,
        "downloaded_sop_files": downloaded,
        "video_files_skipped": video_names,
        "video_bytes_skipped": total_video_bytes,
    }
    Path("dataset_manifest.json").write_text(json.dumps(manifest, indent=2))

    print("\n================ SUMMARY ================")
    print(f"Downloaded {len(downloaded)} SOP file(s) to {SOP_DIR}/  (a few MB)")
    print(f"Skipped {len(video_names)} videos (~{total_video_bytes / 1e9:.1f} GB) — "
          "not needed for Multimodal RAG.")
    if not downloaded:
        print("\n[!] Nothing to index. If the dataset truly has no SOP document, drop the "
              "Prusa assembly manual PDF into ./data/sop_documents/ manually.")
    print("\nNext: python 02_upload_to_blob.py")


if __name__ == "__main__":
    main()
