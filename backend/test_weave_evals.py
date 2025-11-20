"""Test script for W&B Weave Evaluations"""

import os
import sys
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


@weave.op()
async def surgical_vision_model_with_image(input: dict) -> dict:
    """
    Surgical vision model that returns analysis with inline image

    Args:
        input: Dictionary containing 'image', 'image_path', and 'frame_id'

    Returns:
        Dictionary with analysis results AND input image
    """
    analyzer = get_vision_analyzer()
    result = analyzer.analyze_frame(input['image_path'])

    # Include the input image in the output for traceability
    result['input_image'] = input['image']
    result['image_path'] = input['image_path']
    result['frame_id'] = input.get('frame_id', 'unknown')

    return result


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
    # Parse command line arguments
    num_frames = 3  # Default
    video_index = 0  # Default

    if len(sys.argv) > 1:
        try:
            num_frames = int(sys.argv[1])
        except ValueError:
            print("Usage: python test_weave_evals.py [num_frames] [video_index]")
            print("  num_frames: Number of frames to evaluate (default: 3)")
            print("  video_index: Video index to use (default: 0)")
            sys.exit(1)

    if len(sys.argv) > 2:
        try:
            video_index = int(sys.argv[2])
        except ValueError:
            print("Error: video_index must be an integer")
            sys.exit(1)

    print("Testing W&B Weave Evaluations...")
    print("=" * 70)
    print(f"Frames to evaluate: {num_frames}")
    print(f"Video index: {video_index}")
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

    # Prepare evaluation dataset
    videos = loader.get_all_videos()

    if video_index >= len(videos):
        print(f"❌ Video index {video_index} out of range (0-{len(videos)-1})")
        return

    test_video = videos[video_index]
    sequence = loader.load_sequence(test_video, load_images=False)

    # Create evaluation dataset
    # IMPORTANT: Use 'input' key for Weave Evaluations compatibility
    # Approach 1: Dict input with embedded image for thumbnail display in trace list
    eval_dataset = []
    frames_to_process = min(num_frames, len(sequence))

    print(f"📊 Evaluation Dataset: {frames_to_process} frames from {test_video}")
    if num_frames > len(sequence):
        print(f"⚠️  Requested {num_frames} frames, but only {len(sequence)} available")
    print("-" * 70)

    for i in range(frames_to_process):
        frame = sequence[i]
        eval_dataset.append({
            "input": {
                "image": image_to_data_uri(frame['image_path'], max_size=150),  # Small thumbnail for list view
                "image_path": frame['image_path'],
                "frame_id": frame['frame_id']
            },
            # Optional: Add reference answers if you have ground truth
            # "reference_answer": {
            #     "step": "Dissection",
            #     "instruments": ["Grasper"],
            #     "risk": "Low"
            # }
        })

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
        print("=" * 70)
        print("🖼️  画像サムネイルの確認方法")
        print("=" * 70)
        entity = os.getenv("WANDB_ENTITY", "takasi-shibata")
        project = os.getenv("WANDB_PROJECT", "surgical-recap")
        print()
        print("【方法1: Tracesページで確認（推奨）】")
        print(f"   https://wandb.ai/{entity}/{project}/weave/traces")
        print()
        print("   1. 上のリンクを開く")
        print("   2. フィルターで 'surgical_vision_model_with_image' を選択")
        print(f"   3. 最新の{frames_to_process}つのトレースのInputカラムに画像サムネイル表示")
        print()
        print("【方法2: Evaluationsページから】")
        print(f"   https://wandb.ai/{entity}/{project}/weave")
        print()
        print("   1. 'Evaluations' タブをクリック")
        print("   2. 最新のEvaluationをクリック")
        print("   3. 'Calls' または 'Child Calls' セクションを探す")
        print("   4. 'surgical_vision_model_with_image' の呼び出しをクリック")
        print("   5. Inputセクションで画像を確認")
        print()
        print("💡 注意: Evaluationのサマリー画面には画像は表示されません")
        print("   個別のトレース（surgical_vision_model_with_image）を見る必要があります")

    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
