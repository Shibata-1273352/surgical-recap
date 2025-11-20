"""Test script for W&B Weave Evaluations"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import weave
import base64
import io
from PIL import Image
from app.vision import get_vision_analyzer
from app.dataset import get_dataset_loader
from app.evaluation import (
    run_evaluation,
    medical_accuracy_scorer,
    guideline_compliance_scorer,
    clarity_scorer,
    educational_value_scorer,
    total_score_scorer
)

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def image_to_data_uri(image_path: str, max_size: int = 600) -> str:
    """
    Convert image to Data URI for inline display in browsers

    Args:
        image_path: Path to image file
        max_size: Maximum width/height for thumbnail

    Returns:
        Data URI string (data:image/png;base64,...)
    """
    with Image.open(image_path) as img:
        # Resize to reduce payload size
        img.thumbnail((max_size, max_size))

        # Convert to PNG bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()

        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # Return as Data URI
        return f"data:image/png;base64,{img_base64}"


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

    # Initialize Weave
    entity = os.getenv("WANDB_ENTITY", "takasi-shibata")
    project = os.getenv("WANDB_PROJECT", "surgical-recap")
    weave.init(f"{entity}/{project}")
    print("✓ Weave initialized")
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

    # Create custom model function with image support
    @weave.op()
    async def surgical_vision_model_with_image(input: str) -> dict:
        """Surgical vision analysis model that includes image"""
        result = analyzer.analyze_frame(input)

        # Add image as Data URI for proper display
        result['image_url'] = image_to_data_uri(input)
        result['image_path'] = input

        return result

    # Run Weave Evaluation
    print("🚀 Running W&B Weave Evaluation...")
    print()

    try:
        # Create evaluation with custom model function
        evaluation = weave.Evaluation(
            dataset=eval_dataset,
            scorers=[
                medical_accuracy_scorer,
                guideline_compliance_scorer,
                clarity_scorer,
                educational_value_scorer,
                total_score_scorer
            ]
        )

        results = await evaluation.evaluate(surgical_vision_model_with_image)

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
