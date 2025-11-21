#!/bin/bash
# Surgical-Recap 開発サーバー停止スクリプト

set -e

echo "🛑 Surgical-Recap 開発環境を停止します..."
echo ""

# プロジェクトルートディレクトリ
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"

# PIDファイルから停止
if [ -f "$LOG_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$LOG_DIR/backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "🔧 バックエンド (PID: $BACKEND_PID) を停止中..."
        kill $BACKEND_PID 2>/dev/null || true
    fi
    rm -f "$LOG_DIR/backend.pid"
fi

if [ -f "$LOG_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$LOG_DIR/frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "🎨 フロントエンド (PID: $FRONTEND_PID) を停止中..."
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    rm -f "$LOG_DIR/frontend.pid"
fi

# 念のため、プロセス名で検索して停止
echo "📋 残存プロセスをクリーンアップ中..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

sleep 2

echo ""
echo "✅ すべてのサービスが停止しました"
echo ""
