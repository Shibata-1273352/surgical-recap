"""
Stage1フィルター実装

DINOv3を使用してフレームをフィルタリング
1. 全フレームの特徴量を抽出
2. 隣接フレーム間のコサイン類似度を計算
3. 類似度閾値でグルーピング
4. 各グループからキーフレームをサンプリング
"""

from typing import List, Tuple
import numpy as np
import torch
import weave

from .models import Manifest, FrameMetadata
from .protocols import Stage1FilterProtocol
from .dino_v3 import SurgicalDinoExtractor


def compute_adjacent_similarities(features: torch.Tensor) -> np.ndarray:
    """
    隣接フレーム間のコサイン類似度を計算

    Args:
        features: 特徴量行列 [N, D]

    Returns:
        similarities: 隣接フレーム間の類似度 [N-1]
    """
    # 正規化
    features_norm = features / features.norm(dim=-1, keepdim=True)

    # 隣接フレーム間のコサイン類似度
    similarities = torch.cosine_similarity(
        features_norm[:-1],
        features_norm[1:],
        dim=-1
    )

    return similarities.cpu().numpy()


def group_by_similarity(
    similarities: np.ndarray,
    threshold: float = 0.98
) -> List[Tuple[int, int]]:
    """
    類似度閾値でフレームをグルーピング

    連続して類似度が高い（threshold以上）フレームを同一グループとする

    Args:
        similarities: 隣接フレーム間の類似度 [N-1]
        threshold: 類似度閾値

    Returns:
        groups: (start_idx, end_idx) のリスト
    """
    groups = []
    start_idx = 0

    for i, sim in enumerate(similarities):
        if sim < threshold:
            # シーン変化検出 → グループ終了
            groups.append((start_idx, i))
            start_idx = i + 1

    # 最後のグループを追加
    groups.append((start_idx, len(similarities)))

    return groups


def sample_keyframes_from_groups(
    groups: List[Tuple[int, int]],
    total_frames: int,
    sample_interval: int = 10
) -> List[int]:
    """
    各グループからキーフレームをサンプリング

    Args:
        groups: (start_idx, end_idx) のリスト
        total_frames: 総フレーム数
        sample_interval: グループ内サンプリング間隔（フレーム数）

    Returns:
        keep_indices: 保持するフレームのインデックス
    """
    keep_indices = []

    for start_idx, end_idx in groups:
        group_length = end_idx - start_idx + 1

        if group_length <= sample_interval:
            # 短いグループは中央のフレームを選択
            mid = (start_idx + end_idx) // 2
            keep_indices.append(mid)
        else:
            # 長いグループは等間隔でサンプリング
            for i in range(start_idx, end_idx + 1, sample_interval):
                if i < total_frames:
                    keep_indices.append(i)

    # 重複削除してソート
    keep_indices = sorted(set(keep_indices))

    return keep_indices


class DINOv3Stage1Filter:
    """
    DINOv3を使用したStage1フィルター

    1. 全フレームの特徴量を抽出
    2. 隣接フレーム間のコサイン類似度を計算
    3. 類似度閾値でグルーピング
    4. 各グループからキーフレームをサンプリング
    """

    def __init__(
        self,
        fps: float = 1.0,
        batch_size: int = 32
    ):
        """
        Args:
            fps: 動画のフレームレート（cholecSeg8kは1fps想定）
            batch_size: 特徴量抽出時のバッチサイズ
        """
        self.fps = fps
        self.batch_size = batch_size
        self.extractor = SurgicalDinoExtractor()

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
        features = self.extractor.extract_features_batch(
            images=frame_paths,
            normalize=True,
            batch_size=self.batch_size
        )

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
    filter_instance: Stage1FilterProtocol = DINOv3Stage1Filter()
    return filter_instance
