ハッカソンの短い期間内で、審査員に「おっ、本格的だ」と思わせるための**モダンかつ技術的に尖った要件定義書**を作成しました。

「見た目（Modern UI）」と「中身（SambaNova + vLLM）」のギャップで技術力をアピールする構成です。

---

# 要件定義書：Surgical-Recap (v1.0)

## 1. プロジェクト概要
*   **プロダクト名:** Surgical-Recap（サージカル・リキャップ）
*   **コンセプト:** 外科医の「技術継承」を加速する、AI搭載型の手術動画即時分析・教育プラットフォーム。
*   **ターゲット:**
    *   ユーザー：若手外科医（学びたい、特定の手技を探したい）
    *   管理者：ベテラン指導医（教育の手間を省きたい）
*   **コアバリュー:**
    *   **Immediate (即時性):** 手術直後に振り返りが可能（SambaNovaによる超高速解析）。
    *   **Granular (粒度):** 「結紮」「剥離」などの手技（アクション）単位での検索・再生。
    *   **Evidence (根拠):** ガイドラインに基づいたAI解説。

## 2. システムアーキテクチャ

ハッカソン評価軸の「Discovery（技術探求）」をアピールするため、クラウド（SambaNova）とオンプレ/ローカル（vLLM）を適材適所で組み合わせたハイブリッド構成とします。

### 2.1 技術スタック
*   **Frontend (Modern UI):**
    *   **Framework:** Next.js (App Router) + TypeScript
    *   **Styling:** Tailwind CSS + shadcn/ui (美しくモダンなコンポーネント群)
    *   **Video Player:** React Player (または Video.js)
*   **Backend (API):**
    *   **Framework:** FastAPI (Python) - 非同期処理と型安全性を重視
    *   **Data Store:** SQLite (メタデータ), FAISS or ChromaDB (ベクトル検索)
*   **AI / ML Logic:**
    *   **Vision Inference:** **SambaNova Cloud** (Llama 3.2 90B Vision)
        *   役割：動画フレームの超高速キャプション生成、状況理解。
    *   **Text Inference / RAG:** **vLLM** (自前サーバー or Colab上の Llama 3.1 70B/8B)
        *   役割：RAGの回答生成、医療ガイドラインとの照合。
        *   *※vLLMを採用する理由：ローカルでの高速推論技術への挑戦、およびSambaNovaとの役割分担を示すため。*
    *   **Evaluation:** **W&B Weave + Azure OpenAI (LLM as a Judge)**
        *   役割：AI生成コンテンツの品質評価と継続的改善。
        *   評価モデル：Azure OpenAI (GPT-4o)
        *   評価結果の記録：W&B Weaveを使用したトレーシングとメトリクス管理。

## 3. 機能要件 (Functional Requirements)

### 3.1 画像シーケンス解析 (Core)
*   **F-01 データセット読み込み:** cholecSeg8kデータセットから画像シーケンスを読み込む。
    *   画像をタイムスタンプ順に並べて擬似動画として扱う
    *   セグメンテーションマスクとラベル情報も同時に読み込み
*   **F-02 バッチ処理:** 画像シーケンスを効率的にバッチ処理する。
    *   複数フレームを並列でSambaNova APIに送信
    *   非同期処理でスループットを最大化
*   **F-03 高速シーン解析 (SambaNova):**
    *   各画像をSambaNova API (Llama 3.2 Vision) で解析し、以下のJSONを取得する。
    *   `{ "frame_id": 1234, "timestamp": "00:12:05", "action": "Clipping", "instruments": ["Clip applier"], "risk": "High", "description": "胆嚢管へのクリッピング" }`
    *   セグメンテーションマスク（Ground Truth）と比較して精度を評価
*   **F-04 ガイドライン照合 (vLLM + RAG):**
    *   解析されたアクションに対し、医学ガイドライン（事前にVector DB化）を検索し、手技のポイントを付与する。
*   **F-05 評価・検証:**
    *   データセットのラベルとVision解析結果を比較
    *   アクション認識精度、器具識別精度を算出
    *   W&B Weaveで評価結果をトラッキング

### 3.2 ダッシュボード・検索 (UI/UX)
*   **F-06 インタラクティブ・タイムライン:**
    *   画像シーケンスビューアの下に、手技ごとの「色分けされたバー」を表示する（例：赤=切開、青=縫合）。
    *   バーをクリックすると、該当フレームへ即座にジャンプする。
    *   画像のシーケンシャル再生機能（Play/Pause/速度調整）
*   **F-07 アクション検索:**
    *   検索窓に「結紮（けっさつ）」と入力すると、タイムライン上の該当箇所のみがハイライトされる。
    *   検索結果リストが表示され、クリックで該当フレームを表示。
*   **F-08 Ground Truth比較ビュー:**
    *   解析結果とデータセットのラベルを並べて表示
    *   セグメンテーションマスクのオーバーレイ表示

### 3.3 AI解説・チャット
*   **F-09 AIコメンタリー:**
    *   表示中のフレームに合わせて、画面横に「AIによる解説（このシーンの注意点）」と「ガイドラインの抜粋」を表示する。
*   **F-10 質疑応答:**
    *   「この時の剥離操作のコツは？」とチャットで聞くと、Llamaがガイドラインを参照して回答する。

## 4. 非機能要件 (Non-Functional Requirements)

*   **NF-01 パフォーマンス:** 画像シーケンス（1000フレーム）の解析を10分以内に完了させる（SambaNovaの超高速推論を活かす）。
    *   バッチ処理と並列化により、1フレームあたり平均0.6秒以内
*   **NF-02 UIデザイン:** 医療現場で使われることを意識した「ダークモード」基調のProfessionalな配色（黒・グレー・エメラルドグリーン）。
*   **NF-03 レスポンス:** 検索結果の表示は0.5秒以内。
*   **NF-04 精度:** Vision解析のアクション認識精度80%以上を目標（cholecSeg8kのGround Truthと比較）。

## 5. データ要件

### 5.1 画像データ: cholecSeg8k (Kaggle Dataset)

**データセット概要:**
*   **名称:** cholecSeg8k - Cholecystectomy Segmentation Dataset
*   **出典:** https://www.kaggle.com/datasets/newslab/cholecseg8k
*   **内容:** 腹腔鏡下胆嚢摘出術（Laparoscopic Cholecystectomy）のフレーム画像約8,000枚
*   **手術元:** Cholec80ビデオデータセットから抽出

**データ構成:**
*   **画像:** 手術のフレーム画像（PNG/JPG形式）
*   **セグメンテーションマスク:** 器具や解剖学的構造のピクセル単位のアノテーション
*   **ラベル情報:** 手術フェーズ、使用器具、アクションのアノテーション

**活用方法:**
*   画像シーケンスとして時系列順に並べ、擬似的な動画として使用
*   SambaNova Vision APIでフレームごとにアクション認識
*   セグメンテーションマスクを器具識別のGround Truthとして評価に使用
*   タイムライン機能のプロトタイプ検証用データとして活用

**ダウンロード方法:**
```bash
# Kaggle APIでダウンロード
pip install kaggle
kaggle datasets download -d newslab/cholecseg8k
unzip cholecseg8k.zip -d data/cholecseg8k
```

### 5.2 テキストデータ

*   **ガイドライン:** 腹腔鏡下胆嚢摘出術の標準ガイドラインテキスト（PDFから抽出）
*   **出典候補:**
    *   日本外科学会ガイドライン
    *   SAGES (Society of American Gastrointestinal and Endoscopic Surgeons) ガイドライン
*   **フォーマット:** テキスト形式（Markdown or Plain Text）
*   **用途:** RAGのVector DBに格納し、コンテキスト検索用として使用

### 5.3 プロンプトテンプレート

*   **Vision用:** 画像から医療器具とアクションを特定するSystem Prompt
*   **Text用:** 専門医の人格を模した回答生成Prompt
*   **Judge用:** LLM as a JudgeによるRAG回答評価Prompt

## 6. 開発スコープ・優先順位 (MoSCoW分析)

ハッカソン期間内での完遂を目指すための優先度です。

*   **Must (必須 - Day 1完了目標):**
    *   cholecSeg8kデータセットのダウンロードと前処理。
    *   SambaNovaによる画像シーケンス解析とJSON化。
    *   FastAPIによる解析結果のAPI提供。
    *   Next.jsによる画像シーケンスビューアとタイムライン表示（検索機能含む）。
*   **Should (推奨 - Day 2目標):**
    *   vLLMを用いたRAG（ガイドライン連携）。
    *   W&B Weave + Azure OpenAIによるLLM as a Judge評価システムの実装。
    *   UIのブラッシュアップ（shadcn/uiの適用）。
*   **Could (できれば):**
    *   AIチャットボット機能。
    *   ユーザーごとの学習履歴保存。

## 7. 評価システム (LLM as a Judge)

AI生成コンテンツの品質保証と継続的改善のため、LLM as a Judgeによる自動評価システムを実装します。

### 7.1 評価アーキテクチャ

*   **評価モデル:** Azure OpenAI (GPT-4o)
    *   高い推論能力による信頼性の高い評価
    *   構造化された出力による定量的な品質測定
*   **評価プラットフォーム:** W&B Weave
    *   LLM呼び出しの自動トレーシング
    *   評価メトリクスの時系列追跡
    *   プロンプトバージョン管理
    *   評価結果のダッシュボード可視化

### 7.2 評価対象と指標

#### 7.2.1 Vision解析の評価
*   **アクション認識精度:** 正解ラベルとの一致率
*   **器具識別精度:** 検出率と誤検出率
*   **記述の明確性:** 医師による1-5点評価（Judge LLMが代理評価）

#### 7.2.2 RAG回答の評価
*   **医学的正確性 (Medical Accuracy):** 1-5点
    *   医学的事実の正確さ
    *   専門用語の適切な使用
*   **ガイドライン準拠度 (Guideline Compliance):** 1-5点
    *   引用の正確さ
    *   推奨事項との整合性
*   **説明の明確さ (Clarity):** 1-5点
    *   論理的な構成
    *   理解しやすさ
*   **教育的価値 (Educational Value):** 1-5点
    *   学習効果
    *   実践的なアドバイスの有無

### 7.3 実装仕様

#### Judge Prompt Template

```python
JUDGE_SYSTEM_PROMPT = """
あなたは経験豊富な外科指導医として、AIが生成した手術解説の品質を評価します。

評価基準:
1. 医学的正確性 (1-5点): 医学的事実の正確さ、専門用語の適切な使用
2. ガイドライン準拠度 (1-5点): 標準ガイドラインとの整合性
3. 説明の明確さ (1-5点): 論理的な構成、理解しやすさ
4. 教育的価値 (1-5点): 若手医師への学習効果

各項目を公平に評価し、改善提案も含めてJSON形式で出力してください。
"""

JUDGE_USER_PROMPT = """
【評価対象の解説】
{ai_response}

【参考情報】
手術シーン: {action}
使用器具: {instruments}
参照ガイドライン: {guideline_context}

【専門医による模範解説】
{reference_answer}

上記の解説を評価してください。
"""
```

#### W&B Weave統合コード

```python
import weave
from openai import AzureOpenAI
import os

# Weave初期化
weave.init("surgical-recap")

# Azure OpenAI クライアント
judge_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-08-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

@weave.op()
def evaluate_rag_response(
    ai_response: str,
    action: str,
    instruments: list[str],
    guideline_context: str,
    reference_answer: str = None
) -> dict:
    """RAG回答をLLM as a Judgeで評価"""

    user_prompt = JUDGE_USER_PROMPT.format(
        ai_response=ai_response,
        action=action,
        instruments=", ".join(instruments),
        guideline_context=guideline_context,
        reference_answer=reference_answer or "（参考解説なし）"
    )

    response = judge_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    evaluation = json.loads(response.choices[0].message.content)

    # Weaveに自動記録される
    return {
        "medical_accuracy": evaluation["medical_accuracy"],
        "guideline_compliance": evaluation["guideline_compliance"],
        "clarity": evaluation["clarity"],
        "educational_value": evaluation["educational_value"],
        "total_score": sum([
            evaluation["medical_accuracy"],
            evaluation["guideline_compliance"],
            evaluation["clarity"],
            evaluation["educational_value"]
        ]),
        "feedback": evaluation.get("feedback", ""),
        "model": "gpt-4o",
        "timestamp": datetime.now().isoformat()
    }

@weave.op
def surgical_judge(action, explanation, context, reference_answer=None):
    """Weave Evaluation用のJudge関数

    注: weave.Evaluationのscorersとして使用するため、
    引数名は評価対象データのキーと一致させる必要がある
    """

    user_prompt = f"""【評価対象の解説】
{explanation}

【参考情報】
手術シーン: {action}
参照ガイドライン: {context}

【専門医による模範解説】
{reference_answer or "（参考解説なし）"}

上記の解説を評価してください。
"""

    response = judge_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    evaluation = json.loads(response.choices[0].message.content)

    return {
        "medical_accuracy": evaluation["medical_accuracy"],
        "guideline_compliance": evaluation["guideline_compliance"],
        "clarity": evaluation["clarity"],
        "educational_value": evaluation["educational_value"],
        "total_score": sum([
            evaluation["medical_accuracy"],
            evaluation["guideline_compliance"],
            evaluation["clarity"],
            evaluation["educational_value"]
        ]),
        "feedback": evaluation.get("feedback", "")
    }

# オフライン評価の実装（weave.Evaluation Framework）
test_cases = [
    {
        "action_data": {
            "timestamp": "00:12:05",
            "step": "Clipping",
            "instruments": ["Clip applier", "Grasper"],
            "risk": "High"
        },
        "user_question": "この手技のポイントと注意点を教えてください",
        "reference_answer": "クリップは管に対して垂直にかけることが推奨されます..."
    },
    {
        "action_data": {
            "timestamp": "00:08:30",
            "step": "Dissection",
            "instruments": ["Hook", "Grasper"],
            "risk": "Medium"
        },
        "user_question": "剥離のコツは何ですか",
        "reference_answer": "Calot三角の確実な同定が重要です..."
    }
]

# Weaveデータセット作成
dataset = weave.Dataset(rows=test_cases)

# 評価対象の関数を定義
@weave.op
def evaluate_single_case(action_data, user_question, reference_answer=None):
    """各テストケースを実行する関数

    この関数がweave.Evaluationによって各行に対して呼び出される
    """
    # RAGエージェントで解説を生成
    agent = SurgicalRAGAgent(vector_store=chroma_client)
    result = agent.generate_explanation(action_data, user_question)

    # Judgeに渡すためのフォーマット
    return {
        "action": action_data['step'],
        "explanation": result['explanation'],
        "context": result['context'],
        "reference_answer": reference_answer
    }

# 評価実行
evaluation = weave.Evaluation(
    dataset=dataset,
    scorers=[surgical_judge]  # Judge関数をリストで渡す
)

# 評価を実行（非同期）
import asyncio
results = await evaluation.evaluate(evaluate_single_case)

# 結果の確認
print(f"Average Medical Accuracy: {results['surgical_judge']['medical_accuracy']['mean']}")
print(f"Average Guideline Compliance: {results['surgical_judge']['guideline_compliance']['mean']}")
print(f"Average Clarity: {results['surgical_judge']['clarity']['mean']}")
print(f"Average Educational Value: {results['surgical_judge']['educational_value']['mean']}")
print(f"Average Total Score: {results['surgical_judge']['total_score']['mean']}")
```

### 7.4 評価フロー

1. **開発時評価:**
   - プロンプト変更ごとにテストセット（10-20件）で評価
   - Weaveダッシュボードでスコア推移を確認
   - 平均スコア4.0以上を目標

2. **本番モニタリング:**
   - ユーザーからの質問に対する回答を自動評価
   - スコアが3.0未満の場合はアラート
   - 週次でスコア傾向をレビュー

3. **継続的改善:**
   - 低スコア回答の分析
   - プロンプト改善
   - ガイドラインDBの拡充

### 7.5 環境変数の追加

`.env` ファイルに以下を追加:

```env
# Azure OpenAI (Judge用)
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# W&B Weave
WANDB_API_KEY=your_wandb_api_key
WANDB_PROJECT=surgical-recap
```

### 7.6 依存関係の追加

```bash
# Backend
cd backend
uv add weave openai numpy python-dotenv

# Weaveは自動的にW&Bの依存関係も含む
# openaiパッケージはAzure OpenAI、SambaNova、vLLM（OpenAI互換）すべてで使用可能
```

**注意**: `openai`パッケージ（バージョン1.0以降）は、Azure OpenAIもサポートしています。

---

### チームへの共有事項

この構成で進める場合、以下の役割分担がスムーズです。

1.  **Frontend Engineer (Next.js):**
    *   画面作成。「Video Player」と「Timeline」の連携コンポーネントが肝になります。
2.  **Backend/AI Engineer (FastAPI + SambaNova):**
    *   API構築。画像をSambaNovaに投げてJSONを受け取る処理の実装。
3.  **Infra/ML Engineer (vLLM + RAG):**
    *   vLLMの環境構築（ColabなどでAPI化してFastAPIから叩く形が手軽です）、Vector DBの準備。

---
ハッカソンのスピード感に対応しつつ、技術的なこだわり（Discovery）を見せるための、**`uv` を中心としたモダンな開発環境構築手順**をまとめました。

この構成なら、チームメンバーはリポジトリをクローンして**スクリプトを1回叩くだけで、Back/Front/DB/Envが一発で立ち上がります。**

---

### 📂 ディレクトリ構成 (Monorepo構成)

プロジェクトルートにBackendとFrontendを同居させます。

```text
surgical-recap/
├── backend/             # FastAPI + uv
│   ├── app/             # アプリケーションコード
│   ├── .venv/           # uvが管理する仮想環境
│   ├── pyproject.toml   # 依存関係定義
│   └── uv.lock
├── frontend/            # Next.js + shadcn/ui
│   ├── src/
│   └── package.json
├── .env                 # 共通環境変数 (SambaNova API Keyなど)
└── dev.sh               # ★魔法の起動スクリプト
```

---

### 🚀 1. Backend セットアップ (uv + FastAPI)

Pythonのパッケージ管理には、Rust製の爆速ツール `uv` を使用します。

**ターミナル操作:**
```bash
# 1. プロジェクト作成 & backendへ移動
mkdir surgical-recap && cd surgical-recap
mkdir backend && cd backend

# 2. uvの初期化 (Python 3.12推奨)
uv init --python 3.12
# もしuvが入っていなければ: curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 依存関係の追加 (SambaNova/vLLM用にopenai互換ライブラリを使用)
uv add fastapi uvicorn[standard] python-multipart python-dotenv openai wandb chromadb
```

**`backend/app/main.py` (動作確認用スケルトン):**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Surgical-Recap API")

# フロントエンド(Next.js)からのアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "engine": "SambaNova + vLLM", "backend": "FastAPI with uv"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

---

### 🎨 2. Frontend セットアップ (Next.js + shadcn/ui)

**ターミナル操作 (ルートディレクトリに戻って実行):**
```bash
cd .. # surgical-recap/ に戻る

# 1. Next.js アプリ作成 (TypeScript, Tailwind, ESLint 全部Yesで)
npx create-next-app@latest frontend --typescript --tailwind --eslint
# 設定を聞かれたら:
# Would you like to use `src/` directory? -> Yes
# Would you like to use App Router? -> Yes
# Would you like to customize the default import alias? -> No

# 2. shadcn/ui (モダンUIコンポーネント) の初期化
cd frontend
npx shadcn@latest init
# Style: New York, Base color: Zinc, CSS var: Yes

# 3. 必要なコンポーネントとアイコンを入れる
npx shadcn@latest add button input card slider
npm install lucide-react react-player axios
```

---

### ⚡ 3. 一括起動スクリプト (`dev.sh`)

これが今回の肝です。BackendとFrontendを並列起動し、Ctrl+Cで綺麗に終了させるシェルスクリプトを作成します。

**ルートディレクトリに `dev.sh` を作成:**

```bash
#!/bin/bash

# 色の定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Surgical-Recap Development Environment ===${NC}"

# 終了時の処理 (Ctrl+Cを押したときに子プロセスも殺す)
trap 'kill 0' SIGINT

# .envの読み込みチェック
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating a template..."
    echo "SAMBANOVA_API_KEY=your_key_here" > .env
fi

# 1. Backendの起動 (uv run)
echo -e "${GREEN}🚀 Starting Backend (FastAPI + uv)...${NC}"
cd backend
# ポート8000で起動, リロードモード有効
uv run uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# 2. Frontendの起動 (Next.js)
echo -e "${GREEN}🎨 Starting Frontend (Next.js)...${NC}"
cd frontend
# 依存関係がなければインストール
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
# ポート3000で起動
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "${BLUE}=== System is Running ===${NC}"
echo -e "Backend: http://localhost:8000/docs"
echo -e "Frontend: http://localhost:3000"

# プロセスが終了するのを待つ
wait
```

**実行権限を付与:**
```bash
chmod +x dev.sh
```

---

### 🚀 開発の始め方

チームメンバーには以下の手順を共有してください。

1.  **リポジトリをClone**
2.  **uv をインストール** (入ってなければ)
3.  **ルートで `./dev.sh` を叩く**

これだけで、
*   Backendの仮想環境作成 (`uv sync`)
*   Frontendの `node_modules` インストール
*   両方のサーバー起動
*   ホットリロード環境

が全て整います。

#### 補足: `.env` ファイル
ルートディレクトリに `.env` を作成し、APIキーを一元管理します。

```env
# SambaNova (Vision Inference)
SAMBANOVA_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# W&B Weave (Evaluation Tracking)
WANDB_API_KEY=xxxxxxxxxxxxxxxxxxxxxx
WANDB_PROJECT=surgical-recap

# Azure OpenAI (LLM as a Judge)
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# vLLM (RAG Text Inference)
VLLM_API_BASE=http://localhost:8080/v1
```
`backend/app/main.py` 内で `os.getenv("SAMBANOVA_API_KEY")` として読み込めます。

この構成なら、ハッカソン当日に「環境構築でハマって半日終わった...」という悲劇を防げます！