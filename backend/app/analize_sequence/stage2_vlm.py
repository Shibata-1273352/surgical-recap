"""
Stage2: VLM意味的フィルタリング

Sliding windowでフレームをバッチ処理し、
医学的に重要なフレームを選択
"""

from typing import List, Tuple
import weave

from .models import Manifest, FinalManifest, SelectedFrame, FrameMetadata


class VLMStage2Filter:
    """
    Stage2: VLM意味的フィルタリング

    Sliding windowでフレームをバッチ処理し、
    医学的に重要なフレームを選択
    """

    def __init__(
        self,
        vision_analyzer,
        window_size: int = 5,
        overlap: int = 2
    ):
        """
        Args:
            vision_analyzer: VisionAnalyzerインスタンス
            window_size: スライディングウィンドウサイズ
            overlap: オーバーラップフレーム数
        """
        self.vision_analyzer = vision_analyzer
        self.window_size = window_size
        self.overlap = overlap
        self.step_size = window_size - overlap

    def _generate_sliding_windows(
        self,
        frames: List[FrameMetadata],
        window_size: int
    ) -> List[Tuple[int, List[FrameMetadata]]]:
        """
        スライディングウィンドウ生成

        Args:
            frames: フレームのリスト
            window_size: ウィンドウサイズ

        Returns:
            [(batch_id, [frame, ...]), ...]
        """
        windows = []
        batch_id = 0

        for i in range(0, len(frames), self.step_size):
            window = frames[i:i + window_size]
            if len(window) >= 3:  # 最低3フレーム必要
                windows.append((batch_id, window))
                batch_id += 1

        return windows

    def _batch_local_to_global_index(
        self,
        batch_id: int,
        local_index: int
    ) -> int:
        """
        バッチ内のローカルインデックスをグローバルインデックスに変換

        Args:
            batch_id: バッチID
            local_index: バッチ内インデックス (0-4)

        Returns:
            グローバルインデックス (Stage1 keep_indices内)
        """
        return batch_id * self.step_size + local_index

    def _deduplicate_selections(
        self,
        selections: List[Tuple[int, int, int]]
    ) -> List[Tuple[int, int, int]]:
        """
        重複する選択を除去（OR論理）

        Args:
            selections: [(batch_id, local_index, global_index), ...]

        Returns:
            重複除去後のリスト
        """
        # global_indexでユニーク化
        seen = set()
        unique = []

        for batch_id, local_idx, global_idx in selections:
            if global_idx not in seen:
                seen.add(global_idx)
                unique.append((batch_id, local_idx, global_idx))

        return sorted(unique, key=lambda x: x[2])  # global_indexでソート

    @weave.op()
    def filter_frames(
        self,
        manifest: Manifest
    ) -> FinalManifest:
        """
        Stage1の結果から医学的に重要なフレームを選択

        Args:
            manifest: Stage1のManifest

        Returns:
            FinalManifest: 選択されたフレーム
        """
        frames = manifest.frames
        all_selections = []

        # スライディングウィンドウ生成
        windows = self._generate_sliding_windows(frames, self.window_size)

        # 各バッチを処理
        for batch_id, window_frames in windows:
            image_paths = [f.file_path for f in window_frames]

            # VLMで選択
            try:
                selected_indices = self.vision_analyzer.select_keyframes_batch(
                    image_paths=image_paths,
                    batch_id=batch_id
                )

                # グローバルインデックスに変換
                for local_idx in selected_indices:
                    global_idx = self._batch_local_to_global_index(batch_id, local_idx)
                    # global_idxがframes配列の範囲内かチェック
                    if global_idx < len(frames):
                        all_selections.append((batch_id, local_idx, global_idx))

            except Exception as e:
                # エラー時はバッチの中央フレームを選択
                print(f"Warning: Batch {batch_id} failed: {e}. Using center frame.")
                center_idx = len(window_frames) // 2
                global_idx = self._batch_local_to_global_index(batch_id, center_idx)
                if global_idx < len(frames):
                    all_selections.append((batch_id, center_idx, global_idx))

        # 重複除去
        unique_selections = self._deduplicate_selections(all_selections)

        # SelectedFrame作成
        selected_frames = []
        for batch_id, local_idx, global_idx in unique_selections:
            frame = frames[global_idx]
            selected_frames.append(SelectedFrame(
                file_path=frame.file_path,
                timestamp=frame.timestamp
            ))

        return FinalManifest(
            job_id=manifest.job_id,
            video_id=manifest.video_id,
            stage1_frame_count=len(frames),
            selected_frame_count=len(selected_frames),
            selected_frames=selected_frames
        )
