"""Surgical-Recap Backend API"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

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


# ============================================================
# Vision Analysis Endpoints
# ============================================================

# Pydantic Models
class AnalyzeFrameRequest(BaseModel):
    """Request model for single frame analysis"""
    video_id: str
    frame_id: str


class AnalyzeSequenceRequest(BaseModel):
    """Request model for sequence analysis"""
    video_id: str
    max_frames: Optional[int] = 10


class VisionAnalysisResponse(BaseModel):
    """Response model for vision analysis"""
    step: str
    instruments: List[str]
    risk: str
    description: str
    frame_id: Optional[str] = None
    image_path: Optional[str] = None


@app.post("/api/vision/analyze-frame", response_model=VisionAnalysisResponse)
def analyze_frame(request: AnalyzeFrameRequest):
    """
    Analyze a single surgical frame

    Args:
        request: AnalyzeFrameRequest with video_id and frame_id

    Returns:
        VisionAnalysisResponse with analysis results
    """
    from .dataset import get_dataset_loader
    from .vision import get_vision_analyzer

    # Get dataset loader
    loader = get_dataset_loader()
    if not loader:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get vision analyzer
    analyzer = get_vision_analyzer()
    if not analyzer:
        raise HTTPException(status_code=500, detail="Vision analyzer not available. Check SAMBANOVA_API_KEY")

    try:
        # Load sequence to find the specific frame
        sequence = loader.load_sequence(request.video_id, load_images=False)

        # Find the frame
        frame = next((f for f in sequence if f['frame_id'] == request.frame_id), None)
        if not frame:
            raise HTTPException(status_code=404, detail=f"Frame {request.frame_id} not found in video {request.video_id}")

        # Analyze frame
        result = analyzer.analyze_frame(frame['image_path'])

        # Check for errors
        if "error" in result:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        # Add metadata
        result['frame_id'] = request.frame_id
        result['image_path'] = frame['image_path']

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vision/analyze-sequence")
def analyze_sequence(request: AnalyzeSequenceRequest):
    """
    Analyze a sequence of surgical frames

    Args:
        request: AnalyzeSequenceRequest with video_id and optional max_frames

    Returns:
        List of analysis results
    """
    from .dataset import get_dataset_loader
    from .vision import get_vision_analyzer

    # Get dataset loader
    loader = get_dataset_loader()
    if not loader:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get vision analyzer
    analyzer = get_vision_analyzer()
    if not analyzer:
        raise HTTPException(status_code=500, detail="Vision analyzer not available. Check SAMBANOVA_API_KEY")

    try:
        # Load sequence
        sequence = loader.load_sequence(request.video_id, load_images=False)

        if not sequence:
            raise HTTPException(status_code=404, detail=f"No frames found for video {request.video_id}")

        # Limit frames if specified
        frames_to_analyze = sequence[:request.max_frames]

        # Analyze each frame
        results = []
        for frame in frames_to_analyze:
            try:
                result = analyzer.analyze_frame(frame['image_path'])

                # Add metadata
                result['frame_id'] = frame['frame_id']
                result['frame_number'] = frame['frame_number']
                result['image_path'] = frame['image_path']

                results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "frame_id": frame['frame_id'],
                    "image_path": frame['image_path']
                })

        return {
            "status": "ok",
            "video_id": request.video_id,
            "total_frames_analyzed": len(results),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
