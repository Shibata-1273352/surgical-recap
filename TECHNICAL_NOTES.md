# チャット機能 - 技術的課題と解決策

このドキュメントは、チャット機能実装時に直面した技術的課題とその解決策をまとめたものです。

## 目次

1. [ポートフォワーディング環境でのAPI接続問題](#1-ポートフォワーディング環境でのapi接続問題)
2. [動画ファイル配信の設定](#2-動画ファイル配信の設定)
3. [ScrollAreaのインナースクロール実装](#3-scrollareaのインナースクロール実装)
4. [SambaNovaモデルの変更](#4-sambanοvaモデルの変更)

---

## 1. ポートフォワーディング環境でのAPI接続問題

### 問題

ポートフォワーディング環境では、フロントエンド（localhost:46851）からバックエンド（localhost:8000）への直接接続ができず、セッションが取得できない。

```typescript
// ❌ 動作しない
const API_BASE_URL = "http://localhost:8000";
```

### 原因

- ポートフォワーディングではフロントエンドが異なるポート（46851など）で動作
- ブラウザから直接localhost:8000にアクセスできない
- CORSの問題も発生

### 解決策

Next.jsの**rewrite機能**を使用してAPIプロキシを実装。

#### 1. Next.js設定 (`next.config.ts`)

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

#### 2. APIクライアント (`api.ts`)

```typescript
// ✅ 相対パスで呼び出し
const API_BASE_URL = "";

export async function getSessions() {
  const response = await fetch(`${API_BASE_URL}/api/chat/sessions`);
  return response.json();
}
```

### 結果

- フロントエンドの`/api/*`へのリクエストが自動的にバックエンドにプロキシされる
- ポートフォワーディング環境でも正常に動作
- CORS問題も解決

---

## 2. 動画ファイル配信の設定

### 問題

動画プレビューエリアは表示されるが、動画ファイルが読み込まれない。

```
GET /api/videos/sample_masked_clipped.mp4 → 404 Not Found
```

### 原因分析

1. **初期の実装**: `/videos`パスでマウント
   ```python
   app.mount("/videos", StaticFiles(directory=upload_dir), name="videos")
   ```

2. **フロントエンドのリクエスト**: `/api/videos/`
   ```typescript
   <video src="/api/videos/sample_masked_clipped.mp4" />
   ```

3. **パスの不一致**: `/videos` ≠ `/api/videos`

### 解決策

バックエンドのマウントパスを変更。

```python
# backend/app/main.py
from fastapi.staticfiles import StaticFiles

upload_dir = Path(__file__).parent / "upload"
if upload_dir.exists():
    app.mount("/api/videos", StaticFiles(directory=str(upload_dir)), name="videos")
```

### 検証

```bash
# ✅ 正常に動作
curl -I http://localhost:8000/api/videos/sample_masked_clipped.mp4

HTTP/1.1 200 OK
content-type: video/mp4
content-length: 225563911
```

### ポイント

- FastAPIの`StaticFiles`を使用すると、自動的にRange requestに対応
- 動画の部分読み込み（206 Partial Content）が可能
- 大きな動画ファイルでも効率的に配信

---

## 3. ScrollAreaのインナースクロール実装

### 問題

チャットメッセージが増えると、2件目以降が見切れてしまい、スクロールできない。

### 原因

1. **Flexboxの高さ計算問題**
   - `flex-1`だけでは親の高さ制約が効かない
   - ScrollAreaが無限に拡張してしまう

2. **Radix UIのScrollArea構造**
   ```html
   <ScrollArea>
     <div data-radix-scroll-area-viewport>
       <!-- コンテンツ -->
     </div>
   </ScrollArea>
   ```

### 解決策

#### 1. Flexboxの高さ制約を追加

```tsx
{/* ❌ 動作しない */}
<div className="flex-1 flex flex-col">
  <Card className="flex-1">
    <ScrollArea className="flex-1">
      {/* コンテンツ */}
    </ScrollArea>
  </Card>
</div>

{/* ✅ 正しい実装 */}
<div className="flex-1 flex flex-col min-h-0 gap-4">
  <Card className="flex-1 flex flex-col min-h-0">
    <div className="flex-1 overflow-hidden">
      <ScrollArea className="h-full w-full">
        {/* コンテンツ */}
      </ScrollArea>
    </div>
  </Card>
</div>
```

**重要なポイント**:
- `min-h-0`: Flexboxの高さ計算を正しく機能させる
- `overflow-hidden`: ScrollAreaの親要素で高さ制約を強制
- `h-full`: ScrollArea自体は親要素の100%の高さ

#### 2. グローバルCSSでviewportの高さを設定

```css
/* frontend/src/app/globals.css */
[data-radix-scroll-area-viewport] {
  max-height: 100%;
  height: 100%;
}
```

#### 3. 自動スクロール機能

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

### 結果

- ✅ メッセージが増えてもスクロール可能
- ✅ 新しいメッセージが追加されると自動的に最下部にスクロール
- ✅ すべての会話履歴を確認できる

---

## 4. SambaNovaモデルの変更

### 要件

デフォルトの`Meta-Llama-3.1-8B-Instruct`から、日本語に特化した`Llama-3.3-Swallow-70B-Instruct-v0.4`に変更したい。

### 実装

#### backend/app/chat/service.py

```python
class ChatService:
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "Llama-3.3-Swallow-70B-Instruct-v0.4"  # ← 変更
    ):
        self.api_key = api_key or os.getenv("SAMBANOVA_API_KEY")
        self.model = model
        self.session_manager = get_session_manager()
        
        if not self.api_key:
            raise ValueError("SAMBANOVA_API_KEY is not set")
        
        self.client = SambaNova(api_key=self.api_key)
```

### 検証

```bash
# ヘルスチェックで確認
curl http://localhost:8000/api/chat/health | jq

{
  "status": "ok",
  "service": "chat",
  "model": "Llama-3.3-Swallow-70B-Instruct-v0.4"
}
```

### パフォーマンス比較

| モデル | 平均レスポンス時間 | 日本語品質 |
|--------|------------------|-----------|
| Meta-Llama-3.1-8B-Instruct | ~650ms | 普通 |
| Llama-3.3-Swallow-70B-Instruct-v0.4 | ~1800ms | 優秀 |

### 結果

- ✅ 日本語の回答品質が大幅に向上
- ✅ 医療用語の理解が改善
- ⚠️ レスポンス時間は約3倍に増加（許容範囲内）

---

## ベストプラクティス

### 1. ポートフォワーディング環境でのAPI設計

```typescript
// ❌ 避けるべき
const API_URL = "http://localhost:8000";

// ✅ 推奨: Next.jsのrewrite + 相対パス
const API_URL = "";
```

### 2. Flexboxとスクロールエリアの組み合わせ

```tsx
// ✅ 重要な3点セット
<div className="flex-1 min-h-0 overflow-hidden">
  <ScrollArea className="h-full">
    {/* コンテンツ */}
  </ScrollArea>
</div>
```

### 3. 動画配信のパス設計

```python
# バックエンド: Next.jsのrewriteルールに合わせる
app.mount("/api/videos", StaticFiles(...))

# フロントエンド: 相対パスで参照
<video src="/api/videos/sample.mp4" />
```

### 4. 環境に依存しない設計

```typescript
// ✅ 環境変数 + デフォルト値
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

// ✅ プロキシを活用
// next.config.ts でrewriteルールを設定
```

---

## まとめ

### 重要な学び

1. **ポートフォワーディング環境ではプロキシが必須**
   - Next.jsのrewrite機能を活用
   - 相対パスでAPI呼び出し

2. **Flexboxとスクロールの組み合わせは要注意**
   - `min-h-0`で高さ制約を有効化
   - `overflow-hidden`で親要素の高さを強制
   - Radix UIの内部構造を理解する

3. **動画配信はパス設計が重要**
   - フロントエンドとバックエンドのパスを一致させる
   - StaticFilesは自動的にRange requestに対応

4. **モデル選択はユースケースに応じて**
   - 日本語品質を優先 → Swallow-70B
   - レスポンス速度を優先 → Llama-8B

---

**作成日**: 2025-11-21  
**バージョン**: 1.0.0
