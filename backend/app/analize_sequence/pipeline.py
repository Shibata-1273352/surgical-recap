"""
二段階フィルタリングパイプライン

Stage1 (DINOv3) → Stage2 (VLM) を統合
"""

from typing import List, Optional, Tuple
from pathlib import Path
import uuid
import json
import weave

from .protocols import Stage1FilterProtocol
from .stage1_dino import DINOv3Stage1Filter
from .stage2_vlm import VLMStage2Filter
from .models import Manifest, FinalManifest
from .config import STAGE2_WINDOW_SIZE, STAGE2_OVERLAP


class TwoStagePipeline:
    """
    二段階フィルタリングパイプライン

    Stage1 (DINOv3) → Stage2 (VLM) を統合
    """

    def __init__(
        self,
        vision_analyzer,
        stage1_filter: Optional[Stage1FilterProtocol] = None,
        window_size: int = STAGE2_WINDOW_SIZE,
        overlap: int = STAGE2_OVERLAP,
        jobs_dir: Optional[str] = None
    ):
        """
        Args:
            vision_analyzer: VisionAnalyzerインスタンス
            stage1_filter: Stage1フィルター（指定しない場合はDINOv3Stage1Filter）
            window_size: Stage2スライディングウィンドウサイズ（デフォルト: config.STAGE2_WINDOW_SIZE）
            overlap: Stage2オーバーラップ（デフォルト: config.STAGE2_OVERLAP）
            jobs_dir: ジョブ出力ディレクトリ（指定しない場合は backend/jobs）
        """
        self.vision_analyzer = vision_analyzer
        self.stage1_filter = stage1_filter or DINOv3Stage1Filter()
        self.stage2_filter = VLMStage2Filter(
            vision_analyzer=vision_analyzer,
            window_size=window_size,
            overlap=overlap
        )
        # デフォルトは backend/jobs
        self.jobs_dir = Path(jobs_dir) if jobs_dir else Path(__file__).parent.parent.parent / "jobs"

    def _save_manifest(self, job_id: str, filename: str, data: dict) -> Path:
        """
        マニフェストをJSONファイルとして保存

        Args:
            job_id: ジョブID
            filename: ファイル名 (manifest.json or final_manifest.json)
            data: 保存するデータ

        Returns:
            保存先パス
        """
        output_dir = self.jobs_dir / job_id / "keyframes"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path

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

        # manifest.json を保存
        manifest_path = self._save_manifest(
            job_id=job_id,
            filename="manifest.json",
            data=manifest.model_dump()
        )
        print(f"Saved manifest: {manifest_path}")

        # Stage2: VLM意味的フィルタリング
        final_manifest = self.stage2_filter.filter_frames(manifest)

        # final_manifest.json を保存
        final_manifest_path = self._save_manifest(
            job_id=job_id,
            filename="final_manifest.json",
            data=final_manifest.model_dump()
        )
        print(f"Saved final_manifest: {final_manifest_path}")

        return manifest, final_manifest
