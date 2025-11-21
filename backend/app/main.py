"""Surgical-Recap Backend API"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
from pathlib import Path
from dotenv import load_dotenv
import shutil
import json
import uuid
from datetime import datetime


# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

app = FastAPI(
    title="Surgical-Recap API",
    description="AI搭載型の手術動画即時分析・教育プラットフォーム",
    version="0.1.0"
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
VIDEO_DIR = STATIC_DIR / "videos"

# Serve /static/* so the video URLs work
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

VIDEO_DIR.mkdir(parents=True, exist_ok=True)

COMMENTS_DIR = BASE_DIR / "comments"
COMMENTS_DIR.mkdir(parents=True, exist_ok=True)

CHATS_DIR = BASE_DIR / "chats"
CHATS_DIR.mkdir(parents=True, exist_ok=True)



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
    二段階フィルタリングでフレームを解析

    Stage1: DINOv3視覚的類似度（現在はダミー）
    Stage2: VLM意味的選択

    Args:
        request: AnalyzeSequenceRequest with video_id and optional max_frames

    Returns:
        TwoStageFilterResponse with manifest, final_manifest, and analysis results
    """
    from .dataset import get_dataset_loader
    from .vision import get_vision_analyzer
    from .analize_sequence.pipeline import TwoStagePipeline
    from .analize_sequence.models import TwoStageFilterResponse
    from .vision import SURGICAL_VISION_SYSTEM_PROMPT, SURGICAL_VISION_USER_PROMPT

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
        if request.max_frames:
            sequence = sequence[:request.max_frames]

        # フレームパス抽出
        frame_paths = [frame['image_path'] for frame in sequence]

        # 二段階フィルタリングパイプライン
        pipeline = TwoStagePipeline(
            vision_analyzer=analyzer,
            window_size=5,
            overlap=2
        )

        job_id = f"job_{uuid.uuid4().hex[:8]}"
        manifest, final_manifest = pipeline.process(
            video_id=request.video_id,
            frame_paths=frame_paths,
            job_id=job_id
        )

        # 選択されたフレームのみ解析
        analysis_results = []
        for selected_frame in final_manifest.selected_frames:
            try:
                result = analyzer.analyze_frame(
                    image_path=selected_frame.file_path,
                    system_prompt=SURGICAL_VISION_SYSTEM_PROMPT,
                    user_prompt=SURGICAL_VISION_USER_PROMPT
                )
                result['file_path'] = selected_frame.file_path
                result['timestamp'] = selected_frame.timestamp
                analysis_results.append(result)
            except Exception as e:
                analysis_results.append({
                    "error": str(e),
                    "file_path": selected_frame.file_path,
                    "timestamp": selected_frame.timestamp
                })

        return TwoStageFilterResponse(
            status="ok",
            job_id=job_id,
            video_id=request.video_id,
            manifest=manifest,
            final_manifest=final_manifest,
            analysis_results=analysis_results
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

###########################################################
##################### chat endpoint #######################
###########################################################

class ChatRequest(BaseModel):
    message: str
    video_title: str | None = None
    timestamp: float | None = None


class ChatResponse(BaseModel):
    reply: str


class ChatMessageRequest(BaseModel):
    message: str
    timestamp: float | None = None


class ChatCreateResponse(BaseModel):
    id: str
    created_at: str
    title: str


class ChatListItem(BaseModel):
    id: str
    title: str
    created_at: str
    num_messages: int


class ChatHistoryResponse(BaseModel):
    id: str
    messages: list


def _chats_file(video_name: str) -> Path:
    return CHATS_DIR / f"{video_name}.json"


def _load_chats(video_name: str) -> dict:
    path = _chats_file(video_name)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def _save_chats(video_name: str, chats: dict):
    path = _chats_file(video_name)
    with path.open("w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=2)


@app.get("/api/videos/{video_name}/chats")
def list_chats(video_name: str):
    chats = _load_chats(video_name)
    items = []

    for chat_id, chat in chats.items():
        msgs = chat.get("messages", [])
    
        # Make a good title
        first_user = next((m for m in msgs if m["role"] == "user"), None)
        #title = first_user["text"][:30] + "…" if first_user else "New chat"

        items.append({
            "id": chat_id,
            "title": chat.get("title"),
            "created_at": chat["created_at"],
            "num_messages": len(msgs),
        })

    
    # newest first
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return {"chats": items}


@app.post("/api/videos/{video_name}/chats", response_model=ChatCreateResponse)
def create_chat(video_name: str):
    chats = _load_chats(video_name)
    chat_id = str(uuid.uuid4())
    chat_title = f"Chat {len(chats) + 1}"
    now = datetime.utcnow().isoformat() + "Z"

    chats[chat_id] = {
        "id": chat_id,
        "created_at": now,
        "messages": [],
        "title": chat_title
    }

    _save_chats(video_name, chats)

    return ChatCreateResponse(id=chat_id, created_at=now, title=chat_title)


@app.get("/api/videos/{video_name}/chats/{chat_id}", response_model=ChatHistoryResponse)
def get_chat(video_name: str, chat_id: str):
    chats = _load_chats(video_name)
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")

    return {
        "id": chat_id,
        "messages": chats[chat_id]["messages"]
    }


@app.post("/api/videos/{video_name}/chats/{chat_id}/message")
def send_chat_message(video_name: str, chat_id: str, req: ChatMessageRequest):
    chats = _load_chats(video_name)
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")

    chat = chats[chat_id]
    messages = chat["messages"]

    # Store user message
    user_msg = {
        "role": "user",
        "text": req.message,
        "timestamp": req.timestamp or 0
    }
    messages.append(user_msg)

    # Build LLM context 
    llm_input = [
        {
            "role": "system",
            "content": f"You are a surgical video assistant. Video: {video_name}"
        }
    ]

    for m in messages:
        llm_input.append({
            "role": m["role"],
            "content": f"[t={m['timestamp']}s] {m['text']}"
        })

    # ⚠️ Replace with your real LLM call:
    reply_text = f"Llama response placeholder"

    # Store assistant reply
    assistant_msg = {
        "role": "assistant",
        "text": reply_text,
        "timestamp": req.timestamp or 0
    }
    messages.append(assistant_msg)

    # Save back to JSON
    _save_chats(video_name, chats)

    return {
        "reply": reply_text,
        "messages": messages,
        "chat_meta": {
            "id": chat_id,
            "created_at": chat["created_at"],
            "num_messages": len(messages)
        }
    }


###########################################################
########### video serve and upload endpoints ##############
###########################################################


@app.get("/api/videos")
def get_videos():
    """Return list of available video files from static/videos."""
    if not VIDEO_DIR.exists():
        raise HTTPException(status_code=500, detail="Video directory not found")

    videos = []
    for f in VIDEO_DIR.iterdir():
        if f.suffix.lower() in [".mp4", ".mov", ".webm", ".m4v"]:
            videos.append({
                "title": f.name,
                "description": f"Video file: {f.name}",
                "url": f"/static/videos/{f.name}",
            })

    return videos

@app.post("/api/videos/uploadLocal")
async def upload_video_local(file: UploadFile = File(...)):
    """Upload a video file and save it into static/videos."""
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".mp4", ".mov", ".webm", ".m4v"]:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    # Destination path
    dest_path = VIDEO_DIR / file.filename

    try:
        # Stream file to disk
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return {
        "status": "ok",
        "filename": file.filename,
        "url": f"/static/videos/{file.filename}",
        "message": "Video uploaded successfully",
    }

@app.delete("/api/videos/{video_name}")
def delete_video(video_name: str):
    """
    Delete a video file and its associated comments.
    video_name is the filename (e.g. 'sample1.mp4').
    """
    # Basic safety: avoid directory traversal
    if "/" in video_name or "\\" in video_name:
        raise HTTPException(status_code=400, detail="Invalid video name")

    video_path = VIDEO_DIR / video_name
    comments_path = _comments_file(video_name)

    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        # Delete video file
        video_path.unlink()

        # Delete comments file if exists
        if comments_path.exists():
          comments_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {e}")

    return {
        "status": "ok",
        "message": f"Deleted video {video_name}",
    }

###########################################################
#################### comment endpoints ####################
###########################################################


class Comment(BaseModel):
    timestamp: float
    text: str
    parent_id: Optional[int] = None
    likes: int = 0


class CommentUpdate(BaseModel):
    text: str


def _comments_file(video_name: str) -> Path:
    return COMMENTS_DIR / f"{video_name}.json"


def _load_comments(video_name: str) -> List[dict]:
    path = _comments_file(video_name)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            comments = json.load(f)
    except Exception:
        return []

    changed = False

    # Ensure id + likes fields exist
    max_id = 0
    for c in comments:
        if "id" in c and isinstance(c["id"], int):
            max_id = max(max_id, c["id"])
        else:
            changed = True

        if "likes" not in c:   # << new
            c["likes"] = 0
            changed = True

    if changed:
        _save_comments(video_name, comments)

    return comments


def _save_comments(video_name: str, comments: List[dict]) -> None:
    path = _comments_file(video_name)
    with path.open("w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)


@app.get("/api/videos/{video_name}/comments")
def get_video_comments(video_name: str):
    """Get comments for a given video (by filename)."""
    comments = _load_comments(video_name)
    return {"comments": comments}


@app.post("/api/videos/{video_name}/comments")
def add_video_comment(video_name: str, comment: Comment):
    """Add a comment or reply for a given video."""
    video_path = VIDEO_DIR / video_name
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    comments = _load_comments(video_name)

    # Determine new id
    max_id = max((c.get("id", 0) for c in comments), default=0)
    new_id = max_id + 1

    comment_dict = {
        "id": new_id,
        "timestamp": comment.timestamp,
        "text": comment.text,
        "parent_id": comment.parent_id,
    }
    comments.append(comment_dict)
    _save_comments(video_name, comments)

    return {"status": "ok", "comment": comment_dict}


@app.put("/api/videos/{video_name}/comments/{comment_id}")
def update_video_comment(video_name: str, comment_id: int, update: CommentUpdate):
    """Edit a comment's text."""
    comments = _load_comments(video_name)
    for c in comments:
        if c.get("id") == comment_id:
            c["text"] = update.text
            _save_comments(video_name, comments)
            return {"status": "ok", "comment": c}

    raise HTTPException(status_code=404, detail="Comment not found")


@app.delete("/api/videos/{video_name}/comments/{comment_id}")
def delete_video_comment(video_name: str, comment_id: int):
    """Delete a comment and its replies (cascade)."""
    comments = _load_comments(video_name)
    if not comments:
        raise HTTPException(status_code=404, detail="No comments for this video")

    # Cascade: delete comment + all descendants
    to_delete = {comment_id}
    changed = True
    while changed:
        changed = False
        for c in comments:
            pid = c.get("parent_id")
            cid = c.get("id")
            if pid in to_delete and cid not in to_delete:
                to_delete.add(cid)
                changed = True

    new_comments = [c for c in comments if c.get("id") not in to_delete]

    if len(new_comments) == len(comments):
        raise HTTPException(status_code=404, detail="Comment not found")

    _save_comments(video_name, new_comments)
    return {"status": "ok", "deleted_ids": list(to_delete)}


@app.post("/api/videos/{video_name}/comments/{comment_id}/like")
def like_comment(video_name: str, comment_id: int):
    """Increment the like counter for a comment."""
    comments = _load_comments(video_name)

    for c in comments:
        if c.get("id") == comment_id:
            c["likes"] = c.get("likes", 0) + 1
            _save_comments(video_name, comments)
            return {"status": "ok", "likes": c["likes"]}

    raise HTTPException(status_code=404, detail="Comment not found")


@app.post("/api/videos/{video_name}/comments/{comment_id}/unlike")
def unlike_comment(video_name: str, comment_id: int):
    """Decrement the like counter (not below 0)."""
    comments = _load_comments(video_name)

    for c in comments:
        if c.get("id") == comment_id:
            c["likes"] = max(0, c.get("likes", 0) - 1)
            _save_comments(video_name, comments)
            return {"status": "ok", "likes": c["likes"]}

    raise HTTPException(status_code=404, detail="Comment not found")


@app.post("/api/video/upload")
async def upload_video(video: UploadFile = File(...)):
    """
    動画をアップロードして解析

    1. フレーム抽出
    2. 二段階フィルタリング（Stage1 + Stage2）
    3. 選択フレームのVision解析

    Returns:
        TwoStageFilterResponse with manifest, final_manifest, and analysis results
    """
    import cv2
    from .vision import get_vision_analyzer
    from .analize_sequence.pipeline import TwoStagePipeline

    # Get vision analyzer
    analyzer = get_vision_analyzer()
    if not analyzer:
        raise HTTPException(status_code=500, detail="Vision analyzer not available. Check SAMBANOVA_API_KEY")

    # 一時ディレクトリ作成
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())

    # 動画ファイルを保存
    video_path = temp_dir / video.filename
    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)

    # フレーム抽出
    frames_dir = temp_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_paths = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_path = frames_dir / f"frame_{frame_idx:06d}.jpg"
        cv2.imwrite(str(frame_path), frame)
        frame_paths.append(str(frame_path))
        frame_idx += 1

    cap.release()

    if not frame_paths:
        raise HTTPException(status_code=400, detail="No frames extracted from video")

    try:
        # 二段階フィルタリングパイプライン
        pipeline = TwoStagePipeline(
            vision_analyzer=analyzer,
            window_size=5,
            overlap=2
        )

        manifest, final_manifest = pipeline.process(
            video_id=video.filename,
            frame_paths=frame_paths
        )

        # フレーム解析パイプライン
        from .frame_analysis import FrameAnalysisPipeline
        frame_analysis_pipeline = FrameAnalysisPipeline(vision_analyzer=analyzer)
        analysis_results = frame_analysis_pipeline.analyze(final_manifest)

        return {
            "status": "ok",
            "video_id": video.filename,
            "total_frames": len(frame_paths),
            "selected_frames": len(final_manifest.selected_frames),
            "analysis_results": analysis_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
