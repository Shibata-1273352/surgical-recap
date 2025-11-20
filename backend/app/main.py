"""Surgical-Recap Backend API"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(
    title="Surgical-Recap API",
    description="AI搭載型の手術動画即時分析・教育プラットフォーム",
    version="0.1.0"
)

# CORS設定（Next.jsフロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """ルートエンドポイント"""
    return {
        "status": "ok",
        "service": "Surgical-Recap API",
        "version": "0.1.0",
        "components": {
            "vision": "SambaNova (Llama 3.2 90B Vision)",
            "text": "vLLM (Llama 3.1 70B)",
            "evaluation": "W&B Weave + Azure OpenAI"
        }
    }


@app.get("/health")
def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "dataset_path": os.getenv("DATASET_PATH", "backend/data/cholecseg8k")
    }


@app.get("/api/dataset/info")
def dataset_info():
    """データセット情報"""
    from .dataset import get_dataset_loader
    from fastapi import HTTPException

    loader = get_dataset_loader()

    if not loader:
        return {
            "status": "not_found",
            "message": "Dataset not found. Please run: cd backend && uv run python scripts/download_dataset.py"
        }

    try:
        videos = loader.get_all_videos()
        total_frames = loader.get_frame_count()

        # 各ビデオのフレーム数を取得
        video_details = []
        for video_id in videos:
            frame_count = loader.get_frame_count(video_id)
            video_details.append({
                "video_id": video_id,
                "frame_count": frame_count
            })

        return {
            "status": "ok",
            "dataset": "cholecSeg8k",
            "total_videos": len(videos),
            "videos": video_details,
            "total_frames": total_frames
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
