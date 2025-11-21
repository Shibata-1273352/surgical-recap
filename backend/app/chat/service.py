"""
チャットサービスロジック

SambaNova Cloud APIとの連携、メッセージ処理
"""

import os
import time
from typing import Dict, List, Optional, Any
from sambanova import SambaNova

from .prompts import build_full_prompt, extract_frame_references
from .session_manager import get_session_manager


class ChatService:
    """
    チャット機能のビジネスロジック
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "Llama-3.3-Swallow-70B-Instruct-v0.4"):
        """
        初期化
        
        Args:
            api_key: SambaNova APIキー（Noneの場合は環境変数から取得）
            model: 使用するモデル名
        """
        self.api_key = api_key or os.getenv("SAMBANOVA_API_KEY")
        self.model = model
        self.session_manager = get_session_manager()
        
        if not self.api_key:
            raise ValueError("SAMBANOVA_API_KEY is not set")
        
        self.client = SambaNova(api_key=self.api_key)
    
    def send_message(
        self,
        session_id: str,
        message: str,
        history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        メッセージを送信してAIから回答を取得
        
        Args:
            session_id: セッションID
            message: ユーザーのメッセージ
            history: 会話履歴
            
        Returns:
            回答とメタデータを含む辞書
            
        Raises:
            ValueError: セッションが存在しない場合
        """
        # セッション存在チェック
        if not self.session_manager.session_exists(session_id):
            raise ValueError(f"Session {session_id} not found")
        
        # 解析結果を取得
        analysis_results = self.session_manager.get_analysis_results(session_id)
        if not analysis_results:
            raise ValueError(f"No analysis results found for session {session_id}")
        
        # プロンプト構築
        system_prompt, user_prompt = build_full_prompt(
            analysis_results=analysis_results,
            user_message=message,
            history=history or []
        )
        
        # SambaNova APIを呼び出し
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=512
            )
            
            # 応答を取得
            reply = response.choices[0].message.content
            
            # 使用トークン数
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0
            
        except Exception as e:
            raise RuntimeError(f"SambaNova API error: {str(e)}")
        
        # 応答時間計算
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 参照フレーム抽出
        referenced_frames = extract_frame_references(reply, analysis_results)
        
        # メタデータ構築
        metadata = {
            "model": self.model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "response_time_ms": response_time_ms
        }
        
        return {
            "reply": reply,
            "referenced_frames": referenced_frames,
            "metadata": metadata
        }
    
    def get_sessions(self) -> List[Dict[str, Any]]:
        """
        全セッションの概要を取得
        
        Returns:
            セッション概要のリスト
        """
        return self.session_manager.get_session_summaries()
    
    def get_session_detail(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッションの詳細を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            セッション詳細（存在しない場合はNone）
        """
        return self.session_manager.get_session(session_id)
    
    def create_session_from_analysis(
        self,
        session_id: str,
        video_id: str,
        analysis_results: List[Dict[str, Any]]
    ) -> bool:
        """
        解析結果からセッションを作成
        
        Args:
            session_id: セッションID
            video_id: 動画ID
            analysis_results: 解析結果
            
        Returns:
            作成成功ならTrue
        """
        return self.session_manager.create_session(
            session_id=session_id,
            video_id=video_id,
            analysis_results=analysis_results
        )
    
    def delete_session(self, session_id: str) -> bool:
        """
        セッションを削除
        
        Args:
            session_id: セッションID
            
        Returns:
            削除成功ならTrue
        """
        return self.session_manager.delete_session(session_id)


# グローバルインスタンス（遅延初期化）
_chat_service: Optional[ChatService] = None


def get_chat_service() -> Optional[ChatService]:
    """
    ChatServiceのグローバルインスタンスを取得
    
    Returns:
        ChatServiceインスタンス（APIキーが設定されていない場合はNone）
    """
    global _chat_service
    
    if _chat_service is None:
        try:
            _chat_service = ChatService()
        except ValueError:
            # APIキーが設定されていない
            return None
    
    return _chat_service
