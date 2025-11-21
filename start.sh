#!/bin/bash
# Surgical-Recap 開発サーバー起動スクリプト

set -e

echo "🚀 Surgical-Recap 開発環境を起動します..."
echo ""

# プロジェクトルートディレクトリ
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ログディレクトリ
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 既存のプロセスを停止
echo "📋 既存のプロセスをクリーンアップ中..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 2

# バックエンド起動
echo "🔧 バックエンド (FastAPI) を起動中..."
cd "$PROJECT_ROOT/backend"
nohup uv run uvicorn app.main:app --reload --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   ✅ バックエンドPID: $BACKEND_PID"
echo "   📝 ログ: $LOG_DIR/backend.log"

# バックエンドの起動を待つ
echo "   ⏳ バックエンドの起動を待機中..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ バックエンド起動完了!"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "   ❌ バックエンドの起動に失敗しました"
        echo "   ログを確認してください: cat $LOG_DIR/backend.log"
        exit 1
    fi
    sleep 1
done

# フロントエンド起動
echo ""
echo "🎨 フロントエンド (Next.js) を起動中..."
cd "$PROJECT_ROOT/frontend"
nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "   ✅ フロントエンドPID: $FRONTEND_PID"
echo "   📝 ログ: $LOG_DIR/frontend.log"

# フロントエンドの起動を待つ
echo "   ⏳ フロントエンドの起動を待機中..."
for i in {1..20}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "   ✅ フロントエンド起動完了!"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "   ⚠️  フロントエンドの起動確認がタイムアウトしました"
        echo "   ログを確認してください: cat $LOG_DIR/frontend.log"
    fi
    sleep 1
done

# PIDを保存
echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"
echo "$FRONTEND_PID" > "$LOG_DIR/frontend.pid"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Surgical-Recap 開発環境が起動しました！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 アクセスURL:"
echo "   🎨 フロントエンド:     http://localhost:3000"
echo "   💬 チャット画面:       http://localhost:3000/chat"
echo "   🔧 バックエンドAPI:    http://localhost:8000"
echo "   📚 APIドキュメント:    http://localhost:8000/docs"
echo ""
echo "📋 プロセス情報:"
echo "   Backend PID:  $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "📝 ログファイル:"
echo "   Backend:  tail -f $LOG_DIR/backend.log"
echo "   Frontend: tail -f $LOG_DIR/frontend.log"
echo ""
echo "🛑 停止するには:"
echo "   $PROJECT_ROOT/stop.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
