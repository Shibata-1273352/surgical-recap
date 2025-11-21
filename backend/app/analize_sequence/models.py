"""
Pydanticモデル定義

二段階フィルタリングのリクエスト/レスポンス、Manifestデータ構造
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FrameMetadata(BaseModel):
    """フレームのメタデータ"""
    frame_number: int
    timestamp: float
    file_path: str  # ローカルファイルパス


class Manifest(BaseModel):
    """Stage1出力: DINOv3フィルタリング結果"""
    job_id: str
    video_id: str
    total_frames: int
    keep_indices: List[int]  # Stage1で選択されたフレームのインデックス
    frames: List[FrameMetadata]


class SelectedFrame(BaseModel):
    """Stage2で選択されたフレーム"""
    file_path: str  # ローカルファイルパス
    timestamp: float  # タイムスタンプ（秒）


class FinalManifest(BaseModel):
    """Stage2出力: VLM意味的フィルタリング結果"""
    job_id: str
    video_id: str
    stage1_frame_count: int
    selected_frame_count: int
    selected_frames: List[SelectedFrame]


class TwoStageFilterRequest(BaseModel):
    """二段階フィルタリングのリクエスト"""
    video_id: str
    max_frames: Optional[int] = None
    window_size: int = Field(default=5, ge=3, le=10)
    overlap: int = Field(default=2, ge=1, le=4)
    job_id: Optional[str] = None  # 指定しない場合は自動生成


class TwoStageFilterResponse(BaseModel):
    """二段階フィルタリングのレスポンス"""
    status: str
    job_id: str
    video_id: str
    manifest: Manifest
    final_manifest: FinalManifest
    analysis_results: Optional[List[Dict[str, Any]]] = None  # 各フレームの解析結果
