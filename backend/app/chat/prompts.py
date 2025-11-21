"""
チャット機能用のプロンプトテンプレート

SambaNova Cloudに送信するシステムプロンプトとコンテキスト構築
"""

from typing import List, Dict, Any


# システムプロンプト
CHAT_SYSTEM_PROMPT = """あなたは外科医の教育を支援する専門AIアシスタントです。
腹腔鏡下胆嚢摘出術の手術動画を解析した結果を参照して、新人外科医の質問に答えてください。

【あなたの役割】
- 手術手技に関する質問に対して、解析結果に基づいて正確に回答する
- 医学的に正確な用語を使用し、教育的に説明する
- 具体的なフレーム番号を明示して説明する

【回答ルール】
1. 解析結果に基づいて正確に回答する
2. フレーム番号を明示的に言及する（例: 「フレーム8で〜」）
3. 医学的に正確な用語を使用する
4. わからない場合は推測せず「解析結果からは不明です」と答える
5. 日本語で回答する
6. 簡潔かつ教育的に説明する（200文字程度）
7. 必要に応じて、リスクレベルや使用器具についても言及する

【解析結果の参照方法】
- 各フレームには以下の情報があります:
  - frame_number: フレーム番号
  - step: 手術ステップ（例: Preparation, Dissection, Clipping, Cutting, Cauterization, Washing, Inspection）
  - instruments: 使用器具のリスト
  - risk: リスクレベル（Low, Medium, High）
  - description: 日本語での説明
"""


def build_context_prompt(analysis_results: List[Dict[str, Any]]) -> str:
    """
    解析結果からコンテキストプロンプトを構築
    
    Args:
        analysis_results: 解析結果のリスト
        
    Returns:
        整形されたコンテキスト文字列
    """
    if not analysis_results:
        return "\n【解析結果】\n解析結果が見つかりません。\n"
    
    context_lines = ["\n【解析結果】"]
    
    for i, result in enumerate(analysis_results, 1):
        frame_num = result.get("frame_number", "Unknown")
        step = result.get("step", "Unknown")
        instruments = ", ".join(result.get("instruments", []))
        risk = result.get("risk", "Unknown")
        description = result.get("description", "")
        
        frame_info = f"""
フレーム{frame_num}:
  ステップ: {step}
  使用器具: {instruments}
  リスク: {risk}
  説明: {description}"""
        
        context_lines.append(frame_info)
    
    return "\n".join(context_lines) + "\n"


def build_conversation_history(history: List[Dict[str, str]], max_turns: int = 5) -> str:
    """
    会話履歴を構築（最大5往復分）
    
    Args:
        history: 会話履歴のリスト
        max_turns: 最大往復数
        
    Returns:
        整形された会話履歴
    """
    if not history:
        return ""
    
    # 最新の max_turns * 2 メッセージのみを保持
    recent_history = history[-(max_turns * 2):]
    
    conversation_lines = ["\n【会話履歴】"]
    
    for msg in recent_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        if role == "user":
            conversation_lines.append(f"新人外科医: {content}")
        elif role == "assistant":
            conversation_lines.append(f"AIアシスタント: {content}")
    
    return "\n".join(conversation_lines) + "\n"


def build_full_prompt(
    analysis_results: List[Dict[str, Any]],
    user_message: str,
    history: List[Dict[str, str]] = None
) -> tuple[str, str]:
    """
    完全なプロンプトを構築
    
    Args:
        analysis_results: 解析結果
        user_message: ユーザーの質問
        history: 会話履歴
        
    Returns:
        (system_prompt, user_prompt) のタプル
    """
    # コンテキスト構築
    context = build_context_prompt(analysis_results)
    
    # 会話履歴構築
    history_text = ""
    if history:
        history_text = build_conversation_history(history)
    
    # システムプロンプト
    system_prompt = CHAT_SYSTEM_PROMPT + context
    
    # ユーザープロンプト
    user_prompt = f"{history_text}\n【新人外科医の質問】\n{user_message}\n\n上記の質問に対して、解析結果を参照して回答してください。"
    
    return system_prompt, user_prompt


def extract_frame_references(reply: str, analysis_results: List[Dict[str, Any]]) -> List[int]:
    """
    回答から参照されたフレーム番号を抽出
    
    Args:
        reply: AIの回答
        analysis_results: 解析結果
        
    Returns:
        参照されたフレーム番号のリスト
    """
    referenced_frames = []
    
    # 解析結果内の全フレーム番号を取得
    all_frame_numbers = [r.get("frame_number") for r in analysis_results if "frame_number" in r]
    
    # 回答テキストから「フレームX」のパターンを検索
    import re
    pattern = r'フレーム(\d+)'
    matches = re.findall(pattern, reply)
    
    for match in matches:
        frame_num = int(match)
        if frame_num in all_frame_numbers and frame_num not in referenced_frames:
            referenced_frames.append(frame_num)
    
    return sorted(referenced_frames)
