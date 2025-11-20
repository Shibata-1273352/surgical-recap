"""Test W&B Weave Evaluations - Following official documentation pattern"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import weave
from app.vision import get_vision_analyzer
from app.dataset import get_dataset_loader
from app.evaluation import get_evaluator

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


# Define model as a simple function (not weave.Model)
@weave.op()
async def surgical_vision_model(input: str) -> dict:
    """Simple function that analyzes surgical images"""
    analyzer = get_vision_analyzer()
    return analyzer.analyze_frame(input)


# Define scorers with model_output parameter
@weave.op()
async def medical_accuracy_scorer(model_output: dict) -> dict:
    """Score medical accuracy"""
    evaluator = get_evaluator()
    result = evaluator.judge_vision_result(
        step=model_output.get("step", "Unknown"),
        instruments=model_output.get("instruments", []),
        risk=model_output.get("risk", "Unknown"),
        description=model_output.get("description", "")
    )
    return {"medical_accuracy": result.get("medical_accuracy", 0)}


@weave.op()
async def total_score_scorer(model_output: dict) -> dict:
    """Score total"""
    evaluator = get_evaluator()
    result = evaluator.judge_vision_result(
        step=model_output.get("step", "Unknown"),
        instruments=model_output.get("instruments", []),
        risk=model_output.get("risk", "Unknown"),
        description=model_output.get("description", "")
    )
    return {"total_score": result.get("total_score", 0)}


async def main():
    print("Testing W&B Weave Evaluations (Official Pattern)")
    print("=" * 70)

    # Initialize Weave
    entity = os.getenv("WANDB_ENTITY", "takasi-shibata")
    project = os.getenv("WANDB_PROJECT", "surgical-recap")
    weave.init(f"{entity}/{project}")
    print("✓ Weave initialized")

    # Load dataset
    loader = get_dataset_loader()
    videos = loader.get_all_videos()
    sequence = loader.load_sequence(videos[0], load_images=False)

    # Create dataset (using 2 frames for quick test)
    dataset = [
        {"input": sequence[0]['image_path']},
        {"input": sequence[1]['image_path']}
    ]
    print(f"✓ Dataset ready: {len(dataset)} frames")
    print()

    # Create evaluation
    evaluation = weave.Evaluation(
        dataset=dataset,
        scorers=[medical_accuracy_scorer, total_score_scorer]
    )

    print("🚀 Running evaluation...")
    results = await evaluation.evaluate(surgical_vision_model)

    print()
    print("=" * 70)
    print("✓ Evaluation completed!")
    print(f"Results: {results}")
    print()
    print(f"🔗 View at: https://wandb.ai/{entity}/{project}/weave")
    print()


if __name__ == "__main__":
    asyncio.run(main())
