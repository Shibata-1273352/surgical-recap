# 📊 評価システム クイックスタート

## 🎯 用途別スクリプト選択

### 画像サムネイル表示優先: test_continuous_frames.py ⭐

**用途**: Vision解析のみ、トレース一覧で画像を視覚的に確認

```bash
# デフォルト（5フレーム、video01）
uv run python test_continuous_frames.py

# 10フレームを処理
uv run python test_continuous_frames.py 10

# video02の20フレームを処理
uv run python test_continuous_frames.py 20 1
```

**特徴**:
- ✅ **トレース一覧のInputカラムに画像サムネイル表示**
- ✅ Vision解析結果（手技、器具、リスク、説明）
- ❌ 評価メトリック（Judge）なし
- ⚡ 高速（1秒/フレーム）

### 品質評価優先: test_weave_evals.py

**用途**: Azure OpenAI Judgeによる品質評価、スコアリング

```bash
# デフォルト（3フレーム、video01）
uv run python test_weave_evals.py

# 5フレームを評価
uv run python test_weave_evals.py 5

# 10フレームを評価
uv run python test_weave_evals.py 10

# video02の20フレームを評価
uv run python test_weave_evals.py 20 1
```

**特徴**:
- ✅ 5つの評価メトリック（Medical Accuracy, Clarity, etc.）
- ✅ Azure OpenAI Judgeによる品質スコア
- ⚠️ トレース一覧では画像サムネイル非表示（Evaluationコンテキスト）
- ✅ 個別のトレース詳細では画像確認可能
- 🐢 低速（3-4秒/フレーム）、コスト高（$0.01/フレーム）

**引数**:
- 第1引数: フレーム数（デフォルト: 3または5）
- 第2引数: ビデオインデックス（デフォルト: 0）

### 自動化スクリプト: run_evaluation.sh

```bash
# デフォルト（3フレーム）
./scripts/run_evaluation.sh

# 10フレームを評価
./scripts/run_evaluation.sh --frames 10

# 50フレームを評価
./scripts/run_evaluation.sh --frames 50

# video02の20フレームを評価
./scripts/run_evaluation.sh --frames 20 --video 1
```

**オプション**:
- `-f, --frames N`: 評価するフレーム数（デフォルト: 3）
- `-v, --video INDEX`: ビデオインデックス（デフォルト: 0）

## 🖼️ 画像サムネイルの確認方法

### 方法A: Tracesページ（推奨）

1. https://wandb.ai/takasi-shibata/surgical-recap/weave/traces を開く
2. フィルターで `surgical_vision_model_with_image` を選択
3. 最新のトレースのInputカラムに画像サムネイルが表示されます

### 方法B: Evaluationsページから

1. https://wandb.ai/takasi-shibata/surgical-recap/weave を開く
2. **Evaluations**タブをクリック
3. 最新のEvaluationをクリック
4. **Calls**または**Child Calls**セクションを探す
5. `surgical_vision_model_with_image`の呼び出しをクリック
6. **Input**セクションで画像を確認

## 📈 評価メトリック

全5つのスコアラーが実行されます：

| メトリック | 範囲 | 説明 |
|----------|------|------|
| Medical Accuracy | 1-5 | 医学的正確性（手技・器具・リスク判定） |
| Guideline Compliance | 1-5 | ガイドライン準拠度 |
| Clarity | 1-5 | 説明の明確さ |
| Educational Value | 1-5 | 教育的価値 |
| Total Score | 4-20 | 合計スコア |

## ⏱️ パフォーマンス

- **Vision解析**: 約0.5-1.0秒/フレーム
- **評価（5スコアラー）**: 約2-3秒/フレーム
- **合計**: 約3-4秒/フレーム

### コスト見積もり

Azure OpenAI (Judge) の従量課金:
- 1フレームあたり約$0.01（5スコアラー使用時）
- 10フレーム: 約$0.10
- 50フレーム: 約$0.50
- 100フレーム: 約$1.00

## 🎯 使用例

### シナリオ1: 画像を見ながらVision解析を確認

```bash
# トレース一覧で画像サムネイル表示 ⭐
uv run python test_continuous_frames.py 10

# Tracesページで各フレームの画像とVision解析結果を確認
# https://wandb.ai/takasi-shibata/surgical-recap/weave/traces
```

### シナリオ2: Vision解析の品質を評価

```bash
# 評価メトリック付きで少数フレームをテスト
uv run python test_weave_evals.py 5

# Evaluationsページで品質スコアを確認
# https://wandb.ai/takasi-shibata/surgical-recap/weave
```

### シナリオ3: 開発・デバッグ

```bash
# 2フレームで高速動作確認（画像サムネイル表示）
uv run python test_continuous_frames.py 2
```

### シナリオ4: 大規模評価

```bash
# 50-100フレームの品質評価（コストに注意）
./scripts/run_evaluation.sh --frames 50
```

### シナリオ5: 複数ビデオの解析

```bash
# video01の10フレーム（画像サムネイル）
uv run python test_continuous_frames.py 10 0

# video02の10フレーム（画像サムネイル）
uv run python test_continuous_frames.py 10 1

# video03の10フレーム（品質評価）
./scripts/run_evaluation.sh --frames 10 --video 2
```

## 💡 ベストプラクティス

### 1. 段階的な評価

最初は少数のフレームでテストしてから、徐々に増やす：

```bash
# Step 1: 動作確認（2フレーム、画像サムネイル表示）
uv run python test_continuous_frames.py 2

# Step 2: Vision解析の視覚的確認（10フレーム）
uv run python test_continuous_frames.py 10

# Step 3: 品質評価（5-10フレーム）
uv run python test_weave_evals.py 10

# Step 4: 本番評価（50フレーム以上）
./scripts/run_evaluation.sh --frames 50
```

### 2. コスト管理

大規模評価前に見積もりを確認：

```bash
# スクリプトを実行すると、実行前にコスト見積もりが表示されます
./scripts/run_evaluation.sh --frames 100

# 出力例:
# 📊 Estimates:
#   Time: ~200 seconds
#   Cost: ~$1.00 (Azure OpenAI)
```

### 3. 継続的な改善

1. **ベースライン取得**: 初回評価でスコアを記録
2. **プロンプト改善**: Vision/Judgeのプロンプトを調整
3. **再評価**: 同じデータセットで再度評価
4. **比較**: W&B Weave UIで改善度を確認

## ⚠️ 注意事項

- **画像表示**: Evaluationのサマリー画面には画像は表示されません。個別のトレースを確認してください。
- **レート制限**: Azure OpenAIのレート制限に注意。大規模評価時は時間がかかる場合があります。
- **ディスク容量**: データセットは約4.5GB必要です。

## 🐛 トラブルシューティング

### 画像が見つからない

- Tracesページ（https://wandb.ai/.../weave/traces）を確認
- フィルターで`surgical_vision_model_with_image`を選択
- 最新のトレースのInputカラムを確認

### 評価が遅い

- フレーム数を減らす（`--frames 2`など）
- スコアラー数を減らす（コード修正が必要）

### メモリ不足

- フレーム数を減らす
- 画像サイズを小さくする（デフォルト: 150px）

---

**詳細**: [docs/EVALUATION.md](docs/EVALUATION.md) を参照
