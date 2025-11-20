"""Test script for Evaluation System"""

import os
from pathlib import Path
from dotenv import load_dotenv
from app.vision import get_vision_analyzer
from app.dataset import get_dataset_loader
from app.evaluation import get_evaluator

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def main():
    print("Testing Evaluation System with W&B Weave + Azure OpenAI Judge...")
    print("=" * 70)

    # Check Azure OpenAI credentials
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("❌ AZURE_OPENAI_API_KEY is not set!")
        print("Please set your Azure OpenAI credentials in .env file")
        return

    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("❌ AZURE_OPENAI_ENDPOINT is not set!")
        return

    # Check SambaNova API key
    if not os.getenv("SAMBANOVA_API_KEY"):
        print("❌ SAMBANOVA_API_KEY is not set!")
        return

    # Check W&B API key
    if not os.getenv("WANDB_API_KEY"):
        print("⚠️  WANDB_API_KEY is not set - Weave tracking may not work")

    print("✓ All credentials configured")
    print()

    # Get components
    loader = get_dataset_loader()
    if not loader:
        print("❌ Dataset not found!")
        return

    analyzer = get_vision_analyzer()
    if not analyzer:
        print("❌ Vision analyzer not available!")
        return

    evaluator = get_evaluator()
    if not evaluator:
        print("❌ Evaluator not available!")
        return

    print("✓ All components initialized")
    print()

    # Get first video
    videos = loader.get_all_videos()
    test_video = videos[0]
    print(f"Testing with video: {test_video}")
    print("-" * 70)

    # Load first 2 frames
    sequence = loader.load_sequence(test_video, load_images=False)
    test_frames = sequence[:2]

    print(f"Analyzing and evaluating {len(test_frames)} frames...")
    print()

    # Analyze and evaluate each frame
    for i, frame in enumerate(test_frames):
        print(f"Frame {i+1}/{len(test_frames)}")
        print(f"  Image: {frame['frame_id']}")

        # Step 1: Analyze with Vision
        try:
            vision_result = analyzer.analyze_frame(frame['image_path'])

            if "error" in vision_result:
                print(f"  ❌ Vision analysis error: {vision_result['error']}")
                continue

            print(f"  ✓ Vision analysis:")
            print(f"    Step: {vision_result.get('step', 'Unknown')}")
            print(f"    Instruments: {', '.join(vision_result.get('instruments', []))}")
            print(f"    Risk: {vision_result.get('risk', 'Unknown')}")

            # Step 2: Evaluate with Judge
            eval_result = evaluator.judge_vision_result(
                step=vision_result.get("step", "Unknown"),
                instruments=vision_result.get("instruments", []),
                risk=vision_result.get("risk", "Unknown"),
                description=vision_result.get("description", "")
            )

            if "error" in eval_result:
                print(f"  ❌ Evaluation error: {eval_result['error']}")
                continue

            print(f"  ✓ Evaluation scores:")
            print(f"    Medical Accuracy: {eval_result.get('medical_accuracy', 0)}/5")
            print(f"    Guideline Compliance: {eval_result.get('guideline_compliance', 0)}/5")
            print(f"    Clarity: {eval_result.get('clarity', 0)}/5")
            print(f"    Educational Value: {eval_result.get('educational_value', 0)}/5")
            print(f"    Total Score: {eval_result.get('total_score', 0)}/20")
            print(f"  Feedback: {eval_result.get('feedback', 'なし')}")

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            import traceback
            traceback.print_exc()

        print()

    print("=" * 70)
    print("✓ Evaluation test completed!")
    print()
    print("🔗 View traces in W&B Weave:")
    print("   https://wandb.ai/<entity>/<project>/weave")


if __name__ == "__main__":
    main()
