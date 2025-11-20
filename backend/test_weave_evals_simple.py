"""Simple test for W&B Weave Evaluations - Debug version"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import weave
from app.vision import get_vision_analyzer

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


# Simple model for testing
class SimpleVisionModel(weave.Model):
    analyzer: object

    @weave.op()
    async def predict(self, input: str):
        """Predict - returns vision analysis result"""
        result = self.analyzer.analyze_frame(input)
        return result


# Simple scorers for testing
@weave.op()
async def simple_step_scorer(output: dict) -> dict:
    """Simple scorer that checks if step is present"""
    has_step = "step" in output and output["step"] != "Unknown"
    return {"has_step": 1.0 if has_step else 0.0}


@weave.op()
async def simple_instruments_scorer(output: dict) -> dict:
    """Simple scorer that counts instruments"""
    num_instruments = len(output.get("instruments", []))
    return {"num_instruments": float(num_instruments)}


async def main():
    print("Simple W&B Weave Evaluations Test")
    print("=" * 70)

    # Initialize Weave
    entity = os.getenv("WANDB_ENTITY", "takasi-shibata")
    project = os.getenv("WANDB_PROJECT", "surgical-recap")
    weave.init(f"{entity}/{project}")

    print("✓ Weave initialized")

    # Get analyzer
    analyzer = get_vision_analyzer()
    if not analyzer:
        print("❌ Vision analyzer not available!")
        return

    print("✓ Vision analyzer ready")

    # Create model
    model = SimpleVisionModel(analyzer=analyzer)
    print("✓ Model created")

    # Create simple dataset
    from app.dataset import get_dataset_loader
    loader = get_dataset_loader()
    videos = loader.get_all_videos()
    sequence = loader.load_sequence(videos[0], load_images=False)

    # Use only 2 frames for quick test
    dataset = [
        {"input": sequence[0]['image_path']},
        {"input": sequence[1]['image_path']}
    ]

    print(f"✓ Dataset ready: {len(dataset)} frames")
    print()
    print("🚀 Running Evaluation...")

    # Create and run evaluation
    evaluation = weave.Evaluation(
        dataset=dataset,
        scorers=[simple_step_scorer, simple_instruments_scorer]
    )

    results = await evaluation.evaluate(model)

    print()
    print("=" * 70)
    print("✓ Evaluation completed!")
    print()
    print(f"Results: {results}")
    print()
    print(f"🔗 View at: https://wandb.ai/{entity}/{project}/weave")
    print()


if __name__ == "__main__":
    asyncio.run(main())
