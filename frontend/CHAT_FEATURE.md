# チャット機能ドキュメント

## 概要

Surgical-Recapプラットフォームに実装されたAIチャット機能のドキュメントです。解析済みの手術動画について、AIアシスタントに質問できる教育支援機能を提供します。

## 機能概要

### 主な機能

1. **動画プレビュー**
   - 解析済み動画の再生
   - 左側パネルでのリアルタイムプレビュー表示

2. **AIチャット**
   - SambaNova Cloud API統合
   - 日本語対応（Llama-3.3-Swallow-70B-Instruct-v0.4モデル使用）
   - 手術動画の解析結果に基づいた質問応答
   - 会話履歴の保持（最大10往復）

3. **セッション管理**
   - 複数の解析済み動画の切り替え
   - セッションごとの会話履歴管理

4. **参照フレーム表示**
   - AIが言及したフレーム番号の自動抽出
   - メッセージ内での参照フレーム表示

## アーキテクチャ

### 技術スタック

#### フロントエンド
- **フレームワーク**: Next.js 14 (App Router)
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS v4
- **UIコンポーネント**: shadcn/ui (Neutral theme)
  - Button, Card, Input, ScrollArea, Select

#### バックエンド
- **フレームワーク**: FastAPI
- **言語**: Python 3.12+
- **パッケージマネージャー**: uv
- **AI**: SambaNova Cloud API
- **モデル**: Llama-3.3-Swallow-70B-Instruct-v0.4

### ディレクトリ構造

```
surgical-recap/
├── backend/
│   └── app/
│       ├── chat/
│       │   ├── __init__.py          # モジュール初期化
│       │   ├── models.py            # Pydanticデータモデル
│       │   ├── prompts.py           # システムプロンプト
│       │   ├── session_manager.py   # セッション管理
│       │   ├── service.py           # ビジネスロジック
│       │   └── endpoints.py         # FastAPI エンドポイント
│       ├── upload/                   # 動画ファイル保存先
│       │   └── sample_masked_clipped.mp4
│       └── main.py                   # アプリケーションエントリポイント
│
└── frontend/
    └── src/
        ├── app/
        │   ├── chat/
        │   │   └── page.tsx          # チャットページコンポーネント
        │   └── globals.css            # グローバルスタイル
        ├── lib/
        │   ├── api.ts                 # APIクライアント
        │   └── types.ts               # TypeScript型定義
        └── components/ui/             # shadcn/uiコンポーネント
```

## バックエンド実装

### 1. データモデル (`models.py`)

```python
# 主要なモデル
- ChatRequest: チャットリクエスト（session_id, message, history）
- ChatResponse: チャット応答（reply, referenced_frames, metadata）
- SessionSummary: セッション概要
- SessionListResponse: セッション一覧レスポンス
- SessionDetailResponse: セッション詳細レスポンス
- AnalysisResult: フレーム解析結果
```

### 2. プロンプト管理 (`prompts.py`)

```python
# システムプロンプト
CHAT_SYSTEM_PROMPT = """
あなたは腹腔鏡下胆嚢摘出術の専門医として、
新人外科医の教育を支援するAIアシスタントです。
"""

# 主要な関数
- build_full_prompt(): 解析結果と会話履歴を統合
- extract_frame_references(): フレーム番号の抽出
```

### 3. セッション管理 (`session_manager.py`)

```python
class SessionManager:
    """スレッドセーフなメモリベースセッション管理"""
    
    # 主要なメソッド
    - create_session(): セッション作成
    - get_session(): セッション取得
    - get_all_sessions(): 全セッション取得
    - delete_session(): セッション削除
```

### 4. ビジネスロジック (`service.py`)

```python
class ChatService:
    """SambaNova APIとの統合"""
    
    # 設定
    model = "Llama-3.3-Swallow-70B-Instruct-v0.4"
    temperature = 0.7
    max_tokens = 512
    
    # 主要なメソッド
    - send_message(): メッセージ送信と応答生成
    - get_session_detail(): セッション詳細取得
```

### 5. APIエンドポイント (`endpoints.py`)

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/chat/sessions` | セッション一覧取得 |
| GET | `/api/chat/session/{session_id}` | セッション詳細取得 |
| POST | `/api/chat/send` | メッセージ送信 |
| DELETE | `/api/chat/session/{session_id}` | セッション削除 |
| GET | `/api/chat/health` | ヘルスチェック |

### 6. 動画配信 (`main.py`)

```python
# 静的ファイル配信
app.mount("/api/videos", StaticFiles(directory="app/upload"), name="videos")
```

## フロントエンド実装

### 1. 型定義 (`types.ts`)

```typescript
// 主要な型
interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface SessionSummary {
  session_id: string;
  video_id: string;
  analyzed_at: string;
  frame_count: number;
  summary: string;
}

interface ChatResponse {
  reply: string;
  referenced_frames: number[];
  metadata: {
    model: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    response_time_ms: number;
  };
}
```

### 2. APIクライアント (`api.ts`)

```typescript
// Next.jsプロキシ経由でアクセス
const API_BASE_URL = ""; // 相対パス

// 主要な関数
- getSessions(): セッション一覧取得
- getSessionDetail(): セッション詳細取得
- sendChatMessage(): メッセージ送信
- deleteSession(): セッション削除
```

### 3. チャットページ (`page.tsx`)

#### ステート管理

```typescript
const [sessions, setSessions] = useState<SessionSummary[]>([]);
const [selectedSessionId, setSelectedSessionId] = useState<string>("");
const [selectedVideoId, setSelectedVideoId] = useState<string>("");
const [videoError, setVideoError] = useState(false);
const [messages, setMessages] = useState<Message[]>([]);
const [inputMessage, setInputMessage] = useState("");
const [isLoading, setIsLoading] = useState(false);
const [error, setError] = useState<string>("");
```

#### 主要な機能

1. **自動スクロール**
```typescript
useEffect(() => {
  if (scrollAreaRef.current) {
    const scrollElement = scrollAreaRef.current.querySelector(
      '[data-radix-scroll-area-viewport]'
    );
    if (scrollElement) {
      scrollElement.scrollTop = scrollElement.scrollHeight;
    }
  }
}, [messages, isLoading]);
```

2. **メッセージ送信**
```typescript
const handleSendMessage = async () => {
  // ユーザーメッセージを追加
  // API呼び出し
  // アシスタント応答を追加
  // 参照フレームの表示
};
```

3. **セッション切り替え**
```typescript
const handleSessionChange = (newSessionId: string) => {
  setSelectedSessionId(newSessionId);
  setMessages([]);
  setError("");
  setVideoError(false);
  // video_idを更新
};
```

#### レイアウト構造

```tsx
<div className="container mx-auto max-w-6xl p-4 h-screen flex flex-col">
  {/* ヘッダー */}
  
  {/* 動画選択ドロップダウン */}
  
  {/* メインコンテンツ */}
  <div className="flex gap-4 flex-1 overflow-hidden">
    {/* 左: 動画プレビュー (1/3幅) */}
    <div className="w-1/3">
      <Card>
        <video src="/api/videos/{video_id}.mp4" />
      </Card>
    </div>
    
    {/* 右: チャットエリア (2/3幅) */}
    <div className="flex-1 flex flex-col gap-4">
      {/* メッセージ表示 (スクロール可能) */}
      <Card className="flex-1">
        <ScrollArea>
          {/* メッセージリスト */}
        </ScrollArea>
      </Card>
      
      {/* エラー表示 */}
      
      {/* 入力エリア */}
      <div className="flex gap-2">
        <Input />
        <Button />
      </div>
    </div>
  </div>
</div>
```

## 設定とセットアップ

### 環境変数

#### バックエンド (`.env`)
```bash
SAMBANOVA_API_KEY=your_api_key_here
```

#### フロントエンド (`.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Next.js設定 (`next.config.ts`)

```typescript
const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};
```

### グローバルCSS (`globals.css`)

```css
/* ScrollAreaの高さ設定 */
[data-radix-scroll-area-viewport] {
  max-height: 100%;
  height: 100%;
}
```

## 起動方法

### 統合起動スクリプト

```bash
# 起動
./start.sh

# 停止
./stop.sh
```

### 個別起動

#### バックエンド
```bash
cd backend
uv run uvicorn app.main:app --port 8000
```

#### フロントエンド
```bash
cd frontend
npm run dev
```

## アクセスURL

- **フロントエンド**: http://localhost:3000
- **チャット画面**: http://localhost:3000/chat
- **バックエンドAPI**: http://localhost:8000
- **APIドキュメント**: http://localhost:8000/docs

## デモセッション

起動時に自動的に4つのデモセッションが作成されます：

1. **sample_masked_clipped_demo** (9フレーム)
   - 実際の動画ファイルあり
   - 完全な解析データ

2. **demo_video_03_demo** (7フレーム)
   - 動画ファイルなし（解析データのみ）
   - Critical View of Safety含む

3. **demo_video_02_demo** (6フレーム)
   - 動画ファイルなし（解析データのみ）
   - Calot三角の剥離含む

4. **demo_video_01_demo** (5フレーム)
   - 動画ファイルなし（解析データのみ）
   - 基本的な胆嚢摘出術

## トラブルシューティング

### 動画が表示されない

**原因**: 動画ファイルが存在しない、または配信パスが間違っている

**解決策**:
1. `/api/videos/`パスでマウントされているか確認
2. `backend/app/upload/`に動画ファイルが存在するか確認
3. バックエンドログでリクエストを確認

### チャットメッセージが見切れる

**原因**: ScrollAreaの高さが正しく計算されていない

**解決策**:
1. `globals.css`にScrollArea用のスタイルが追加されているか確認
2. 親要素に`min-h-0`が設定されているか確認
3. ブラウザのキャッシュをクリア

### セッションが取得できない

**原因**: ポートフォワーディング環境でのCORS/プロキシ問題

**解決策**:
1. Next.jsの`rewrites`設定を確認
2. フロントエンドが正しいポート（3000）で起動しているか確認
3. バックエンドのCORS設定を確認

### APIキーエラー

**原因**: SambaNova APIキーが設定されていない

**解決策**:
1. `.env`ファイルに`SAMBANOVA_API_KEY`が設定されているか確認
2. 環境変数が正しく読み込まれているか確認
3. `/api/chat/health`エンドポイントで確認

## パフォーマンス

### レスポンス時間

- **Llama-3.3-Swallow-70B-Instruct-v0.4**: 平均1.8秒
- **会話履歴の影響**: トークン数により変動
- **最大トークン数**: 512トークン

### メモリ使用量

- **セッション管理**: メモリベース（再起動で消失）
- **会話履歴**: 最大10往復まで保持
- **動画ファイル**: ストリーミング配信（メモリに全体をロードしない）

## 今後の改善案

### 機能拡張

1. **データベース統合**
   - セッションの永続化
   - 会話履歴の保存

2. **フレーム表示機能**
   - 参照フレームのサムネイル表示
   - クリックで動画の該当位置にジャンプ

3. **エクスポート機能**
   - 会話履歴のPDF出力
   - 学習記録としての保存

4. **マルチモーダル対応**
   - フレーム画像の直接送信
   - 画像ベースの質問

### UI/UX改善

1. **メッセージのマークダウン対応**
2. **コードブロックのシンタックスハイライト**
3. **音声入力機能**
4. **リアルタイム翻訳**

### セキュリティ

1. **認証・認可の実装**
2. **レート制限**
3. **入力バリデーション強化**

## ライセンスと依存関係

### 主要な依存パッケージ

#### バックエンド
- fastapi >= 0.121.0
- uvicorn
- sambanova
- pydantic
- python-dotenv

#### フロントエンド
- next >= 16.0.3
- react >= 19.0.0
- typescript >= 5
- tailwindcss >= 4.0.0
- @radix-ui/react-scroll-area

## サポート

問題が発生した場合：

1. **ログの確認**
   ```bash
   tail -f logs/backend.log
   tail -f logs/frontend.log
   ```

2. **ヘルスチェック**
   ```bash
   curl http://localhost:8000/api/chat/health
   ```

3. **ブラウザ開発者ツール**
   - F12キーでコンソールとネットワークタブを確認

---

**作成日**: 2025-11-21  
**バージョン**: 1.0.0  
**最終更新**: 2025-11-21
