"""
Chat機能のデータモデル定義

Pydanticモデルでリクエスト/レスポンスのバリデーションを実施
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class Message(BaseModel):
    """チャットメッセージ"""
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="メッセージ内容")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="送信日時")


class ChatRequest(BaseModel):
    """チャットメッセージ送信リクエスト"""
    session_id: str = Field(..., description="セッションID（動画解析結果のID）")
    message: str = Field(..., min_length=1, max_length=2000, description="ユーザーの質問")
    history: List[Message] = Field(default=[], description="会話履歴（最大10往復）")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "video01_20250121_1230",
                "message": "この手術でクリッピングはどの段階で行われましたか？",
                "history": [
                    {
                        "role": "user",
                        "content": "この手術の概要を教えて"
                    },
                    {
                        "role": "assistant",
                        "content": "この手術は腹腔鏡下胆嚢摘出術で..."
                    }
                ]
            }
        }


class ChatResponse(BaseModel):
    """チャット応答"""
    reply: str = Field(..., description="AIアシスタントの回答")
    referenced_frames: List[int] = Field(default=[], description="参照したフレーム番号のリスト")
    metadata: Dict[str, Any] = Field(default={}, description="メタデータ（モデル名、トークン数など）")

    class Config:
        json_schema_extra = {
            "example": {
                "reply": "クリッピングはフレーム8と9で行われました。具体的には...",
                "referenced_frames": [8, 9],
                "metadata": {
                    "model": "Meta-Llama-3.1-70B-Instruct",
                    "tokens": 150,
                    "response_time_ms": 450
                }
            }
        }


class SessionSummary(BaseModel):
    """セッション概要"""
    session_id: str = Field(..., description="セッションID")
    video_id: str = Field(..., description="動画ID")
    analyzed_at: datetime = Field(..., description="解析日時")
    frame_count: int = Field(..., description="解析済みフレーム数")
    summary: str = Field(..., description="セッション概要")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "video01_20250121_1230",
                "video_id": "video01",
                "analyzed_at": "2025-01-21T12:30:00Z",
                "frame_count": 15,
                "summary": "胆嚢摘出術 - 15フレーム解析済み"
            }
        }


class SessionListResponse(BaseModel):
    """セッション一覧レスポンス"""
    status: str = Field(default="ok", description="ステータス")
    sessions: List[SessionSummary] = Field(..., description="セッション一覧")
    total: int = Field(..., description="総セッション数")


class AnalysisResult(BaseModel):
    """フレーム解析結果"""
    frame_number: int
    step: str
    instruments: List[str]
    risk: str
    description: str


class SessionDetailResponse(BaseModel):
    """セッション詳細レスポンス"""
    status: str = Field(default="ok", description="ステータス")
    session_id: str = Field(..., description="セッションID")
    video_id: str = Field(..., description="動画ID")
    analysis_results: List[AnalysisResult] = Field(..., description="解析結果の詳細")
    created_at: datetime = Field(..., description="セッション作成日時")
    frame_count: int = Field(..., description="フレーム数")


class DeleteResponse(BaseModel):
    """削除レスポンス"""
    status: str = Field(default="ok", description="ステータス")
    message: str = Field(..., description="メッセージ")


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    status: str = Field(default="error", description="ステータス")
    error: str = Field(..., description="エラーメッセージ")
    detail: Optional[str] = Field(None, description="詳細情報")
