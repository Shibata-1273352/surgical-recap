# チャット機能 要件定義書

## 📋 概要

新人外科医が手術動画の解析結果について質問できる、AI搭載チャット機能。
SambaNova CloudのLLMを使用して高速回答を実現し、事前に生成された解析レポートを参照してRAG風の回答を提供する。

---

## 🎯 目的

- **新人教育の効率化**: 手術手技に関する疑問を即座に解消
- **高速な回答**: SambaNova Cloudによる低レイテンシー応答
- **コンテキスト参照**: 解析済みレポートを元にした正確な回答
- **既存機能への非侵襲**: 独立したモジュールとして実装

---

## 🏗️ アーキテクチャ

```
┌─────────────────────────────────────┐
│   Next.js 14 Frontend (App Router)  │
│   - TypeScript                       │
│   - Tailwind CSS + shadcn/ui        │
│   - Chat UI Component               │
└────────┬────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────┐
│       FastAPI (chat endpoints)       │
│  /api/chat/sessions                 │  ← 動画一覧取得
│  /api/chat/send                     │  ← メッセージ送信
└────────┬───────────────┬────────────┘
         │               │
         ↓               ↓
┌──────────────┐  ┌─────────────────┐
│  SambaNova   │  │ Analysis Report │
│  Cloud LLM   │  │   (Context)     │
└──────────────┘  └─────────────────┘
```

---

## 🚀 機能要件

### 1. 動画選択機能

#### 1.1 解析済み動画一覧の表示
- **エンドポイント**: `GET /api/chat/sessions`
- **機能**: 解析済みの動画リストを取得
- **レスポンス例**:
  ```json
  {
    "sessions": [
      {
        "session_id": "video01_20250121_1230",
        "video_id": "video01",
        "analyzed_at": "2025-01-21T12:30:00Z",
        "frame_count": 15,
        "summary": "胆嚢摘出術 - 15フレーム解析済み"
      }
    ]
  }
  ```

#### 1.2 動画選択UI
- ドロップダウンまたはリストで選択
- 各動画の基本情報（video_id, フレーム数, 日時）を表示
- 選択後、チャット画面に遷移

---

### 2. チャット機能

#### 2.1 メッセージ送信
- **エンドポイント**: `POST /api/chat/send`
- **リクエスト**:
  ```json
  {
    "session_id": "video01_20250121_1230",
    "message": "この手術でクリッピングはどの段階で行われましたか？",
    "history": [
      {"role": "user", "content": "この手術の概要を教えて"},
      {"role": "assistant", "content": "この手術は..."}
    ]
  }
  ```
- **レスポンス**:
  ```json
  {
    "reply": "クリッピングはフレーム8と9で行われました。具体的には...",
    "referenced_frames": [8, 9],
    "metadata": {
      "model": "Meta-Llama-3.1-70B-Instruct",
      "tokens": 150,
      "response_time_ms": 450
    }
  }
  ```

#### 2.2 会話履歴管理
- **保持方法**: メモリ内（セッション単位）
- **最大履歴数**: 直近10往復（20メッセージ）
- **永続化**: 暫定版では不要（将来的にDB保存も検討）

#### 2.3 チャットUI
- **必須要素**:
  - メッセージ入力ボックス
  - 送信ボタン
  - メッセージ履歴表示エリア
  - ユーザー/AIメッセージの区別表示
- **推奨要素**:
  - ローディングインジケーター
  - 参照フレーム番号の表示
  - エラーメッセージ表示

---

### 3. コンテキスト参照（RAG風）

#### 3.1 解析レポートの構造
- **保存場所**: メモリ内（`/api/vision/analyze-sequence`のレスポンス）
- **データ形式**:
  ```json
  {
    "session_id": "video01_20250121_1230",
    "video_id": "video01",
    "analysis_results": [
      {
        "frame_number": 1,
        "step": "Preparation",
        "instruments": ["Grasper", "Camera"],
        "risk": "Low",
        "description": "手術開始前の準備"
      }
    ]
  }
  ```

#### 3.2 コンテキスト注入方法
- 解析結果をJSON形式でシステムプロンプトに含める
- ユーザーの質問に関連するフレーム情報を抽出（暫定版では全件注入）
- 将来的には埋め込みベクトルによる類似検索を実装

#### 3.3 システムプロンプト
```
あなたは外科医の教育を支援する専門AIアシスタントです。
以下の手術動画解析結果を参照して、新人外科医の質問に答えてください。

【解析結果】
<解析結果のJSON>

【回答ルール】
1. 解析結果に基づいて正確に回答する
2. フレーム番号を明示的に言及する
3. 医学的に正確な用語を使用する
4. わからない場合は推測せず「不明」と答える
5. 日本語で回答する
6. 簡潔かつ教育的に説明する
```

---

## 🛠️ 技術仕様

### 1. バックエンド

#### 1.1 ディレクトリ構造
```
backend/app/chat/
├── __init__.py
├── REQUIREMENTS.md          # 本ドキュメント
├── models.py                # Pydanticモデル
├── service.py               # ビジネスロジック（SambaNova連携）
├── endpoints.py             # FastAPIルーター
├── prompts.py               # プロンプトテンプレート
└── session_manager.py       # セッション管理（メモリ内）
```

#### 1.2 使用ライブラリ
- **SambaNova SDK**: `sambanova` (既存)
- **FastAPI**: エンドポイント実装
- **Pydantic**: データバリデーション
- **Weave**: トレーシング（オプション）

#### 1.3 エンドポイント一覧

| Method | Endpoint                  | 説明                     | リクエスト | レスポンス |
|--------|---------------------------|--------------------------|-----------|-----------|
| GET    | `/api/chat/sessions`      | 解析済み動画一覧取得     | - | `SessionListResponse` |
| GET    | `/api/chat/session/{id}`  | 特定セッションの詳細取得 | - | `SessionDetailResponse` |
| POST   | `/api/chat/send`          | メッセージ送信           | `ChatRequest` | `ChatResponse` |
| DELETE | `/api/chat/session/{id}`  | セッション削除（オプション）| - | `DeleteResponse` |

#### 1.4 データモデル（models.py）

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = datetime.now()

class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: List[Message] = []

class ChatResponse(BaseModel):
    reply: str
    referenced_frames: List[int] = []
    metadata: dict

class SessionSummary(BaseModel):
    session_id: str
    video_id: str
    analyzed_at: datetime
    frame_count: int
    summary: str

class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]

class SessionDetailResponse(BaseModel):
    session_id: str
    video_id: str
    analysis_results: List[dict]
    created_at: datetime
```

---

### 2. フロントエンド

#### 2.1 技術スタック
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State Management**: React hooks (useState, useEffect)
- **API Client**: fetch API / axios

#### 2.2 ディレクトリ構造
```
frontend/
├── app/
│   ├── chat/
│   │   └── page.tsx              # チャット画面
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── chat/
│   │   ├── ChatInterface.tsx     # メインチャットコンポーネント
│   │   ├── ChatMessage.tsx       # メッセージ表示
│   │   ├── ChatInput.tsx         # 入力欄
│   │   └── VideoSelector.tsx     # 動画選択ドロップダウン
│   └── ui/                       # shadcn/ui components
│       ├── button.tsx
│       ├── card.tsx
│       ├── input.tsx
│       └── ...
├── lib/
│   ├── api.ts                    # API呼び出しロジック
│   └── types.ts                  # TypeScript型定義
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

#### 2.3 主要コンポーネント設計

**ChatInterface.tsx** (親コンポーネント)
```typescript
interface ChatInterfaceProps {}

export function ChatInterface() {
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  // API呼び出し、メッセージ管理
}
```

**ChatMessage.tsx** (メッセージ表示)
```typescript
interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  referencedFrames?: number[];
  timestamp: Date;
}
```

**VideoSelector.tsx** (動画選択)
```typescript
interface VideoSelectorProps {
  onSelect: (sessionId: string) => void;
}
```

---

## 📊 データフロー

### 1. 初期化フロー
```
1. ユーザー: アクセス
2. Frontend: GET /api/chat/sessions
3. Backend: 解析済みセッション一覧を返却
4. Frontend: ドロップダウンに表示
```

### 2. チャットフロー
```
1. ユーザー: 動画選択 + 質問入力
2. Frontend: POST /api/chat/send
   {
     "session_id": "...",
     "message": "...",
     "history": [...]
   }
3. Backend:
   a. セッション検証
   b. 解析結果取得（メモリから）
   c. システムプロンプト構築
   d. SambaNova API呼び出し
   e. レスポンス整形
4. Backend → Frontend: 回答返却
5. Frontend: チャット画面に表示
```

---

## 🔒 非機能要件

### 1. パフォーマンス
- **応答時間**: 平均500ms以内（SambaNova依存）
- **同時接続**: 最大10セッション（暫定版）

### 2. セキュリティ
- **API認証**: 暫定版では不要（将来的に実装）
- **入力検証**: Pydanticで実施
- **プロンプトインジェクション対策**: システムプロンプトの保護

### 3. エラーハンドリング
- SambaNova API障害時のフォールバック
- ネットワークエラーの適切な表示
- 不正なsession_idのエラー処理

---

## 🚧 制約事項・暫定仕様

### 1. RAG機能の簡略化
- **現状**: 全フレーム情報をコンテキストに注入
- **理由**: ハッカソン時間制約
- **将来改善**:
  - 埋め込みベクトル検索（FAISS, ChromaDB）
  - 関連フレームの動的選択
  - コンテキストウィンドウ最適化

### 2. セッション永続化の簡略化
- **現状**: メモリ内管理（サーバー再起動で消失）
- **理由**: DBセットアップ時間削減
- **データ構造**: Python辞書（session_id → analysis_results）
- **将来改善**: SQLite/PostgreSQLへの保存

### 3. 認証機能の省略
- **現状**: 認証なし（パブリックアクセス）
- **理由**: 認証機構の実装時間削減
- **将来改善**: 
  - JWT認証
  - ユーザー管理
  - セッションごとのアクセス制御

### 4. リアルタイム通信の不使用
- **現状**: HTTPポーリング（通常のREST API）
- **理由**: WebSocket実装の複雑性回避
- **将来改善**: Server-Sent Events or WebSocket

---

## 📅 実装スケジュール（目安）

| Phase | 作業内容 | 所要時間 |
|-------|---------|---------|
| **バックエンド** |
| 1 | models.py, prompts.py 実装 | 30分 |
| 2 | service.py 実装（SambaNova連携） | 30分 |
| 3 | endpoints.py 実装（FastAPIルーター） | 30分 |
| 4 | session_manager.py 実装 | 20分 |
| **フロントエンド** |
| 5 | Next.jsプロジェクトセットアップ | 20分 |
| 6 | shadcn/ui コンポーネント追加 | 15分 |
| 7 | API Client実装（lib/api.ts） | 20分 |
| 8 | ChatInterface コンポーネント実装 | 40分 |
| 9 | VideoSelector コンポーネント実装 | 20分 |
| 10 | スタイリング調整 | 30分 |
| **統合** |
| 11 | E2Eテスト | 30分 |
| 12 | デバッグ・調整 | 30分 |
| **合計** | | **約5時間** |

---

## ✅ 受け入れ基準

### 必須機能
- [ ] 解析済み動画を選択できる
- [ ] 選択した動画について質問できる
- [ ] SambaNova経由でAIが回答する
- [ ] 回答に解析結果が反映されている
- [ ] 会話履歴が保持される

### 推奨機能
- [ ] 参照したフレーム番号が表示される
- [ ] エラーメッセージが適切に表示される
- [ ] ローディング中の表示がある

---

## 🔮 将来の拡張計画

1. **ベクトル検索の実装**
   - FAISS or ChromaDBによる関連フレーム検索
   - 埋め込みモデル（sentence-transformers）

2. **マルチモーダル応答**
   - 参照フレーム画像の表示
   - タイムスタンプ付き動画リンク

3. **評価機能**
   - 回答の医学的正確性評価（W&B Weave）
   - ユーザーフィードバック収集

4. **永続化**
   - セッション履歴のDB保存
   - 過去の質問/回答の検索

5. **認証・認可**
   - ユーザー管理
   - アクセス権限制御

---

## 📚 参考資料

### 技術ドキュメント
- [Next.js 14 Documentation](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [SambaNova Cloud API Documentation](https://sambanova.ai/docs)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/)

### デザイン参考
- [Vercel AI Chatbot](https://github.com/vercel/ai-chatbot)
- [ChatGPT UI Clone](https://github.com/mckaywrigley/chatbot-ui)

### プロンプトエンジニアリング
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [OpenAI Best Practices](https://platform.openai.com/docs/guides/prompt-engineering)

---

## 📞 連絡先・質問

実装中の不明点や仕様変更は随時相談してください。

---

**作成日**: 2025-01-21  
**バージョン**: 1.0  
**ステータス**: 承認待ち
