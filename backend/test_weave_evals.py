"""Test script for W&B Weave Evaluations"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from app.vision import get_vision_analyzer
from app.dataset import get_dataset_loader
from app.evaluation import (
    SurgicalVisionModel,
    run_evaluation,
    medical_accuracy_scorer,
    guideline_compliance_scorer,
    clarity_scorer,
    educational_value_scorer,
    total_score_scorer
)

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


async def main():
    print("Testing W&B Weave Evaluations...")
    print("=" * 70)

    # Check credentials
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("❌ AZURE_OPENAI_API_KEY is not set!")
        return

    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("❌ AZURE_OPENAI_ENDPOINT is not set!")
        return

    if not os.getenv("SAMBANOVA_API_KEY"):
        print("❌ SAMBANOVA_API_KEY is not set!")
        return

    if not os.getenv("WANDB_API_KEY"):
        print("⚠️  WANDB_API_KEY is not set - Weave tracking may not work")

    print("✓ All credentials configured")
    print()

    # Load dataset
    loader = get_dataset_loader()
    if not loader:
        print("❌ Dataset not found!")
        return

    print("✓ Dataset loaded")
    print()

    # Get vision analyzer
    analyzer = get_vision_analyzer()
    if not analyzer:
        print("❌ Vision analyzer not available!")
        return

    print("✓ Vision analyzer initialized")
    print()

    # Create model
    model = SurgicalVisionModel(analyzer=analyzer)
    print("✓ Surgical Vision Model created")
    print()

    # Prepare evaluation dataset (first 3 frames from video01)
    videos = loader.get_all_videos()
    test_video = videos[0]
    sequence = loader.load_sequence(test_video, load_images=False)

    # Create evaluation dataset
    # IMPORTANT: Use 'input' key for Weave Evaluations compatibility
    eval_dataset = []
    for i in range(min(3, len(sequence))):
        frame = sequence[i]
        eval_dataset.append({
            "input": frame['image_path'],  # Weave expects 'input' key
            "frame_id": frame['frame_id'],
            # Optional: Add reference answers if you have ground truth
            # "reference_answer": {
            #     "step": "Dissection",
            #     "instruments": ["Grasper"],
            #     "risk": "Low"
            # }
        })

    print(f"📊 Evaluation Dataset: {len(eval_dataset)} frames from {test_video}")
    print("-" * 70)

    # Run Weave Evaluation
    print("🚀 Running W&B Weave Evaluation...")

    # Generate unique evaluation name with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eval_name = f"surgical-vision-eval-{timestamp}"
    print(f"📝 Evaluation name: {eval_name}")
    print()

    try:
        results = await run_evaluation(
            dataset=eval_dataset,
            model=model,
            scorers=[
                medical_accuracy_scorer,
                guideline_compliance_scorer,
                clarity_scorer,
                educational_value_scorer,
                total_score_scorer
            ],
            evaluation_name=eval_name
        )

        print("=" * 70)
        print("✓ Weave Evaluation completed!")
        print()
        print("📈 Results:")
        print(f"  {results}")
        print()
        print("🔗 View detailed results in W&B Weave:")
        entity = os.getenv("WANDB_ENTITY", "takasi-shibata")
        project = os.getenv("WANDB_PROJECT", "surgical-recap")
        print(f"   https://wandb.ai/{entity}/{project}/weave")
        print()
        print("💡 The evaluation results are now visible in the 'Evaluations' tab")

    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
