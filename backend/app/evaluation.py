"""Evaluation Module - W&B Weave + Azure OpenAI Judge"""

import os
import json
from typing import Dict, List, Optional, Any
from openai import AzureOpenAI
import weave
from pydantic import BaseModel


# Judge System Prompt
JUDGE_SYSTEM_PROMPT = """あなたは経験豊富な外科指導医であり、AI生成コンテンツの評価を専門としています。

あなたの役割:
- 手術画像解析結果の医学的正確性を評価する
- 医療ガイドラインへの準拠度を確認する
- 説明の明確さと教育的価値を判定する

評価基準:
1. 医学的正確性 (1-5点): 解析結果が医学的に正確か
2. ガイドライン準拠度 (1-5点): 標準的なガイドラインに沿っているか
3. 説明の明確さ (1-5点): 説明がわかりやすく具体的か
4. 教育的価値 (1-5点): 若手医師の教育に役立つか

必ずJSON形式で出力してください。"""


# Judge User Prompt Template
JUDGE_USER_PROMPT_TEMPLATE = """以下の手術画像解析結果を評価してください。

【解析結果】
手術手技: {step}
使用器具: {instruments}
リスクレベル: {risk}
説明: {description}

【評価項目】
1. 医学的正確性 (1-5点)
   - 手技認識は正確か
   - 器具識別は正確か
   - リスク評価は適切か

2. ガイドライン準拠度 (1-5点)
   - 標準的な医療ガイドラインに沿っているか
   - 用語が適切か

3. 説明の明確さ (1-5点)
   - 説明が具体的でわかりやすいか
   - 専門用語が適切に使われているか

4. 教育的価値 (1-5点)
   - 若手医師の学習に役立つか
   - 重要なポイントが含まれているか

【出力形式】
以下のJSON形式で評価を出力してください:
{{
  "medical_accuracy": <1-5>,
  "guideline_compliance": <1-5>,
  "clarity": <1-5>,
  "educational_value": <1-5>,
  "total_score": <4-20>,
  "feedback": "具体的な評価コメント（日本語、50-100文字）"
}}"""


class VisionEvaluator:
    """Vision解析結果の評価システム"""

    def __init__(
        self,
        azure_api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        azure_deployment: Optional[str] = None,
        wandb_project: Optional[str] = None,
        wandb_entity: Optional[str] = None
    ):
        """
        Initialize Vision Evaluator

        Args:
            azure_api_key: Azure OpenAI API key
            azure_endpoint: Azure OpenAI endpoint
            azure_deployment: Azure OpenAI deployment name
            wandb_project: W&B project name
            wandb_entity: W&B entity name
        """
        # Azure OpenAI setup
        self.api_key = azure_api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment = azure_deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        if not all([self.api_key, self.endpoint]):
            raise ValueError("Azure OpenAI credentials not set")

        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version="2024-08-01-preview",
            azure_endpoint=self.endpoint
        )

        # Note: weave.init() should be called externally before creating evaluator
        # to avoid multiple initialization issues

    @weave.op()
    def judge_vision_result(
        self,
        step: str,
        instruments: List[str],
        risk: str,
        description: str,
        reference_answer: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Judge vision analysis result using Azure OpenAI

        Args:
            step: Detected surgical step
            instruments: List of detected instruments
            risk: Risk level assessment
            description: Description of the scene
            reference_answer: Optional ground truth for comparison

        Returns:
            Evaluation results with scores and feedback
        """
        # Format instruments
        instruments_str = ", ".join(instruments) if instruments else "なし"

        # Build user prompt
        user_prompt = JUDGE_USER_PROMPT_TEMPLATE.format(
            step=step,
            instruments=instruments_str,
            risk=risk,
            description=description or "（説明なし）"
        )

        # Add reference if available
        if reference_answer:
            user_prompt += f"\n\n【参考（正解データ）】\n{json.dumps(reference_answer, ensure_ascii=False, indent=2)}"

        # Call Azure OpenAI
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            # Parse JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            # Add metadata
            result["input"] = {
                "step": step,
                "instruments": instruments,
                "risk": risk,
                "description": description
            }

            return result

        except Exception as e:
            return {
                "error": str(e),
                "medical_accuracy": 0,
                "guideline_compliance": 0,
                "clarity": 0,
                "educational_value": 0,
                "total_score": 0,
                "feedback": f"評価エラー: {str(e)}"
            }

    @weave.op()
    def evaluate_batch(
        self,
        results: List[Dict[str, Any]],
        reference_answers: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a batch of vision results

        Args:
            results: List of vision analysis results
            reference_answers: Optional list of ground truth data

        Returns:
            Aggregated evaluation metrics
        """
        evaluations = []

        for i, result in enumerate(results):
            ref = reference_answers[i] if reference_answers and i < len(reference_answers) else None

            evaluation = self.judge_vision_result(
                step=result.get("step", "Unknown"),
                instruments=result.get("instruments", []),
                risk=result.get("risk", "Unknown"),
                description=result.get("description", ""),
                reference_answer=ref
            )

            evaluations.append(evaluation)

        # Calculate aggregate metrics
        total_items = len(evaluations)
        valid_items = [e for e in evaluations if "error" not in e]

        if not valid_items:
            return {
                "status": "error",
                "message": "No valid evaluations",
                "evaluations": evaluations
            }

        avg_metrics = {
            "medical_accuracy": sum(e["medical_accuracy"] for e in valid_items) / len(valid_items),
            "guideline_compliance": sum(e["guideline_compliance"] for e in valid_items) / len(valid_items),
            "clarity": sum(e["clarity"] for e in valid_items) / len(valid_items),
            "educational_value": sum(e["educational_value"] for e in valid_items) / len(valid_items),
            "total_score": sum(e["total_score"] for e in valid_items) / len(valid_items)
        }

        return {
            "status": "ok",
            "total_evaluated": total_items,
            "valid_evaluations": len(valid_items),
            "average_metrics": avg_metrics,
            "evaluations": evaluations
        }


def get_evaluator() -> Optional[VisionEvaluator]:
    """
    Get VisionEvaluator instance

    Returns:
        VisionEvaluator or None if credentials not available
    """
    try:
        return VisionEvaluator()
    except ValueError as e:
        print(f"Warning: {e}")
        return None


# ============================================================
# W&B Weave Evaluations Integration
# ============================================================

# Note: W&B Weave Evaluations work best with simple @weave.op() functions,
# not weave.Model classes. The model function is created dynamically in run_evaluation().


# Global evaluator instance for scorers
_evaluator_instance = None

def _get_evaluator_instance() -> VisionEvaluator:
    """Get or create global evaluator instance"""
    global _evaluator_instance
    if _evaluator_instance is None:
        _evaluator_instance = VisionEvaluator()
    return _evaluator_instance


@weave.op()
async def medical_accuracy_scorer(model_output: Dict) -> Dict:
    """
    Score medical accuracy of vision analysis

    Args:
        model_output: Output from the vision model (matches Weave convention)

    Returns:
        Dictionary with medical_accuracy score (0-5)
    """
    evaluator = _get_evaluator_instance()

    result = evaluator.judge_vision_result(
        step=model_output.get("step", "Unknown"),
        instruments=model_output.get("instruments", []),
        risk=model_output.get("risk", "Unknown"),
        description=model_output.get("description", "")
    )

    return {"medical_accuracy": result.get("medical_accuracy", 0)}


@weave.op()
async def guideline_compliance_scorer(model_output: Dict) -> Dict:
    """
    Score guideline compliance of vision analysis

    Args:
        model_output: Output from the vision model

    Returns:
        Dictionary with guideline_compliance score (0-5)
    """
    evaluator = _get_evaluator_instance()

    result = evaluator.judge_vision_result(
        step=model_output.get("step", "Unknown"),
        instruments=model_output.get("instruments", []),
        risk=model_output.get("risk", "Unknown"),
        description=model_output.get("description", "")
    )

    return {"guideline_compliance": result.get("guideline_compliance", 0)}


@weave.op()
async def clarity_scorer(model_output: Dict) -> Dict:
    """
    Score clarity of vision analysis description

    Args:
        model_output: Output from the vision model

    Returns:
        Dictionary with clarity score (0-5)
    """
    evaluator = _get_evaluator_instance()

    result = evaluator.judge_vision_result(
        step=model_output.get("step", "Unknown"),
        instruments=model_output.get("instruments", []),
        risk=model_output.get("risk", "Unknown"),
        description=model_output.get("description", "")
    )

    return {"clarity": result.get("clarity", 0)}


@weave.op()
async def educational_value_scorer(model_output: Dict) -> Dict:
    """
    Score educational value of vision analysis

    Args:
        model_output: Output from the vision model

    Returns:
        Dictionary with educational_value score (0-5)
    """
    evaluator = _get_evaluator_instance()

    result = evaluator.judge_vision_result(
        step=model_output.get("step", "Unknown"),
        instruments=model_output.get("instruments", []),
        risk=model_output.get("risk", "Unknown"),
        description=model_output.get("description", "")
    )

    return {"educational_value": result.get("educational_value", 0)}


@weave.op()
async def total_score_scorer(model_output: Dict) -> Dict:
    """
    Score total evaluation (sum of all metrics)

    Args:
        model_output: Output from the vision model

    Returns:
        Dictionary with total_score (0-20)
    """
    evaluator = _get_evaluator_instance()

    result = evaluator.judge_vision_result(
        step=model_output.get("step", "Unknown"),
        instruments=model_output.get("instruments", []),
        risk=model_output.get("risk", "Unknown"),
        description=model_output.get("description", "")
    )

    return {"total_score": result.get("total_score", 0)}


async def run_evaluation(
    dataset: List[Dict[str, Any]],
    analyzer: Any,
    scorers: Optional[List] = None
) -> Any:
    """
    Run W&B Weave Evaluation on surgical vision dataset

    Args:
        dataset: List of examples with 'input' (image path) and optional 'reference_answer'
        analyzer: Vision analyzer instance
        scorers: List of scorer functions (default: all scorers)

    Returns:
        Evaluation results

    Example:
        dataset = [
            {
                "input": "path/to/frame1.jpg",  # Use 'input' key for Weave compatibility
                "reference_answer": {"step": "Dissection", "instruments": ["Grasper"], "risk": "Low"}
            },
            {
                "input": "path/to/frame2.jpg"
            }
        ]

        from app.vision import get_vision_analyzer
        analyzer = get_vision_analyzer()

        import asyncio
        results = asyncio.run(run_evaluation(dataset, analyzer))
    """
    if scorers is None:
        scorers = [
            medical_accuracy_scorer,
            guideline_compliance_scorer,
            clarity_scorer,
            educational_value_scorer,
            total_score_scorer
        ]

    # Create model function (simple @weave.op() function, not weave.Model)
    @weave.op()
    async def surgical_vision_model(input: str) -> dict:
        """Surgical vision analysis model"""
        return analyzer.analyze_frame(input)

    evaluation = weave.Evaluation(
        dataset=dataset,
        scorers=scorers
    )

    return await evaluation.evaluate(surgical_vision_model)
