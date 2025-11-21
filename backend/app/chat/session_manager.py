"""
セッション管理モジュール

メモリ内で解析結果を管理（暫定実装）
将来的にはDBへの永続化を検討
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import threading


class SessionManager:
    """
    解析セッションを管理するクラス
    
    メモリ内でセッション情報を保持
    スレッドセーフな実装
    """
    
    def __init__(self):
        """初期化"""
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_session(
        self,
        session_id: str,
        video_id: str,
        analysis_results: List[Dict[str, Any]]
    ) -> bool:
        """
        新しいセッションを作成
        
        Args:
            session_id: セッションID
            video_id: 動画ID
            analysis_results: 解析結果のリスト
            
        Returns:
            作成成功ならTrue
        """
        with self._lock:
            if session_id in self._sessions:
                return False  # 既に存在する
            
            self._sessions[session_id] = {
                "session_id": session_id,
                "video_id": video_id,
                "analysis_results": analysis_results,
                "created_at": datetime.now(),
                "frame_count": len(analysis_results)
            }
            return True
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッション情報を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            セッション情報（存在しない場合はNone）
        """
        with self._lock:
            return self._sessions.get(session_id)
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        全セッション情報を取得
        
        Returns:
            全セッションのリスト
        """
        with self._lock:
            return list(self._sessions.values())
    
    def get_session_summaries(self) -> List[Dict[str, Any]]:
        """
        全セッションの概要を取得
        
        Returns:
            セッション概要のリスト
        """
        with self._lock:
            summaries = []
            for session_id, session_data in self._sessions.items():
                summary = {
                    "session_id": session_id,
                    "video_id": session_data["video_id"],
                    "analyzed_at": session_data["created_at"],
                    "frame_count": session_data["frame_count"],
                    "summary": f"{session_data['video_id']} - {session_data['frame_count']}フレーム解析済み"
                }
                summaries.append(summary)
            
            # 新しい順にソート
            summaries.sort(key=lambda x: x["analyzed_at"], reverse=True)
            return summaries
    
    def delete_session(self, session_id: str) -> bool:
        """
        セッションを削除
        
        Args:
            session_id: セッションID
            
        Returns:
            削除成功ならTrue
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
    
    def session_exists(self, session_id: str) -> bool:
        """
        セッションが存在するか確認
        
        Args:
            session_id: セッションID
            
        Returns:
            存在する場合True
        """
        with self._lock:
            return session_id in self._sessions
    
    def get_analysis_results(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        セッションの解析結果を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            解析結果のリスト（存在しない場合はNone）
        """
        session = self.get_session(session_id)
        if session:
            return session.get("analysis_results")
        return None
    
    def get_session_count(self) -> int:
        """
        セッション数を取得
        
        Returns:
            セッション数
        """
        with self._lock:
            return len(self._sessions)
    
    def clear_all(self) -> None:
        """
        全セッションをクリア（テスト用）
        """
        with self._lock:
            self._sessions.clear()


# グローバルインスタンス
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """
    SessionManagerのグローバルインスタンスを取得
    
    Returns:
        SessionManagerインスタンス
    """
    return _session_manager
