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
        output_dir: Optional[str] = None
    ):
        """
        Args:
            vision_analyzer: VisionAnalyzerインスタンス
            stage1_filter: Stage1フィルター（指定しない場合はDINOv3Stage1Filter）
            window_size: Stage2スライディングウィンドウサイズ（デフォルト: config.STAGE2_WINDOW_SIZE）
            overlap: Stage2オーバーラップ（デフォルト: config.STAGE2_OVERLAP）
            output_dir: 出力ディレクトリ（指定しない場合はmanifest保存をスキップ）
        """
        self.vision_analyzer = vision_analyzer
        self.stage1_filter = stage1_filter or DINOv3Stage1Filter()
        self.stage2_filter = VLMStage2Filter(
            vision_analyzer=vision_analyzer,
            window_size=window_size,
            overlap=overlap
        )
        self.output_dir = Path(output_dir) if output_dir else None

    def _save_json(self, filename: str, data: dict) -> Optional[Path]:
        """
        JSONファイルとして保存

        Args:
            filename: ファイル名 (manifest.json or final_manifest.json)
            data: 保存するデータ

        Returns:
            保存先パス（output_dirが未設定の場合はNone）
        """
        if self.output_dir is None:
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path

    @weave.op()
    def process(
        self,
        video_id: str,
        frame_paths: List[str]
    ) -> Tuple[Manifest, FinalManifest]:
        """
        二段階フィルタリング実行

        Args:
            video_id: 動画ID
            frame_paths: 全フレームのローカルパス

        Returns:
            (manifest, final_manifest)
        """
        # Stage1: 視覚的類似度フィルタリング
        manifest = self.stage1_filter.filter_frames(
            video_id=video_id,
            frame_paths=frame_paths,
            job_id=video_id  # video_idをjob_idとして使用
        )

        # manifest.json を保存
        manifest_path = self._save_json("manifest.json", manifest.model_dump())
        if manifest_path:
            print(f"Saved manifest: {manifest_path}")

        # Stage2: VLM意味的フィルタリング
        final_manifest = self.stage2_filter.filter_frames(manifest)

        # final_manifest.json を保存
        final_manifest_path = self._save_json("final_manifest.json", final_manifest.model_dump())
        if final_manifest_path:
            print(f"Saved final_manifest: {final_manifest_path}")

        return manifest, final_manifest
