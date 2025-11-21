"""
Stage1フィルター（DINOv3）のインターフェース定義

Protocolを使用することで、後でDINOv3実装に差し替え可能
"""

from typing import Protocol, List
from .models import Manifest


class Stage1FilterProtocol(Protocol):
    """
    Stage1フィルター（DINOv3）のインターフェース定義

    後でDINOv3実装に差し替え可能
    """

    def filter_frames(
        self,
        video_id: str,
        frame_paths: List[str],
        job_id: str,
        similarity_threshold: float = 0.98,
        sample_interval_sec: int = 10
    ) -> Manifest:
        """
        フレームを視覚的類似度でフィルタリング

        Args:
            video_id: 動画ID
            frame_paths: フレーム画像のローカルパス
            job_id: ジョブID
            similarity_threshold: 類似度閾値 (0.98推奨)
            sample_interval_sec: グループ内サンプリング間隔（秒）

        Returns:
            Manifest: 選択されたフレームのメタデータ
        """
        ...
