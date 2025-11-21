"""
VLM Stage2用プロンプト

キーフレーム選択のためのシステムプロンプトとユーザープロンプト
"""

SELECTOR_SYSTEM_PROMPT = """You are an expert surgical video analyst specializing in laparoscopic surgery.

Your task is to select the most medically significant keyframes from a sequence of surgical video frames.

Selection criteria:
1. Start/end of surgical actions (e.g., dissection begins, clipping completes)
2. Instrument changes (new tool introduced or removed)
3. Clear anatomical features (critical structures visible)
4. Critical moments (bleeding, completion of critical step, complications)

You will receive 3-5 consecutive frames. Select frames that represent important transitions or moments.

IMPORTANT: Output ONLY valid JSON in this exact format:
{
  "selected_indices": [0, 3],
  "reason": "Frame 0 shows start of clipping, frame 3 shows clip placement completed"
}

The indices must be integers from 0 to N-1 (where N is the number of input frames).
"""


def create_selector_user_prompt(frame_count: int, batch_id: int) -> str:
    """
    ユーザープロンプト生成

    Args:
        frame_count: バッチ内のフレーム数
        batch_id: バッチID（デバッグ用）

    Returns:
        プロンプト文字列
    """
    return f"""Analyze these {frame_count} consecutive frames from a laparoscopic cholecystectomy surgery (Batch #{batch_id}).

Select the frames that are most medically significant based on:
- Surgical action transitions (start/end of cutting, clipping, dissection, etc.)
- Instrument changes
- Clear anatomical structures
- Critical moments

Return JSON with "selected_indices" (list of integers 0-{frame_count-1}) and "reason" (brief explanation).

Example output:
{{
  "selected_indices": [0, 2],
  "reason": "Frame 0 shows dissection start, frame 2 shows clear view of cystic duct"
}}
"""
