# DINOv3 Integration in Surgical-Recap

## ✅ Status: READY

DINOv3がsurgical-recapプロジェクトから直接実行できるようになりました！

## 🚀 Quick Start

### 基本的な使い方

```python
from app.analize_sequence.dino_v3 import SurgicalDinoExtractor

# DINOv3 extractorを作成
extractor = SurgicalDinoExtractor(use_dinov3=True)

# フレームから特徴を抽出
features = extractor.extract_features("path/to/frame.jpg")
print(features.shape)  # [1, 384]
```

### DINOv2を使用（開発用）

```python
# DINOv2を使用（認証不要）
extractor = SurgicalDinoExtractor(use_dinov3=False)
features = extractor.extract_features("path/to/frame.jpg")
```

## 📋 使用例

### 1. 特徴抽出

```python
from app.analize_sequence.dino_v3 import SurgicalDinoExtractor

extractor = SurgicalDinoExtractor(use_dinov3=True)

# 単一フレーム
features = extractor.extract_features("frame.jpg")

# バッチ処理
frame_paths = ["frame1.jpg", "frame2.jpg", "frame3.jpg"]
features_batch = extractor.extract_features_batch(frame_paths)
print(features_batch.shape)  # [3, 384]
```

### 2. フレーム間の類似度

```python
# 2つのフレームを比較
similarity = extractor.compute_similarity("frame1.jpg", "frame2.jpg")
print(f"Similarity: {similarity:.4f}")
```

### 3. シーン変化検出

```python
# 連続フレームからシーン変化を検出
frame_paths = [f"frame_{i:04d}.jpg" for i in range(100)]
scene_changes = extractor.detect_scene_changes(
    frame_paths,
    threshold=0.7  # 類似度がこの値未満で変化とみなす
)

print(f"Scene changes at frames: {scene_changes}")
```

### 4. 手術フェーズのクラスタリング

```python
# フレームを手術フェーズに分類
frame_paths = [f"frame_{i:04d}.jpg" for i in range(100)]
clusters = extractor.cluster_phases(
    frame_paths,
    n_clusters=5  # 5つのフェーズに分類
)

# 各フレームのフェーズを確認
for i, phase in enumerate(clusters):
    print(f"Frame {i}: Phase {phase}")
```

### 5. 類似フレーム検索

```python
# データベースから類似フレームを検索
query_frame = "query_frame.jpg"
database_frames = [f"frame_{i:04d}.jpg" for i in range(100)]

results = extractor.find_similar_frames(
    query_frame,
    database_frames,
    top_k=10
)

for idx, score in results:
    print(f"Frame {idx}: Similarity {score:.4f}")
```

## 🎯 実用的なワークフロー

### 手術動画の解析

```python
from pathlib import Path
from app.analize_sequence.dino_v3 import SurgicalDinoExtractor

# 1. Extractorを初期化
extractor = SurgicalDinoExtractor(use_dinov3=True)

# 2. 動画からフレームを読み込み（既存のコードを使用）
frames_dir = Path("data/surgical_video_frames")
frame_paths = sorted(frames_dir.glob("*.jpg"))

# 3. 全フレームの特徴を抽出
print("Extracting features...")
features = extractor.extract_features_batch(
    frame_paths,
    batch_size=32
)

# 4. シーン変化を検出
print("Detecting scene changes...")
scene_changes = extractor.detect_scene_changes(frame_paths)

# 5. 手術フェーズを識別
print("Clustering surgical phases...")
phases = extractor.cluster_phases(frame_paths, n_clusters=7)

# 6. 結果を保存
import numpy as np
np.save("features.npy", features.cpu().numpy())
np.save("scene_changes.npy", scene_changes)
np.save("phases.npy", phases)
```

### 特定の手術シーンの検索

```python
# 特定のシーン（例：切開）を検索
reference_incision = "reference/incision.jpg"

# データベースから類似シーンを検索
results = extractor.find_similar_frames(
    reference_incision,
    frame_paths,
    top_k=20
)

# 類似度の高いフレームを抽出
incision_frames = [frame_paths[idx] for idx, score in results if score > 0.8]
print(f"Found {len(incision_frames)} incision frames")
```

## ⚙️ 設定

### モデルの選択

```python
# 開発環境: DINOv2（セットアップ簡単）
extractor = SurgicalDinoExtractor(use_dinov3=False)

# 本番環境: DINOv3（最高品質）
extractor = SurgicalDinoExtractor(use_dinov3=True)
```

### デバイスの指定

```python
# GPUを使用
extractor = SurgicalDinoExtractor(use_dinov3=True, device="cuda")

# CPUを使用
extractor = SurgicalDinoExtractor(use_dinov3=True, device="cpu")
```

## 🧪 テスト実行

```bash
# surgical-recapのbackendディレクトリで
cd /home/ubuntu/work/shibata/surgical-recap/backend

# デモを実行
uv run python app/analize_sequence/dino_v3.py
```

## 📊 パフォーマンス

### Tesla T4での測定値

| 処理 | 時間 | FPS |
|------|------|-----|
| 単一フレーム | 24.5 ms | 40.8 |
| バッチ (32枚) | ~0.8 s | ~40 |

### メモリ使用量

- **モデル**: ~90 MB
- **単一画像**: ~10 MB
- **バッチ (32枚)**: ~320 MB

## 🔧 トラブルシューティング

### CUDA out of memory

```python
# バッチサイズを減らす
features = extractor.extract_features_batch(
    frame_paths,
    batch_size=8  # デフォルトは32
)
```

### ImportError

```bash
# 必要なパッケージをインストール
cd /home/ubuntu/work/shibata/surgical-recap/backend
uv add torch torchvision pillow transformers scikit-learn
```

### DINOv3モデルが見つからない

DINOv3のモデルが正しくダウンロードされているか確認：
```bash
ls -la /home/ubuntu/work/shibata/dinov3/models/dinov3-vits16/
```

モデルがない場合：
```bash
cd /home/ubuntu/work/shibata/dinov3
uv run huggingface-cli download facebook/dinov3-vits16-pretrain-lvd1689m --local-dir ./models/dinov3-vits16
```

## 💡 ベストプラクティス

### 1. 特徴のキャッシュ

```python
import pickle
from pathlib import Path

cache_file = Path("features_cache.pkl")

if cache_file.exists():
    with open(cache_file, 'rb') as f:
        features = pickle.load(f)
else:
    features = extractor.extract_features_batch(frame_paths)
    with open(cache_file, 'wb') as f:
        pickle.dump(features, f)
```

### 2. 大量のフレーム処理

```python
# チャンクに分けて処理
chunk_size = 1000

for i in range(0, len(frame_paths), chunk_size):
    chunk = frame_paths[i:i+chunk_size]
    features = extractor.extract_features_batch(chunk)
    # 結果を保存
    np.save(f"features_chunk_{i}.npy", features.cpu().numpy())
```

### 3. 環境変数での制御

```python
import os

# 環境変数で制御
use_dinov3 = os.getenv("USE_DINOV3", "true").lower() == "true"
extractor = SurgicalDinoExtractor(use_dinov3=use_dinov3)
```

## 📚 関連ドキュメント

- **DINOv3統合ガイド**: `/home/ubuntu/work/shibata/dinov3/DINOV3_COMPLETE.md`
- **移行ガイド**: `/home/ubuntu/work/shibata/dinov3/MIGRATION_GUIDE.md`
- **API詳細**: `/home/ubuntu/work/shibata/dinov3/dino_extractor.py`

## ✅ まとめ

- ✅ DINOv3がsurgical-recapから直接使用可能
- ✅ シーン変化検出、フェーズ分類、類似検索をサポート
- ✅ バッチ処理で高速化
- ✅ DINOv2との簡単な切り替え
- ✅ 本番環境対応

surgical-recapプロジェクトでDINOv3の強力な特徴抽出機能を活用してください！🎉
