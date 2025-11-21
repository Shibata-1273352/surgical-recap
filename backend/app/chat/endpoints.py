"""
チャット機能のAPIエンドポイント

FastAPIルーターで実装
"""

from fastapi import APIRouter, HTTPException, status
from typing import List

from .models import (
    ChatRequest,
    ChatResponse,
    SessionListResponse,
    SessionDetailResponse,
    SessionSummary,
    DeleteResponse,
    ErrorResponse
)
from .service import get_chat_service


def initialize_demo_sessions():
    """
    デモ用セッションを初期化（起動時に自動実行）
    """
    from .session_manager import get_session_manager
    from datetime import datetime
    
    session_manager = get_session_manager()
    
    # 既にセッションがある場合はスキップ
    if session_manager.get_session_count() > 0:
        return
    
    demo_sessions = [
        {
            "video_id": "demo_video_01",
            "analysis_results": [
                {
                    "frame_number": 1,
                    "step": "Preparation",
                    "instruments": ["Grasper", "Camera"],
                    "risk": "Low",
                    "description": "手術開始前の準備段階"
                },
                {
                    "frame_number": 5,
                    "step": "Dissection",
                    "instruments": ["Hook", "Grasper"],
                    "risk": "Medium",
                    "description": "胆嚢周囲の剥離操作"
                },
                {
                    "frame_number": 8,
                    "step": "Clipping",
                    "instruments": ["Clipper", "Grasper"],
                    "risk": "High",
                    "description": "胆嚢管のクリッピング"
                },
                {
                    "frame_number": 10,
                    "step": "Cutting",
                    "instruments": ["Scissors", "Grasper"],
                    "risk": "High",
                    "description": "胆嚢管の切離"
                },
                {
                    "frame_number": 15,
                    "step": "Cauterization",
                    "instruments": ["Hook", "Suction"],
                    "risk": "Medium",
                    "description": "止血処理"
                }
            ]
        },
        {
            "video_id": "demo_video_02",
            "analysis_results": [
                {
                    "frame_number": 2,
                    "step": "Preparation",
                    "instruments": ["Grasper", "Camera", "Trocar"],
                    "risk": "Low",
                    "description": "トロッカー挿入と視野確保"
                },
                {
                    "frame_number": 6,
                    "step": "Dissection",
                    "instruments": ["Hook", "Grasper"],
                    "risk": "Medium",
                    "description": "Calot三角の剥離"
                },
                {
                    "frame_number": 12,
                    "step": "Clipping",
                    "instruments": ["Clipper", "Grasper"],
                    "risk": "High",
                    "description": "胆嚢動脈のクリッピング"
                },
                {
                    "frame_number": 14,
                    "step": "Clipping",
                    "instruments": ["Clipper", "Grasper"],
                    "risk": "High",
                    "description": "胆嚢管のクリッピング"
                },
                {
                    "frame_number": 16,
                    "step": "Cutting",
                    "instruments": ["Scissors", "Grasper"],
                    "risk": "High",
                    "description": "胆嚢動脈・胆嚢管の切離"
                },
                {
                    "frame_number": 20,
                    "step": "Washing",
                    "instruments": ["Suction", "Irrigation"],
                    "risk": "Low",
                    "description": "術野の洗浄"
                }
            ]
        },
        {
            "video_id": "demo_video_03",
            "analysis_results": [
                {
                    "frame_number": 3,
                    "step": "Preparation",
                    "instruments": ["Grasper", "Camera"],
                    "risk": "Low",
                    "description": "気腹確立と視野確認"
                },
                {
                    "frame_number": 7,
                    "step": "Dissection",
                    "instruments": ["Hook", "Grasper", "Suction"],
                    "risk": "Medium",
                    "description": "胆嚢底部の把持と展開"
                },
                {
                    "frame_number": 11,
                    "step": "Dissection",
                    "instruments": ["Hook", "Grasper"],
                    "risk": "High",
                    "description": "Critical view of safety確保"
                },
                {
                    "frame_number": 13,
                    "step": "Clipping",
                    "instruments": ["Clipper", "Grasper"],
                    "risk": "High",
                    "description": "構造物の二重クリップ"
                },
                {
                    "frame_number": 15,
                    "step": "Cutting",
                    "instruments": ["Scissors", "Grasper"],
                    "risk": "High",
                    "description": "クリップ間の切離"
                },
                {
                    "frame_number": 18,
                    "step": "Dissection",
                    "instruments": ["Hook", "Grasper"],
                    "risk": "Medium",
                    "description": "胆嚢床からの剥離"
                },
                {
                    "frame_number": 22,
                    "step": "Inspection",
                    "instruments": ["Camera", "Suction"],
                    "risk": "Low",
                    "description": "止血確認と最終チェック"
                }
            ]
        },
        {
            "video_id": "sample_masked_clipped",
            "analysis_results": [
                {
                    "frame_number": 1,
                    "step": "Preparation",
                    "instruments": ["Camera", "Trocar"],
                    "risk": "Low",
                    "description": "ポート挿入と気腹確立"
                },
                {
                    "frame_number": 10,
                    "step": "Dissection",
                    "instruments": ["Hook", "Grasper"],
                    "risk": "Medium",
                    "description": "胆嚢周囲の剥離開始"
                },
                {
                    "frame_number": 20,
                    "step": "Dissection",
                    "instruments": ["Hook", "Grasper"],
                    "risk": "Medium",
                    "description": "Calot三角の展開"
                },
                {
                    "frame_number": 30,
                    "step": "Clipping",
                    "instruments": ["Clipper", "Grasper"],
                    "risk": "High",
                    "description": "胆嚢動脈のクリッピング"
                },
                {
                    "frame_number": 35,
                    "step": "Clipping",
                    "instruments": ["Clipper", "Grasper"],
                    "risk": "High",
                    "description": "胆嚢管のクリッピング"
                },
                {
                    "frame_number": 40,
                    "step": "Cutting",
                    "instruments": ["Scissors", "Grasper"],
                    "risk": "High",
                    "description": "胆嚢管・動脈の切離"
                },
                {
                    "frame_number": 50,
                    "step": "Dissection",
                    "instruments": ["Hook", "Grasper"],
                    "risk": "Medium",
                    "description": "胆嚢床からの剥離"
                },
                {
                    "frame_number": 60,
                    "step": "Washing",
                    "instruments": ["Suction", "Irrigation"],
                    "risk": "Low",
                    "description": "術野の洗浄"
                },
                {
                    "frame_number": 70,
                    "step": "Inspection",
                    "instruments": ["Camera"],
                    "risk": "Low",
                    "description": "止血確認と最終確認"
                }
            ]
        }
    ]
    
    # セッションを作成
    for demo in demo_sessions:
        session_id = f"{demo['video_id']}_demo"
        session_manager.create_session(
            session_id=session_id,
            video_id=demo['video_id'],
            analysis_results=demo['analysis_results']
        )


# ルーター作成
router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
    responses={
        404: {"model": ErrorResponse, "description": "Not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


@router.get("/sessions", response_model=SessionListResponse)
def get_sessions():
    """
    解析済みセッション一覧を取得
    
    Returns:
        SessionListResponse: セッション一覧
    """
    # セッション管理は直接使用（API キー不要）
    from .session_manager import get_session_manager
    session_manager = get_session_manager()
    
    try:
        sessions = session_manager.get_session_summaries()
        
        return SessionListResponse(
            status="ok",
            sessions=sessions,
            total=len(sessions)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sessions: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(session_id: str):
    """
    特定セッションの詳細を取得
    
    Args:
        session_id: セッションID
        
    Returns:
        SessionDetailResponse: セッション詳細
    """
    service = get_chat_service()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. Check SAMBANOVA_API_KEY."
        )
    
    try:
        session_detail = service.get_session_detail(session_id)
        
        if not session_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return SessionDetailResponse(
            status="ok",
            session_id=session_detail["session_id"],
            video_id=session_detail["video_id"],
            analysis_results=session_detail["analysis_results"],
            created_at=session_detail["created_at"],
            frame_count=session_detail["frame_count"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session detail: {str(e)}"
        )


@router.post("/send", response_model=ChatResponse)
def send_message(request: ChatRequest):
    """
    チャットメッセージを送信
    
    Args:
        request: チャットリクエスト
        
    Returns:
        ChatResponse: AI応答
    """
    service = get_chat_service()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. Check SAMBANOVA_API_KEY."
        )
    
    try:
        # 会話履歴を辞書形式に変換
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.history
        ]
        
        # メッセージ送信
        result = service.send_message(
            session_id=request.session_id,
            message=request.message,
            history=history
        )
        
        return ChatResponse(
            reply=result["reply"],
            referenced_frames=result["referenced_frames"],
            metadata=result["metadata"]
        )
    
    except ValueError as e:
        # セッションが存在しない等
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        # SambaNova APIエラー
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.delete("/session/{session_id}", response_model=DeleteResponse)
def delete_session(session_id: str):
    """
    セッションを削除
    
    Args:
        session_id: セッションID
        
    Returns:
        DeleteResponse: 削除結果
    """
    service = get_chat_service()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. Check SAMBANOVA_API_KEY."
        )
    
    try:
        success = service.delete_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return DeleteResponse(
            status="ok",
            message=f"Session {session_id} deleted successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.post("/test/create-session")
def create_test_session(video_id: str = "test_video01"):
    """
    テスト用セッションを作成（開発・デモ用）
    
    Args:
        video_id: 動画ID
        
    Returns:
        作成されたセッション情報
    """
    from .session_manager import get_session_manager
    from datetime import datetime
    
    session_manager = get_session_manager()
    
    # ダミーの解析結果を作成
    session_id = f"{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    analysis_results = [
        {
            "frame_number": 1,
            "step": "Preparation",
            "instruments": ["Grasper", "Camera"],
            "risk": "Low",
            "description": "手術開始前の準備段階"
        },
        {
            "frame_number": 5,
            "step": "Dissection",
            "instruments": ["Hook", "Grasper"],
            "risk": "Medium",
            "description": "胆嚢周囲の剥離操作"
        },
        {
            "frame_number": 8,
            "step": "Clipping",
            "instruments": ["Clipper", "Grasper"],
            "risk": "High",
            "description": "胆嚢管のクリッピング"
        },
        {
            "frame_number": 9,
            "step": "Cutting",
            "instruments": ["Scissors", "Grasper"],
            "risk": "High",
            "description": "胆嚢管の切離"
        },
        {
            "frame_number": 12,
            "step": "Cauterization",
            "instruments": ["Hook", "Suction"],
            "risk": "Medium",
            "description": "止血処理"
        }
    ]
    
    success = session_manager.create_session(
        session_id=session_id,
        video_id=video_id,
        analysis_results=analysis_results
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session {session_id} already exists"
        )
    
    return {
        "status": "ok",
        "session_id": session_id,
        "video_id": video_id,
        "frame_count": len(analysis_results),
        "message": "Test session created successfully"
    }


@router.get("/health")
def health_check():
    """
    チャット機能のヘルスチェック
    
    Returns:
        ヘルスステータス
    """
    service = get_chat_service()
    
    if not service:
        return {
            "status": "unavailable",
            "message": "SAMBANOVA_API_KEY is not set"
        }
    
    return {
        "status": "ok",
        "service": "chat",
        "model": service.model
    }
