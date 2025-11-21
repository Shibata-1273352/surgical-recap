"""
フレーム解析パイプライン

選択されたキーフレームの詳細解析
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from ..analize_sequence.models import FinalManifest


class FrameAnalysisPipeline:
    """
    フレーム解析パイプライン

    選択されたキーフレームに対してVision解析を実行
    """

    def __init__(self, vision_analyzer, output_dir: Optional[str] = None):
        """
        Args:
            vision_analyzer: VisionAnalyzerインスタンス
            output_dir: 出力ディレクトリ（指定しない場合は保存をスキップ）
        """
        self.vision_analyzer = vision_analyzer
        self.output_dir = Path(output_dir) if output_dir else None

    def analyze(self, final_manifest: FinalManifest) -> List[Dict[str, Any]]:
        """
        選択されたフレームを解析

        Args:
            final_manifest: Stage2で選択されたフレーム情報

        Returns:
            解析結果のリスト
        """
        results = []

        for selected_frame in final_manifest.selected_frames:
            try:
                # VLMで詳細解析
                analysis = self.vision_analyzer.analyze_frame(
                    image_path=selected_frame.file_path
                )

                results.append({
                    "timestamp": selected_frame.timestamp,
                    "file_path": selected_frame.file_path,
                    **analysis
                })

            except Exception as e:
                # エラー時はエラー情報を含めて返す
                print(f"Warning: Frame analysis failed for {selected_frame.file_path}: {e}")
                results.append({
                    "timestamp": selected_frame.timestamp,
                    "file_path": selected_frame.file_path,
                    "error": str(e)
                })

        # 結果を保存
        if self.output_dir:
            self._save_results(final_manifest.video_id, results)

        return results

    def _save_results(self, video_id: str, results: List[Dict[str, Any]]) -> Path:
        """
        解析結果をJSONファイルとして保存

        Args:
            video_id: 動画ID
            results: 解析結果

        Returns:
            保存先パス
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / "analysis_results.json"

        data = {
            "video_id": video_id,
            "frame_count": len(results),
            "results": results
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Saved analysis_results: {output_path}")
        return output_path
