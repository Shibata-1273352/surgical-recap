"""
DINOv3のダミー実装

10秒間隔で均等にフレームをサンプリング
後でDINOv3実装に差し替え
"""

from typing import List
from pathlib import Path
import weave

from .models import Manifest, FrameMetadata
from .protocols import Stage1FilterProtocol


class DummyStage1Filter:
    """
    DINOv3のダミー実装

    10秒間隔で均等にフレームをサンプリング
    後でDINOv3実装に差し替え
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
        ダミー実装: 全フレームを通過させる

        Args:
            video_id: 動画ID
            frame_paths: フレーム画像のローカルパス
            job_id: ジョブID
            similarity_threshold: 類似度閾値（使用しない）
            sample_interval_sec: サンプリング間隔（使用しない）

        Returns:
            Manifest: 選択されたフレームのメタデータ
        """
        # ダミー実装: 全フレームを通過
        keep_indices = list(range(len(frame_paths)))

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
    dummy: Stage1FilterProtocol = DummyStage1Filter()
    return dummy
