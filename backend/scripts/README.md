# Surgical-Recap Scripts

このディレクトリには、Surgical-Recapプロジェクトで使用するスクリプトが含まれています。

## run_evaluation.sh

SambaNovaでの推論から評価までの一連の流れを一括実行するシェルスクリプトです。

### 機能

- 環境変数の自動チェック
- データセットの存在確認
- フレーム数の指定
- 動画インデックスの指定
- 評価時間とコストの概算表示
- W&B Weave Evaluationsへの結果ログ
- カラフルな進捗表示

### 使い方

#### 基本的な使い方

```bash
# デフォルト設定で実行（3フレーム）
./scripts/run_evaluation.sh

# フレーム数を指定
./scripts/run_evaluation.sh --frames 5

# 異なる動画を評価
./scripts/run_evaluation.sh --frames 10 --video 1

# 画像付きで評価
./scripts/run_evaluation.sh --frames 5 --with-images
```

#### オプション

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|-----------|
| `--frames N` | `-f` | 評価するフレーム数 | 3 |
| `--video INDEX` | `-v` | 評価する動画のインデックス | 0 |
| `--with-images` | `-i` | 評価結果に画像を含める | false |
| `--help` | `-h` | ヘルプメッセージを表示 | - |

### 必要な環境変数

スクリプトを実行する前に、以下の環境変数を設定してください（`.env`ファイルに記載）：

```bash
# SambaNova Cloud (Vision解析用)
SAMBANOVA_API_KEY=your_sambanova_api_key

# Azure OpenAI (Judge用)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# W&B Weave (トレーシング用)
WANDB_API_KEY=your_wandb_api_key
WANDB_ENTITY=your_wandb_entity
WANDB_PROJECT=surgical-recap
```

### 実行例

#### 例1: 基本的な評価（3フレーム）

```bash
cd backend
./scripts/run_evaluation.sh
```

出力例:
```
========================================
  Surgical-Recap Evaluation Pipeline
========================================

[1/5] Checking environment variables...
  ✓ All required credentials configured

[2/5] Checking dataset...
  ✓ Dataset found: 247 frames available

[3/5] Evaluation settings:
  Frames to evaluate: 3
  Video index: 0
  Include images: false
  Evaluation script: test_weave_evals.py

📊 Estimates:
  Time: ~6 seconds
  Cost: ~$0.03 (Azure OpenAI)

Press Enter to continue, or Ctrl+C to cancel...

[4/5] Preparing evaluation...
  ✓ Evaluation prepared

[5/5] Running evaluation pipeline...

Surgical-Recap Evaluation
======================================================================
✓ Weave initialized
✓ Dataset loaded
✓ Vision analyzer initialized

📊 Evaluation Dataset: 3 frames from video01
----------------------------------------------------------------------

🚀 Running evaluation...

======================================================================
✓ Evaluation completed!

📈 Results:

  📊 Medical Accuracy: 3.00/5
  📊 Guideline Compliance: 3.00/5
  📊 Clarity: 1.33/5
  📊 Educational Value: 2.00/5
  📊 Total Score: 9.67/20
  ⏱️  Model Latency: 0.46s

🔗 View detailed results:
   https://wandb.ai/takasi-shibata/surgical-recap/weave

========================================
  ✓ Evaluation completed successfully!
========================================
```

#### 例2: 大規模評価（10フレーム）

```bash
./scripts/run_evaluation.sh --frames 10
```

#### 例3: 画像付き評価（Data URI形式）

```bash
./scripts/run_evaluation.sh --frames 5 --with-images
```

この場合、W&B Weaveの評価結果に画像がインライン表示されます。

### トラブルシューティング

#### エラー: 環境変数が設定されていない

```
❌ SAMBANOVA_API_KEY is not set
```

**解決策**: `.env`ファイルに必要な環境変数を設定してください。

```bash
# .envファイルを編集
vi ../.env

# または環境変数をエクスポート
export SAMBANOVA_API_KEY=your_api_key
```

#### エラー: データセットが見つからない

```
❌ Dataset not found at ../data/cholecSeg8k
```

**解決策**: データセットをダウンロードしてください。

```bash
uv run python scripts/download_dataset.py
```

#### エラー: Video index out of range

```
❌ Video index 5 out of range (0-1)
```

**解決策**: 存在する動画のインデックスを指定してください（通常は0-1）。

```bash
./scripts/run_evaluation.sh --video 0
```

### コスト見積もり

スクリプトは実行前にコストの概算を表示します：

| フレーム数 | 概算時間 | 概算コスト |
|-----------|---------|-----------|
| 3 | 6秒 | $0.03 |
| 5 | 10秒 | $0.05 |
| 10 | 20秒 | $0.10 |
| 50 | 100秒 | $0.50 |
| 100 | 200秒 | $1.00 |

**注意**:
- Vision解析（SambaNova）は無料プラン内
- Judge評価（Azure OpenAI）は従量課金
- 5スコアラー使用時の概算（1フレーム = 5回のJudge呼び出し）

### 自動化

cronジョブで定期的に評価を実行する例：

```bash
# 毎日午前2時に10フレーム評価
0 2 * * * cd /path/to/project/backend && ./scripts/run_evaluation.sh --frames 10 >> /var/log/surgical-recap-eval.log 2>&1
```

### CI/CD統合

GitHub Actionsで評価を実行する例：

```yaml
name: Run Evaluation

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 0'  # 毎週日曜日

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install uv
          cd backend && uv sync
      - name: Run evaluation
        env:
          SAMBANOVA_API_KEY: ${{ secrets.SAMBANOVA_API_KEY }}
          AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
          AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          WANDB_API_KEY: ${{ secrets.WANDB_API_KEY }}
        run: |
          cd backend
          ./scripts/run_evaluation.sh --frames 5
```

---

## download_dataset.py

cholecSeg8kデータセットをダウンロードするスクリプトです。

### 使い方

```bash
uv run python scripts/download_dataset.py
```

詳細は[DATASET.md](../docs/DATASET.md)を参照してください。

---

## その他のスクリプト

今後、以下のようなスクリプトを追加予定：

- `export_results.sh`: 評価結果をCSV/JSONでエクスポート
- `compare_models.sh`: 複数のモデル設定を比較
- `batch_evaluate.sh`: 複数の動画を一括評価

---

**作成日**: 2025年11月20日
**最終更新**: 2025年11月20日
