# チャット機能 - クイックスタート

## 概要

手術動画の解析結果について、AIアシスタント（Llama-3.3-Swallow-70B-Instruct-v0.4）に質問できる教育支援機能です。

## 起動方法

```bash
# プロジェクトルートで実行
./start.sh

# アクセス
open http://localhost:3000/chat
```

## 主な機能

✅ 動画プレビュー（左側パネル）  
✅ AIチャット（右側パネル）  
✅ 自動スクロール  
✅ 参照フレーム表示  
✅ 会話履歴管理（最大10往復）  

## 使い方

1. **動画を選択**: ドロップダウンから解析済み動画を選択
2. **質問を入力**: 下部の入力欄に質問を入力
3. **送信**: Enterキーまたは送信ボタンをクリック
4. **回答を確認**: AIアシスタントからの回答が表示されます

## 例：質問例

```
- この手術の最初のステップは何ですか？
- クリッピングはどの段階で行われましたか？
- 重要なステップを教えてください
- フレーム30では何が行われていますか？
```

## 技術スタック

### フロントエンド
- Next.js 14 + TypeScript
- Tailwind CSS v4 + shadcn/ui

### バックエンド
- FastAPI + Python 3.12+
- SambaNova Cloud API
- Llama-3.3-Swallow-70B-Instruct-v0.4

## ファイル構成

```
backend/app/chat/
├── models.py           # データモデル
├── prompts.py          # システムプロンプト
├── session_manager.py  # セッション管理
├── service.py          # ビジネスロジック
└── endpoints.py        # APIエンドポイント

frontend/src/
├── app/chat/page.tsx   # チャット画面
├── lib/api.ts          # APIクライアント
└── lib/types.ts        # 型定義
```

## APIエンドポイント

| エンドポイント | 説明 |
|--------------|------|
| `GET /api/chat/sessions` | セッション一覧 |
| `GET /api/chat/session/{id}` | セッション詳細 |
| `POST /api/chat/send` | メッセージ送信 |
| `GET /api/chat/health` | ヘルスチェック |
| `GET /api/videos/{video_id}.mp4` | 動画配信 |

## 環境変数

### backend/.env
```bash
SAMBANOVA_API_KEY=your_api_key_here
```

### frontend/.env.local
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## トラブルシューティング

### 動画が表示されない
→ `sample_masked_clipped`を選択してください（実際の動画ファイルあり）

### チャットが見切れる
→ ブラウザをリフレッシュしてください

### セッションが取得できない
→ バックエンドが起動しているか確認: `curl http://localhost:8000/api/chat/health`

## ログ確認

```bash
# バックエンド
tail -f logs/backend.log

# フロントエンド
tail -f logs/frontend.log
```

## 停止方法

```bash
./stop.sh
```

---

詳細なドキュメント: [CHAT_FEATURE.md](./CHAT_FEATURE.md)
