"use client";

import { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getSessions, sendChatMessage } from "@/lib/api";
import type { Message, SessionSummary } from "@/lib/types";

export default function ChatPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string>("");
  const [selectedVideoId, setSelectedVideoId] = useState<string>("");
  const [videoError, setVideoError] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // セッション一覧を取得
  useEffect(() => {
    async function fetchSessions() {
      try {
        console.log("Fetching sessions...");
        const response = await getSessions();
        console.log("Sessions response:", response);
        setSessions(response.sessions);
        // 最初のセッションを自動選択
        if (response.sessions.length > 0) {
          setSelectedSessionId(response.sessions[0].session_id);
          setSelectedVideoId(response.sessions[0].video_id);
          console.log("Selected session:", response.sessions[0].session_id);
        }
      } catch (err) {
        setError("セッション一覧の取得に失敗しました");
        console.error("Error fetching sessions:", err);
      }
    }
    fetchSessions();
  }, []);

  // メッセージが更新されたらスクロール
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages, isLoading]);

  // メッセージ送信
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !selectedSessionId) return;

    const userMessage: Message = {
      role: "user",
      content: inputMessage,
      timestamp: new Date().toISOString(),
    };

    // ユーザーメッセージを追加
    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);
    setError("");

    try {
      // API呼び出し
      const response = await sendChatMessage({
        session_id: selectedSessionId,
        message: inputMessage,
        history: messages,
      });

      // アシスタントの回答を追加
      const assistantMessage: Message = {
        role: "assistant",
        content: response.reply,
        timestamp: new Date().toISOString(),
      };

      // 参照フレームがあれば表示
      if (response.referenced_frames.length > 0) {
        assistantMessage.content += `\n\n📌 参照フレーム: ${response.referenced_frames.join(", ")}`;
      }

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "メッセージ送信に失敗しました"
      );
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // セッション変更時にメッセージをクリア
  const handleSessionChange = (newSessionId: string) => {
    setSelectedSessionId(newSessionId);
    setMessages([]);
    setError("");
    setVideoError(false);
    
    // 選択されたセッションのvideo_idを取得
    const session = sessions.find(s => s.session_id === newSessionId);
    if (session) {
      setSelectedVideoId(session.video_id);
    }
  };

  // Enterキーで送信
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="container mx-auto max-w-6xl p-4 h-screen flex flex-col">
      <div className="mb-4">
        <h1 className="text-3xl font-bold mb-2">🩺 外科医教育チャット</h1>
        <p className="text-muted-foreground">
          手術動画の解析結果について質問してください
        </p>
      </div>

      {/* 動画選択 */}
      <div className="mb-4">
        <div className="text-sm text-gray-500 mb-2">
          読み込まれたセッション数: {sessions.length} | 選択中: {selectedSessionId}
        </div>
        <Select value={selectedSessionId} onValueChange={handleSessionChange}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="解析済み動画を選択" />
          </SelectTrigger>
          <SelectContent>
            {sessions.map((session) => (
              <SelectItem key={session.session_id} value={session.session_id}>
                {session.summary}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* メインコンテンツエリア */}
      <div className="flex gap-4 flex-1 overflow-hidden">
        {/* 左側：動画プレビュー */}
        <div className="w-1/3">
          <Card className="h-full flex flex-col">
            <div className="p-4 border-b">
              <h2 className="font-semibold">📹 動画プレビュー</h2>
            </div>
            <div className="flex-1 p-4 flex items-center justify-center bg-black">
              {selectedVideoId ? (
                videoError ? (
                  <div className="text-gray-400 text-center p-4">
                    <p className="text-yellow-400 mb-2">⚠️ 動画が見つかりません</p>
                    <p className="text-sm">
                      video_id: {selectedVideoId}
                    </p>
                    <p className="text-xs mt-2">
                      解析データは利用可能です
                    </p>
                  </div>
                ) : (
                  <video
                    key={selectedVideoId}
                    controls
                    className="w-full h-full object-contain"
                    src={`/api/videos/${selectedVideoId}.mp4`}
                    onError={() => setVideoError(true)}
                  >
                    お使いのブラウザは動画タグをサポートしていません。
                  </video>
                )
              ) : (
                <div className="text-gray-400 text-center">
                  <p>動画を選択してください</p>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* 右側：チャットエリア */}
        <div className="flex-1 flex flex-col min-h-0 gap-4">
          {/* チャットメッセージエリア */}
          <Card className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="flex-1 overflow-hidden">
              <ScrollArea
                className="h-full w-full p-4"
                ref={scrollAreaRef as React.RefObject<HTMLDivElement>}
              >
                {messages.length === 0 ? (
                  <div className="text-center text-muted-foreground py-8">
                    <p>動画を選択して質問を始めてください</p>
                    <p className="text-sm mt-2">
                      例: 「クリッピングはどの段階で行われましたか？」
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex ${
                          msg.role === "user" ? "justify-end" : "justify-start"
                        }`}
                      >
                        <div
                          className={`max-w-[80%] rounded-lg px-4 py-2 ${
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted"
                          }`}
                        >
                          <div className="text-sm font-semibold mb-1">
                            {msg.role === "user" ? "新人外科医" : "AIアシスタント"}
                          </div>
                          <div className="whitespace-pre-wrap">{msg.content}</div>
                        </div>
                      </div>
                    ))}
                    {isLoading && (
                      <div className="flex justify-start">
                        <div className="bg-muted rounded-lg px-4 py-2">
                          <div className="text-sm font-semibold mb-1">
                            AIアシスタント
                          </div>
                          <div className="flex gap-1">
                            <span className="animate-bounce">●</span>
                            <span className="animate-bounce delay-100">●</span>
                            <span className="animate-bounce delay-200">●</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </ScrollArea>
            </div>
          </Card>

          {/* エラー表示 */}
          {error && (
            <div className="p-3 bg-destructive/10 text-destructive rounded-lg">
              {error}
            </div>
          )}

          {/* 入力エリア */}
          <div className="flex gap-2">
            <Input
              placeholder="質問を入力..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading || !selectedSessionId}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={isLoading || !inputMessage.trim() || !selectedSessionId}
            >
              {isLoading ? "送信中..." : "送信"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
