"""
Stage1フィルター実装

DINOv3を使用してフレームをフィルタリング
1. 全フレームの特徴量を抽出
2. 隣接フレーム間のコサイン類似度を計算
3. 類似度閾値でグルーピング
4. 各グループからキーフレームをサンプリング
"""

from typing import List
from pathlib import Path
import weave

from .models import Manifest, FrameMetadata
from .protocols import Stage1FilterProtocol
from .dino_v3 import (
    extract_features_batch,
    compute_adjacent_similarities,
    group_by_similarity,
    sample_keyframes_from_groups,
)


class DINOv3Stage1Filter:
    """
    DINOv3を使用したStage1フィルター

    1. 全フレームの特徴量を抽出
    2. 隣接フレーム間のコサイン類似度を計算
    3. 類似度閾値でグルーピング
    4. 各グループからキーフレームをサンプリング
    """

    def __init__(self, fps: float = 1.0):
        """
        Args:
            fps: 動画のフレームレート（cholecSeg8kは1fps想定）
        """
        self.fps = fps

    @weave.op()
    def filter_frames(
        self,
        video_id: str,
        frame_paths: List[str],
        job_id: str,
        similarity_threshold: float = 0.98,
        sample_interval_sec: int = 10
    ) -> Manifest:
        """
        DINOv3特徴量に基づいてフレームをフィルタリング

        Args:
            video_id: 動画ID
            frame_paths: フレーム画像のローカルパス
            job_id: ジョブID
            similarity_threshold: 類似度閾値（0.98推奨）
            sample_interval_sec: グループ内サンプリング間隔（秒）

        Returns:
            Manifest: 選択されたフレームのメタデータ
        """
        # 1. 全フレームの特徴量を抽出
        features = extract_features_batch(frame_paths)

        # 2. 隣接フレーム間のコサイン類似度を計算
        similarities = compute_adjacent_similarities(features)

        # 3. 類似度閾値でグルーピング
        groups = group_by_similarity(similarities, threshold=similarity_threshold)

        # 4. 各グループからキーフレームをサンプリング
        sample_interval_frames = int(sample_interval_sec * self.fps)
        keep_indices = sample_keyframes_from_groups(
            groups=groups,
            total_frames=len(frame_paths),
            sample_interval=sample_interval_frames
        )

        # フレームメタデータ作成
        frames = []
        for idx in keep_indices:
            file_path = frame_paths[idx]
            frames.append(FrameMetadata(
                frame_number=idx,
                timestamp=idx / self.fps,
                file_path=file_path
            ))

        return Manifest(
            job_id=job_id,
            video_id=video_id,
            total_frames=len(frame_paths),
            keep_indices=keep_indices,
            frames=frames
        )


# Protocolチェック（型エラーがないか確認）
def _check_protocol_compliance() -> Stage1FilterProtocol:
    """型チェック用（実行不要）"""
    filter: Stage1FilterProtocol = DINOv3Stage1Filter()
    return filter
