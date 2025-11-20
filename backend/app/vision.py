"""Vision Analysis Module - SambaNova Cloud + Llama 3.2 90B Vision"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Optional, Union
from sambanova import SambaNova
import weave


# System Prompt for Surgical Analysis
SURGICAL_VISION_SYSTEM_PROMPT = """You are an expert surgical assistant AI specialized in laparoscopic surgery analysis.
Your role is to analyze surgical video frames with precision and provide structured, medically accurate information.

Key responsibilities:
- Identify surgical instruments visible in the frame
- Recognize the current surgical action/step
- Assess potential risk levels
- Provide concise, professional descriptions in Japanese

Always output in valid JSON format."""


# User Prompt Template
SURGICAL_VISION_USER_PROMPT = """Analyze this image from a laparoscopic cholecystectomy surgery.

Identify:
1. Current Step: The specific surgical action (e.g., Dissection, Clipping, Cutting, Cauterization, Washing, Preparation, Inspection)
2. Instruments: All visible surgical instruments (e.g., Grasper, Hook, Clipper, Scissors, Suction)
3. Risk Level: Assess the risk level of this step (Low, Medium, High)
4. Description: Brief description in Japanese (max 30 characters)

Output format (JSON only):
{
  "step": "string",
  "instruments": ["string"],
  "risk": "Low|Medium|High",
  "description": "string"
}

Rules:
- Use standardized medical terminology in Japanese
- Be specific about instrument types (e.g., "Maryland Dissector" not just "Grasper")
- Consider anatomical context when assessing risk
- If unclear, use "Unknown" rather than guessing"""


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
        system_prompt = system_prompt or SURGICAL_VISION_SYSTEM_PROMPT
        user_prompt = user_prompt or SURGICAL_VISION_USER_PROMPT

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

        # Parse JSON response
        try:
            content = response.choices[0].message.content

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return raw content
            return {
                "error": "Failed to parse JSON",
                "raw_content": response.choices[0].message.content,
                "exception": str(e)
            }

    @weave.op()
    def analyze_sequence(
        self,
        image_paths: list[Union[str, Path]],
        batch_size: int = 1
    ) -> list[Dict]:
        """
        Analyze a sequence of surgical frames

        Args:
            image_paths: List of image paths
            batch_size: Number of images to process at once (default: 1)

        Returns:
            List of analysis results
        """
        results = []

        for i, image_path in enumerate(image_paths):
            try:
                result = self.analyze_frame(image_path)
                result["frame_index"] = i
                result["image_path"] = str(image_path)
                results.append(result)
            except Exception as e:
                results.append({
                    "frame_index": i,
                    "image_path": str(image_path),
                    "error": str(e)
                })

        return results


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
