# DINOv3 Integration in Surgical-Recap

## ✅ Status: READY

DINOv3がsurgical-recapプロジェクトから直接実行できます。

## 🚀 Quick Start

```python
from app.analize_sequence.dino_v3 import SurgicalDinoExtractor

# DINOv3 extractorを作成（解像度448がデフォルト）
extractor = SurgicalDinoExtractor()

# フレームから特徴を抽出
features = extractor.extract_features("path/to/frame.jpg")
print(features.shape)  # [1, 384]

# バッチ処理
frame_paths = ["frame1.jpg", "frame2.jpg", "frame3.jpg"]
features_batch = extractor.extract_features_batch(frame_paths)
print(features_batch.shape)  # [3, 384]
```

## 📋 主要機能

### 1. 特徴抽出

```python
# 単一フレーム
features = extractor.extract_features("frame.jpg")

# バッチ処理（デフォルト: batch_size=64）
features_batch = extractor.extract_features_batch(frame_paths)
```

### 2. フレーム間の類似度

```python
similarity = extractor.compute_similarity("frame1.jpg", "frame2.jpg")
print(f"Similarity: {similarity:.4f}")
```

### 3. シーン変化検出

```python
scene_changes = extractor.detect_scene_changes(
    frame_paths,
    threshold=0.7  # 類似度がこの値未満で変化とみなす
)
print(f"Scene changes at frames: {scene_changes}")
```

### 4. 手術フェーズのクラスタリング

```python
clusters = extractor.cluster_phases(frame_paths, n_clusters=5)
```

### 5. 類似フレーム検索

```python
results = extractor.find_similar_frames(
    "query_frame.jpg",
    database_frames,
    top_k=10
)
```

## ⚙️ 設定

### 解像度の指定

```python
# デフォルト: 448（推奨）
extractor = SurgicalDinoExtractor()

# 高速モード: 224
extractor = SurgicalDinoExtractor(resolution=224)

# 高精度モード: 518
extractor = SurgicalDinoExtractor(resolution=518)
```

### デバイスの指定

```python
extractor = SurgicalDinoExtractor(device="cuda")  # GPU
extractor = SurgicalDinoExtractor(device="cpu")   # CPU
```

## 📊 パフォーマンス

### ベンチマーク環境

- **GPU**: Tesla T4 (16GB VRAM)
- **モデル**: DINOv3-ViT-S/16 (21.6M params)
- **入力フレーム**: 1920x1080 JPEG
- **テストフレーム数**: 100枚

### 解像度 × バッチサイズ ベンチマーク (2024-11-21)

| 解像度 | Batch 8 | Batch 16 | Batch 32 | Batch 64 | VRAM (B64) |
|--------|---------|----------|----------|----------|------------|
| 224 (fast) | 248.9 fps | 245.6 fps | 271.3 fps | **295.8 fps** | 0.37 GB |
| 384 | 88.2 fps | 90.4 fps | 92.6 fps | 91.8 fps | 0.90 GB |
| **448 (推奨)** | 62.3 fps | 63.2 fps | 63.8 fps | **63.9 fps** | 1.18 GB |
| 518 (native) | 45.1 fps | 45.0 fps | 44.5 fps | 45.1 fps | 1.52 GB |

### 推奨設定

- **採用設定**: 448解像度 + batch 64 = **63.9 fps**（VRAM 1.18GB）
- 1時間動画（3600フレーム@1fps）: 約56秒で処理完了

### 設定選択の指針

| ユースケース | 解像度 | バッチサイズ | 想定FPS |
|-------------|--------|-------------|---------|
| 高速プレビュー | 224 | 64 | ~296 fps |
| **本番運用（推奨）** | 448 | 64 | ~64 fps |
| 高精度解析 | 518 | 64 | ~45 fps |

### メモリ使用量（448解像度）

- **モデル**: ~90 MB
- **バッチ (64枚)**: ~1.18 GB

## 🔧 トラブルシューティング

### CUDA out of memory

```python
# バッチサイズを減らす
features = extractor.extract_features_batch(
    frame_paths,
    batch_size=8
)
```

### ImportError

```bash
cd /home/ubuntu/iori/surgical-recap/backend
uv sync
```

### DINOv3モデルが見つからない

```bash
ls -la /home/ubuntu/work/shibata/dinov3/models/dinov3-vits16/
```

## 🧪 テスト実行

```bash
cd /home/ubuntu/iori/surgical-recap/backend
source .venv/bin/activate
python -c "from app.analize_sequence.dino_v3 import SurgicalDinoExtractor; e = SurgicalDinoExtractor(); print('OK')"
```

## 📚 関連ファイル

- `dino_v3.py`: メインの特徴抽出クラス
- `stage1_dino.py`: Stage1フィルタリングパイプライン
- `pipeline.py`: 二段階フィルタリング統合
