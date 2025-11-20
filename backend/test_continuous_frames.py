"""
Continuous frame evaluation WITHOUT using weave.Evaluation
This displays image thumbnails in the trace list view
"""

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

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def image_to_data_uri(image_path: str, max_size: int = 150) -> str:
    """Convert image to Data URI for thumbnails"""
    with Image.open(image_path) as img:
        img.thumbnail((max_size, max_size))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"


@weave.op()
async def surgical_vision_model_with_image(input: dict) -> dict:
    """Model function with dict input containing image"""
    analyzer = get_vision_analyzer()
    result = analyzer.analyze_frame(input['image_path'])
    result['input_image'] = input['image']
    result['image_path'] = input['image_path']
    result['frame_id'] = input.get('frame_id', 'unknown')
    return result


async def main():
    # Parse command line arguments
    num_frames = 5  # Default
    video_index = 0  # Default

    if len(sys.argv) > 1:
        try:
            num_frames = int(sys.argv[1])
        except ValueError:
            print("Usage: python test_continuous_frames.py [num_frames] [video_index]")
            print("  num_frames: Number of frames to evaluate (default: 5)")
            print("  video_index: Video index to use (default: 0)")
            sys.exit(1)

    if len(sys.argv) > 2:
        try:
            video_index = int(sys.argv[2])
        except ValueError:
            print("Error: video_index must be an integer")
            sys.exit(1)

    print("🔬 Continuous Frame Evaluation (Image Thumbnails in Trace List)")
    print("="*70)
    print(f"Frames to process: {num_frames}")
    print(f"Video index: {video_index}")
    print("="*70)

    # Initialize Weave
    entity = os.getenv("WANDB_ENTITY", "takasi-shibata")
    project = os.getenv("WANDB_PROJECT", "surgical-recap")
    weave.init(f"{entity}/{project}")
    print(f"✓ Weave initialized: {entity}/{project}")
    print()

    # Load dataset
    loader = get_dataset_loader()
    if not loader:
        print("❌ Dataset not found!")
        return

    videos = loader.get_all_videos()

    if video_index >= len(videos):
        print(f"❌ Video index {video_index} out of range (0-{len(videos)-1})")
        return

    test_video = videos[video_index]
    sequence = loader.load_sequence(test_video, load_images=False)
    frames_to_process = min(num_frames, len(sequence))

    print(f"✓ Dataset loaded: {test_video}")
    print(f"✓ Processing {frames_to_process} frames")
    if num_frames > len(sequence):
        print(f"⚠️  Requested {num_frames} frames, but only {len(sequence)} available")
    print()

    # Get vision analyzer
    analyzer = get_vision_analyzer()
    if not analyzer:
        print("❌ Vision analyzer not available!")
        return

    print("✓ Vision analyzer initialized")
    print()

    # Process frames one by one (NOT using Evaluation)
    print("🚀 Processing frames...")
    print("-"*70)

    results = []
    for i in range(frames_to_process):
        frame = sequence[i]

        # Prepare input with image
        input_dict = {
            "image": image_to_data_uri(frame['image_path'], max_size=150),
            "image_path": frame['image_path'],
            "frame_id": frame['frame_id']
        }

        # Call model
        result = await surgical_vision_model_with_image(input_dict)
        results.append(result)

        print(f"  ✓ {i+1}/{frames_to_process}: {result['frame_id']} - {result.get('step', 'Unknown')}")

    print("-"*70)
    print()
    print("="*70)
    print("✅ All frames processed!")
    print("="*70)
    print()
    print(f"📊 Processed {len(results)} frames from {test_video}")
    print()
    print("="*70)
    print("🖼️  画像サムネイルの確認方法")
    print("="*70)
    print()
    print("【Tracesページで確認（画像サムネイル表示）】")
    print(f"   https://wandb.ai/{entity}/{project}/weave/traces")
    print()
    print("   1. 上のリンクを開く")
    print("   2. フィルターで 'surgical_vision_model_with_image' を選択")
    print(f"   3. 最新の{frames_to_process}つのトレース一覧のInputカラムに画像サムネイル表示")
    print()
    print("💡 このスクリプトはEvaluationを使わないため、")
    print("   トレース一覧に画像サムネイルが表示されます！")
    print()


if __name__ == "__main__":
    asyncio.run(main())
