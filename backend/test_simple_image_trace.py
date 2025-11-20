"""
Simple test to verify image thumbnails in trace list
Directly calls the model without using Evaluation
"""

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

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def image_to_data_uri(image_path: str, max_size: int = 150) -> str:
    """Convert image to Data URI"""
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
    print("🔬 Simple Image Trace Test")
    print("="*70)

    # Initialize Weave
    entity = os.getenv("WANDB_ENTITY", "takasi-shibata")
    project = os.getenv("WANDB_PROJECT", "surgical-recap")
    weave.init(f"{entity}/{project}")
    print(f"✓ Weave initialized: {entity}/{project}")
    print()

    # Load dataset
    loader = get_dataset_loader()
    videos = loader.get_all_videos()
    sequence = loader.load_sequence(videos[0], load_images=False)

    # Get first 2 frames
    frames = sequence[:2]

    print(f"📊 Testing with {len(frames)} frames")
    print()

    # Call model with dict input containing image
    for i, frame in enumerate(frames, 1):
        print(f"Processing frame {i}...", end=" ")

        input_dict = {
            "image": image_to_data_uri(frame['image_path'], max_size=150),
            "image_path": frame['image_path'],
            "frame_id": frame['frame_id']
        }

        result = await surgical_vision_model_with_image(input_dict)
        print(f"✓ {result['frame_id']}")

    print()
    print("="*70)
    print("✅ Test completed!")
    print()
    print("🔗 View traces at:")
    print(f"   https://wandb.ai/{entity}/{project}/weave/traces")
    print()
    print("📝 How to check:")
    print("   1. Click on the link above")
    print("   2. Look for 'surgical_vision_model_with_image' traces")
    print("   3. Check the 'Input' column - you should see image thumbnails")
    print()


if __name__ == "__main__":
    asyncio.run(main())
