# Surgical-Recap 評価システム

## 概要

Surgical-Recapの評価システムは、**W&B Weave + Azure OpenAI Judge**を使用して、手術画像解析の品質を自動的に評価します。

### システム構成

```
手術画像フレーム
    ↓
Vision解析 (SambaNova + Llama-4-Maverick)
    ↓
解析結果（手技、器具、リスク、説明）
    ↓
LLM as a Judge (Azure OpenAI GPT-4o)
    ↓
5つの評価メトリック（1-5点 × 4 + 合計スコア）
    ↓
W&B Weave Evaluations（自動トレーシング＆可視化）
```

---

## 評価軸の詳細

### 1. 医学的正確性（Medical Accuracy）

**評価範囲**: 1-5点

**評価項目**:
- 手技認識は正確か
- 器具識別は正確か
- リスク評価は適切か

**スコアリング基準**:
- **5点**: すべての項目が完璧に正確
- **4点**: ほぼ正確だが、細かい誤認識がある
- **3点**: 基本的な認識はできているが、重要な誤りがある
- **2点**: 複数の誤認識があり、信頼性が低い
- **1点**: ほとんど不正確、または認識失敗

**例**:
```
解析結果: "Dissection", "Maryland Grasper", "Medium"
評価: 手技は正確だが、器具名が曖昧（"Grasper"のみの方が適切） → 3点
```

---

### 2. ガイドライン準拠度（Guideline Compliance）

**評価範囲**: 1-5点

**評価項目**:
- 標準的な医療ガイドラインに沿っているか
- 用語が適切か（医学用語の使用）

**スコアリング基準**:
- **5点**: ガイドラインに完全準拠、用語も標準的
- **4点**: ほぼ準拠しているが、一部表現が非標準的
- **3点**: 基本的には準拠しているが、重要な逸脱がある
- **2点**: ガイドラインからの逸脱が複数ある
- **1点**: ガイドラインに準拠していない

**参照ガイドライン**:
- 日本外科学会ガイドライン
- 腹腔鏡下胆嚢摘出術の標準手技

**例**:
```
解析結果: リスクレベル "High"（クリッピング時）
評価: 標準的なリスク評価に基づいている → 4点
```

---

### 3. 説明の明確さ（Clarity）

**評価範囲**: 1-5点

**評価項目**:
- 説明が具体的でわかりやすいか
- 専門用語が適切に使われているか
- 冗長でなく、簡潔か

**スコアリング基準**:
- **5点**: 非常に明確で具体的、誰が読んでも理解できる
- **4点**: 明確だが、一部曖昧な表現がある
- **3点**: 基本的な情報はあるが、不明瞭な部分がある
- **2点**: 説明が曖昧で理解しにくい
- **1点**: 説明が欠如している、または意味不明

**例**:
```
解析結果: description "胆嚢管へのクリップ適用"
評価: 具体的で明確 → 5点

解析結果: description "処置中"
評価: 曖昧で具体性に欠ける → 2点
```

---

### 4. 教育的価値（Educational Value）

**評価範囲**: 1-5点

**評価項目**:
- 若手医師の学習に役立つか
- 重要なポイントが含まれているか
- 注意喚起や学びの要素があるか

**スコアリング基準**:
- **5点**: 教育的に非常に価値が高い、学びのポイントが明確
- **4点**: 教育的価値があるが、追加情報があればより良い
- **3点**: 基本的な情報は提供されているが、教育的深みに欠ける
- **2点**: 教育的価値が低い、表面的な情報のみ
- **1点**: 教育的価値がほとんどない

**重視される要素**:
- 解剖学的な注意点
- 手技のコツ
- よくある失敗とその回避方法
- リスクの根拠

**例**:
```
解析結果: "Clipping"（詳細な説明なし）
評価: 基本情報のみで教育的深みなし → 2点

解析結果: "Clipping - Calot三角の確実な同定後に実施"
評価: 教育的に重要なポイントを含む → 4点
```

---

### 5. 合計スコア（Total Score）

**評価範囲**: 4-20点

**計算方法**:
```
合計スコア = 医学的正確性 + ガイドライン準拠度 + 説明の明確さ + 教育的価値
```

**解釈**:
- **16-20点**: 優秀（Excellent）- そのまま教材として使用可能
- **12-15点**: 良好（Good）- 基本的に信頼できるが改善の余地あり
- **8-11点**: 要改善（Needs Improvement）- 重要な問題がある
- **4-7点**: 不可（Poor）- 大幅な改善が必要

---

## 評価の実行手順

### 1. 環境変数の設定

`.env`ファイルに以下を設定：

```bash
# SambaNova API（Vision解析用）
SAMBANOVA_API_KEY=your_sambanova_api_key

# Azure OpenAI（Judge用）
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# W&B Weave（トレーシング用）
WANDB_API_KEY=your_wandb_api_key
WANDB_ENTITY=your_wandb_entity
WANDB_PROJECT=surgical-recap
```

### 2. テストスクリプトの実行

#### 基本的な評価（3フレーム、全5メトリック）

```bash
cd backend
uv run python test_weave_evals.py
```

**出力例**:
```
Testing W&B Weave Evaluations...
======================================================================
✓ All credentials configured
✓ Dataset loaded
✓ Vision analyzer initialized

📊 Evaluation Dataset: 3 frames from video01
----------------------------------------------------------------------
🚀 Running W&B Weave Evaluation...

======================================================================
✓ Weave Evaluation completed!

📈 Results:
  {'medical_accuracy_scorer': {'medical_accuracy': {'mean': 3.0}},
   'guideline_compliance_scorer': {'guideline_compliance': {'mean': 3.0}},
   'clarity_scorer': {'clarity': {'mean': 1.67}},
   'educational_value_scorer': {'educational_value': {'mean': 2.0}},
   'total_score_scorer': {'total_score': {'mean': 9.67}},
   'model_latency': {'mean': 3.0}}

🔗 View detailed results in W&B Weave:
   https://wandb.ai/<entity>/<project>/weave

💡 The evaluation results are now visible in the 'Evaluations' tab
```

#### シンプルな評価（2フレーム、2メトリック）

```bash
uv run python test_weave_evals_fixed.py
```

デバッグや動作確認に便利です。

### 3. プログラムからの実行

```python
import asyncio
from app.vision import get_vision_analyzer
from app.dataset import get_dataset_loader
from app.evaluation import run_evaluation

async def main():
    # データセット準備
    loader = get_dataset_loader()
    videos = loader.get_all_videos()
    sequence = loader.load_sequence(videos[0], load_images=False)

    dataset = [
        {"input": sequence[0]['image_path']},
        {"input": sequence[1]['image_path']},
    ]

    # Vision analyzer取得
    analyzer = get_vision_analyzer()

    # 評価実行
    results = await run_evaluation(dataset, analyzer)

    print(results)

asyncio.run(main())
```

---

## W&B Weave UIでの結果確認

### 1. Evalsタブへのアクセス

1. W&B Weaveにアクセス: https://wandb.ai/<entity>/<project>/weave
2. 左サイドバーの **"Evaluations"** または **"Evals"** タブをクリック
3. 実行された評価のリストが表示される

### 2. 評価の詳細表示

各評価エントリをクリックすると：

- **Summary**: 全メトリックの平均値
- **Samples**: 各フレームの詳細スコア
- **Traces**: 各操作のトレース（Vision解析、Judge評価）
- **Latency**: モデルの実行時間

### 3. メトリックの可視化

- **時系列グラフ**: 複数回の評価での推移
- **ヒートマップ**: フレームごとのスコア分布
- **比較表**: 異なるモデルや設定の比較

### 4. トレースの確認

**Traces**タブでは：
- Vision解析の入出力
- Judge評価のプロンプトとレスポンス
- 各ステップの実行時間

をドリルダウンして確認できます。

---

## カスタム評価の作成

### 独自のスコアラー関数を追加

```python
import weave
from app.evaluation import get_evaluator

@weave.op()
async def custom_risk_scorer(model_output: dict) -> dict:
    """カスタムリスク評価スコアラー"""
    risk = model_output.get("risk", "Unknown")

    # 独自のロジック
    score = 5 if risk == "High" else 3 if risk == "Medium" else 1

    return {"custom_risk_score": score}

# 評価時に追加
results = await run_evaluation(
    dataset=dataset,
    analyzer=analyzer,
    scorers=[
        medical_accuracy_scorer,
        custom_risk_scorer  # カスタムスコアラー
    ]
)
```

### 参照データ（Ground Truth）の利用

```python
dataset = [
    {
        "input": "path/to/frame1.jpg",
        "reference_answer": {
            "step": "Dissection",
            "instruments": ["Maryland Grasper"],
            "risk": "Low"
        }
    }
]

# スコアラーで参照データを使用
@weave.op()
async def accuracy_with_ground_truth(model_output: dict, reference_answer: dict) -> dict:
    """Ground Truthと比較して精度を評価"""
    step_match = model_output.get("step") == reference_answer.get("step")
    return {"step_accuracy": 1.0 if step_match else 0.0}
```

---

## トラブルシューティング

### Evalsタブに結果が表示されない

**原因**:
- モデル関数が`@weave.op()`でデコレートされていない
- スコアラーのパラメータ名が`model_output`でない
- `weave.init()`が実行されていない

**解決策**:
```python
# ✅ 正しいパターン
@weave.op()
async def model_function(input: str) -> dict:
    return analyzer.analyze_frame(input)

@weave.op()
async def scorer(model_output: dict) -> dict:  # model_outputを使用
    return {"score": 5}
```

### APIキーのエラー

**症状**: `AZURE_OPENAI_API_KEY is not set!`

**解決策**:
```bash
# .envファイルを確認
cat .env

# 環境変数が読み込まれているか確認
uv run python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('AZURE_OPENAI_API_KEY'))"
```

### レイテンシーが高い

**原因**: Judge（Azure OpenAI）の呼び出しに時間がかかる

**解決策**:
- 評価するフレーム数を減らす
- スコアラーの数を減らす（必要最小限にする）
- より高速なJudgeモデルを使用（gpt-4o-miniなど）

### JSON解析エラー

**症状**: `Failed to parse JSON`

**原因**: Vision解析の出力がJSON形式でない、またはマークダウンで囲まれている

**確認方法**:
```python
# トレースログで生のレスポンスを確認
result = analyzer.analyze_frame(image_path)
print(result)
```

---

## ベストプラクティス

### 1. 段階的な評価

最初は**少数のフレーム**（2-3枚）で動作確認してから、徐々に増やす：

```python
# 開発時: 2フレーム
dataset = sequence[:2]

# テスト時: 10フレーム
dataset = sequence[:10]

# 本番評価: 全フレーム
dataset = sequence
```

### 2. メトリックの選択

すべてのスコアラーが必要とは限らない。タスクに応じて選択：

```python
# 基本評価: 正確性と合計のみ
scorers = [medical_accuracy_scorer, total_score_scorer]

# 詳細評価: 全5メトリック
scorers = [medical_accuracy_scorer, guideline_compliance_scorer,
           clarity_scorer, educational_value_scorer, total_score_scorer]
```

### 3. 継続的な改善

1. **ベースライン取得**: 初回評価でスコアを記録
2. **プロンプト改善**: Vision/Judge のプロンプトを調整
3. **再評価**: 同じデータセットで再度評価
4. **比較**: W&B Weave UIで改善度を確認

### 4. コスト管理

- Azure OpenAI (Judge) は**従量課金**
- 1フレーム = 1 Vision呼び出し + 5 Judge呼び出し（スコアラー数）
- 大規模評価前にコスト見積もりを確認

**概算**:
- Vision (SambaNova): 無料プラン内
- Judge (Azure OpenAI GPT-4o): ~$0.01/フレーム（5スコアラー）
- 100フレーム評価: 約$1

---

## 参考リソース

### 公式ドキュメント

- [W&B Weave Evaluations](https://docs.wandb.ai/weave/guides/core-types/evaluations)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [SambaNova Cloud](https://sambanova.ai/docs)

### 関連ファイル

- `backend/app/evaluation.py`: 評価システムの実装
- `backend/app/vision.py`: Vision解析の実装
- `backend/test_weave_evals.py`: 評価テストスクリプト
- `backend/test_weave_evals_fixed.py`: シンプルな評価例

### プロンプト

- **Vision System Prompt**: `app/vision.py` L13-22
- **Vision User Prompt**: `app/vision.py` L26-46
- **Judge System Prompt**: `app/evaluation.py` L11-24
- **Judge User Prompt Template**: `app/evaluation.py` L28-63

---

## まとめ

Surgical-Recapの評価システムは：

✅ **自動化**: 手動評価不要、スクリプト実行のみ
✅ **多面的**: 5つの観点から総合評価
✅ **トレーサブル**: W&B Weaveで全操作を追跡
✅ **改善可能**: プロンプト調整で継続的に精度向上
✅ **スケーラブル**: 数フレーム～数千フレームまで対応

これにより、**Vision解析の品質を客観的に測定し、継続的に改善**できます。

---

**作成日**: 2025年11月20日
**バージョン**: 1.0
**最終更新**: 2025年11月20日
