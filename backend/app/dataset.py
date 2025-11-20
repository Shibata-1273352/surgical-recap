"""cholecSeg8kデータセットローダー"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
import cv2


class CholecSeg8kLoader:
    """cholecSeg8kデータセットのローダー

    データセット構造:
    cholecseg8k/
    ├── video01/
    │   ├── video01_00080/
    │   │   ├── frame_80_endo.png
    │   │   ├── frame_80_endo_mask.png
    │   │   └── ...
    │   └── ...
    └── ...
    """

    def __init__(self, data_dir: str):
        """
        Args:
            data_dir: データセットのルートディレクトリ
        """
        self.data_dir = Path(data_dir)

        # データセットの存在確認
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Dataset directory not found: {self.data_dir}")

        # ビデオフォルダの一覧を取得
        self.video_dirs = sorted([d for d in self.data_dir.iterdir() if d.is_dir() and d.name.startswith("video")])

        if not self.video_dirs:
            raise FileNotFoundError(f"No video directories found in: {self.data_dir}")

    def load_sequence(self, video_id: str, load_images: bool = False) -> List[Dict]:
        """
        画像シーケンスとメタデータを読み込み

        Args:
            video_id: ビデオID (例: "video01")
            load_images: 画像データも読み込むかどうか（メモリに注意）

        Returns:
            フレーム情報のリスト
        """
        sequence = []
        video_dir = self.data_dir / video_id

        if not video_dir.exists():
            raise FileNotFoundError(f"Video directory not found: {video_dir}")

        # タイムスタンプフォルダを時系列順に取得
        timestamp_dirs = sorted([d for d in video_dir.iterdir() if d.is_dir()])

        for timestamp_dir in timestamp_dirs:
            # 画像ファイルを取得（_endo.png で終わるもの、マスク以外）
            image_files = sorted([
                f for f in timestamp_dir.glob("*_endo.png")
                if not any(x in f.name for x in ["mask", "watershed"])
            ])

            for img_path in image_files:
                # フレーム番号を抽出 (frame_80_endo.png -> 80)
                frame_num = self._extract_frame_number(img_path)
                frame_id = img_path.stem  # "frame_80_endo"

                # 画像読み込み（オプション）
                image = None
                if load_images:
                    image = cv2.imread(str(img_path))

                # セグメンテーションマスク読み込み（存在する場合）
                mask_path = img_path.parent / f"frame_{frame_num}_endo_mask.png"
                mask = None
                if mask_path.exists() and load_images:
                    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

                sequence.append({
                    "video_id": video_id,
                    "timestamp_dir": timestamp_dir.name,
                    "frame_id": frame_id,
                    "frame_number": frame_num,
                    "image_path": str(img_path),
                    "image": image,
                    "mask": mask,
                    "mask_path": str(mask_path) if mask_path.exists() else None,
                })

        return sequence

    def get_all_videos(self) -> List[str]:
        """すべてのビデオIDを取得"""
        return [video_dir.name for video_dir in self.video_dirs]

    def get_frame_count(self, video_id: Optional[str] = None) -> int:
        """
        フレーム数を取得

        Args:
            video_id: ビデオID（Noneの場合は全体）

        Returns:
            フレーム数
        """
        if video_id:
            video_dir = self.data_dir / video_id
            if not video_dir.exists():
                return 0

            count = 0
            for timestamp_dir in video_dir.iterdir():
                if timestamp_dir.is_dir():
                    # _endo.png で終わるファイル（マスク以外）をカウント
                    count += len([
                        f for f in timestamp_dir.glob("*_endo.png")
                        if not any(x in f.name for x in ["mask", "watershed"])
                    ])
            return count
        else:
            # 全ビデオの合計フレーム数
            return sum(self.get_frame_count(vid.name) for vid in self.video_dirs)

    def _extract_frame_number(self, path: Path) -> int:
        """
        ファイル名からフレーム番号を抽出

        Args:
            path: ファイルパス

        Returns:
            フレーム番号
        """
        stem = path.stem

        # 末尾の数字を抽出
        import re
        match = re.search(r'(\d+)$', stem)
        if match:
            return int(match.group(1))

        return 0


def get_dataset_loader() -> Optional[CholecSeg8kLoader]:
    """
    データセットローダーのインスタンスを取得

    Returns:
        CholecSeg8kLoader（データセットが見つからない場合はNone）
    """
    # backend ディレクトリからの相対パスまたは環境変数
    default_path = os.path.join(os.path.dirname(__file__), "..", "data", "cholecseg8k")
    dataset_path = os.getenv("DATASET_PATH", default_path)

    try:
        return CholecSeg8kLoader(dataset_path)
    except FileNotFoundError:
        return None
