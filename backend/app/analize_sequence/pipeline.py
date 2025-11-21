"""
二段階フィルタリングパイプライン

Stage1 (DINOv3) → Stage2 (VLM) を統合
"""

from typing import List, Optional, Tuple
import uuid
import weave

from .protocols import Stage1FilterProtocol
from .stage1_dummy import DummyStage1Filter
from .stage2_vlm import VLMStage2Filter
from .models import Manifest, FinalManifest


class TwoStagePipeline:
    """
    二段階フィルタリングパイプライン

    Stage1 (DINOv3) → Stage2 (VLM) を統合
    """

    def __init__(
        self,
        vision_analyzer,
        stage1_filter: Optional[Stage1FilterProtocol] = None,
        window_size: int = 5,
        overlap: int = 2
    ):
        """
        Args:
            vision_analyzer: VisionAnalyzerインスタンス
            stage1_filter: Stage1フィルター（指定しない場合はダミー）
            window_size: Stage2スライディングウィンドウサイズ
            overlap: Stage2オーバーラップ
        """
        self.vision_analyzer = vision_analyzer
        self.stage1_filter = stage1_filter or DummyStage1Filter()
        self.stage2_filter = VLMStage2Filter(
            vision_analyzer=vision_analyzer,
            window_size=window_size,
            overlap=overlap
        )

    @weave.op()
    def process(
        self,
        video_id: str,
        frame_paths: List[str],
        job_id: Optional[str] = None
    ) -> Tuple[Manifest, FinalManifest]:
        """
        二段階フィルタリング実行

        Args:
            video_id: 動画ID
            frame_paths: 全フレームのローカルパス
            job_id: ジョブID（指定しない場合は自動生成）

        Returns:
            (manifest, final_manifest)
        """
        if job_id is None:
            job_id = f"job_{uuid.uuid4().hex[:8]}"

        # Stage1: 視覚的類似度フィルタリング
        manifest = self.stage1_filter.filter_frames(
            video_id=video_id,
            frame_paths=frame_paths,
            job_id=job_id
        )

        # Stage2: VLM意味的フィルタリング
        final_manifest = self.stage2_filter.filter_frames(manifest)

        return manifest, final_manifest
