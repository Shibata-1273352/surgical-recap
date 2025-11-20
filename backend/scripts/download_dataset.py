#!/usr/bin/env python3
"""cholecSeg8kデータセットのダウンロードスクリプト"""

import kagglehub
from pathlib import Path
import shutil


def download_cholecseg8k(target_dir: str = "data/cholecseg8k"):
    """
    cholecSeg8kデータセットをダウンロード

    Args:
        target_dir: ダウンロード先ディレクトリ
    """
    print("cholecSeg8kデータセットをダウンロード中...")
    print("=" * 60)

    # データセットをダウンロード
    path = kagglehub.dataset_download("newslab/cholecseg8k")

    print(f"\nダウンロード完了:")
    print(f"  元のパス: {path}")

    # プロジェクトのdataディレクトリに移動
    project_root = Path(__file__).parent.parent
    target_path = project_root / target_dir

    print(f"  移動先: {target_path}")

    # ディレクトリが存在する場合は削除
    if target_path.exists():
        print(f"  既存のディレクトリを削除中...")
        shutil.rmtree(target_path)

    # データセットをコピー
    print(f"  データセットをコピー中...")
    shutil.copytree(path, target_path)

    print("=" * 60)
    print("✓ データセットの準備が完了しました")
    print(f"  場所: {target_path.absolute()}")

    # データセットの内容を確認
    print("\nデータセットの内容:")
    for item in sorted(target_path.iterdir()):
        if item.is_file():
            size_mb = item.stat().st_size / (1024 * 1024)
            print(f"  - {item.name} ({size_mb:.2f} MB)")
        else:
            file_count = len(list(item.glob("*")))
            print(f"  - {item.name}/ ({file_count} files)")

    return target_path


if __name__ == "__main__":
    download_cholecseg8k()
