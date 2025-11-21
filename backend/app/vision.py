"""Vision Analysis Module - SambaNova Cloud + Llama 3.2 90B Vision"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Optional, Union, List
from sambanova import SambaNova
import weave

from .frame_analysis.prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT
)


class VisionAnalyzer:
    """Vision analysis using SambaNova Cloud API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Vision Analyzer

        Args:
            api_key: SambaNova API key (defaults to SAMBANOVA_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("SAMBANOVA_API_KEY")
        if not self.api_key:
            raise ValueError("SAMBANOVA_API_KEY is not set")

        self.client = SambaNova(
            api_key=self.api_key,
            base_url="https://api.sambanova.ai/v1"
        )

    def encode_image(self, image_path: Union[str, Path]) -> str:
        """
        Encode image to base64

        Args:
            image_path: Path to image file

        Returns:
            Base64-encoded image string
        """
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    def _extract_json(self, content: str) -> Dict:
        """
        VLMの出力からJSONを抽出してパース

        reasoningやmarkdownコードブロックが混在していても対応

        Args:
            content: VLMの生出力

        Returns:
            パースされたdict
        """
        import re

        # マークダウンコードブロックを除去
        if "```json" in content:
            match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                content = match.group(1)
        elif "```" in content:
            match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                content = match.group(1)

        # JSON部分を抽出（最初の { から最後の } まで）
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # パース失敗時はdescriptionに生テキストを格納
        return {
            "description": content.strip()
        }

    @weave.op()
    def analyze_frame(
        self,
        image_path: Union[str, Path],
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        temperature: float = 0.1,
        top_p: float = 0.1,
        max_tokens: int = 500
    ) -> Dict:
        """
        Analyze surgical frame using Vision API

        Args:
            image_path: Path to surgical frame image
            system_prompt: Custom system prompt (optional)
            user_prompt: Custom user prompt (optional)
            temperature: Sampling temperature (default: 0.1 for reproducibility)
            top_p: Top-p sampling (default: 0.1)
            max_tokens: Maximum tokens in response

        Returns:
            Dictionary with analysis results
        """
        # Use default prompts if not provided
        system_prompt = system_prompt or SYSTEM_PROMPT
        user_prompt = user_prompt or USER_PROMPT

        # Encode image
        image_base64 = self.encode_image(image_path)

        # Call SambaNova API
        response = self.client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{system_prompt}\n\n{user_prompt}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            temperature=temperature,
            top_p=top_p
        )

        # JSONを抽出してパース
        content = response.choices[0].message.content
        return self._extract_json(content)

    def encode_image_resized(
        self,
        image_path: Union[str, Path],
        max_size: tuple = (512, 512),
        quality: int = 85
    ) -> str:
        """
        画像をリサイズしてbase64エンコード

        Args:
            image_path: 画像パス
            max_size: 最大サイズ (width, height)
            quality: JPEG品質

        Returns:
            Base64エンコードされた文字列
        """
        import cv2

        img = cv2.imread(str(image_path))
        h, w = img.shape[:2]

        # アスペクト比を維持してリサイズ
        scale = min(max_size[0] / w, max_size[1] / h)
        if scale < 1:
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))

        # JPEGエンコード
        _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buffer).decode()

    @weave.op()
    def select_keyframes_batch(
        self,
        image_paths: List[Union[str, Path]],
        batch_id: int = 0
    ) -> List[int]:
        """
        バッチからキーフレームを選択

        Args:
            image_paths: 画像パスのリスト (3-10枚)
            batch_id: バッチID（プロンプト用）

        Returns:
            選択されたインデックスのリスト (0 ~ len(image_paths)-1)
        """
        from .analize_sequence.prompts import (
            SELECTOR_SYSTEM_PROMPT,
            create_selector_user_prompt
        )

        # 画像をリサイズしてbase64エンコード
        image_contents = []
        for img_path in image_paths:
            img_b64 = self.encode_image_resized(img_path)
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })

        # プロンプト構築
        user_prompt = create_selector_user_prompt(
            frame_count=len(image_paths),
            batch_id=batch_id
        )

        # メッセージ構築
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{SELECTOR_SYSTEM_PROMPT}\n\n{user_prompt}"},
                    *image_contents
                ]
            }
        ]

        # API呼び出し
        response = self.client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct",
            messages=messages,
            temperature=0.1,
            top_p=0.1
        )

        # JSON解析
        try:
            content = response.choices[0].message.content

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            result = json.loads(content)
            selected_indices = result.get("selected_indices", [])

            # バリデーション
            valid_indices = [
                idx for idx in selected_indices
                if isinstance(idx, int) and 0 <= idx < len(image_paths)
            ]

            if not valid_indices:
                # フォールバック: 中央とエンド
                valid_indices = [0, len(image_paths) // 2]

            return valid_indices

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: JSON parse error in batch {batch_id}: {e}")
            # フォールバック: 最初と中央
            return [0, len(image_paths) // 2]


def get_vision_analyzer() -> Optional[VisionAnalyzer]:
    """
    Get VisionAnalyzer instance

    Returns:
        VisionAnalyzer instance or None if API key is not set
    """
    try:
        return VisionAnalyzer()
    except ValueError:
        return None
