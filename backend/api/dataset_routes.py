"""
dataset_routes.py
-----------------
Endpoints for uploading and retrieving CSV datasets.
"""
from __future__ import annotations

import logging
import os
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from backend.market_data.csv_dataset_loader import load_dataset_candles, load_dataset_summary
from backend.market_data.dataset_normalizer import get_dataset_csv_path

router = APIRouter(tags=["datasets"])
DATASETS_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
os.makedirs(DATASETS_DIR, exist_ok=True)
logger = logging.getLogger(__name__)


@router.post("/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    dataset_id = str(uuid.uuid4())
    csv_path = get_dataset_csv_path(dataset_id, DATASETS_DIR)

    try:
        with csv_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

        logger.info("Dataset uploaded dataset_id=%s filename=%s", dataset_id, filename)
        return {
            "id": dataset_id,
            "dataset_id": dataset_id,
            "filename": filename,
            "status": "uploaded",
        }
    except Exception as exc:
        logger.exception("Dataset upload failed dataset_id=%s filename=%s error=%s", dataset_id, filename, exc)
        raise HTTPException(status_code=500, detail="Failed to save CSV dataset.")


@router.get("/dataset/{dataset_id}")
def get_dataset(dataset_id: str):
    try:
        return load_dataset_summary(dataset_id, DATASETS_DIR)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Dataset summary failed dataset_id=%s error=%s", dataset_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dataset/{dataset_id}/candles")
def get_dataset_candles(
    dataset_id: str,
    timeframe: Optional[str] = Query("1m"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
):
    try:
        return load_dataset_candles(
            dataset_id,
            DATASETS_DIR,
            timeframe=timeframe or "1m",
            start=start,
            end=end,
            limit=limit,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Dataset candle load failed dataset_id=%s error=%s", dataset_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dataset/{dataset_id}/{timeframe}")
def get_dataset_timeframe(dataset_id: str, timeframe: str):
    try:
        return load_dataset_candles(dataset_id, DATASETS_DIR, timeframe=timeframe)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Dataset timeframe load failed dataset_id=%s timeframe=%s error=%s", dataset_id, timeframe, exc)
        raise HTTPException(status_code=500, detail=str(exc))
