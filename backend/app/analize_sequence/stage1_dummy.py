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
        ダミー実装: 10秒間隔でフレームをサンプリング

        Args:
            video_id: 動画ID
            frame_paths: フレーム画像のローカルパス
            job_id: ジョブID
            similarity_threshold: 類似度閾値（使用しない）
            sample_interval_sec: サンプリング間隔（秒）

        Returns:
            Manifest: 選択されたフレームのメタデータ
        """
        # 10秒間隔のフレーム数
        frame_interval = int(sample_interval_sec * self.fps)

        # 均等サンプリング
        keep_indices = list(range(0, len(frame_paths), frame_interval))

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
