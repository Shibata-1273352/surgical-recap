"""
Experimental script to test different methods of displaying image thumbnails in Weave trace lists

This script tests multiple approaches:
1. Using dict input with image field
2. Using weave.Image type (if available)
3. Returning image in specific fields
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


def image_to_data_uri(image_path: str, max_size: int = 200) -> str:
    """Convert image to small Data URI for thumbnails"""
    with Image.open(image_path) as img:
        img.thumbnail((max_size, max_size))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"


# Approach 1: Dict input with image field
@weave.op()
async def model_with_dict_input(input: dict) -> dict:
    """Model that takes dict input including image"""
    analyzer = get_vision_analyzer()
    result = analyzer.analyze_frame(input['image_path'])
    result['input_image'] = input['image']
    return result


# Approach 2: String input, but return image in 'image' field
@weave.op()
async def model_with_image_field(input: str) -> dict:
    """Model that returns result with 'image' field (not 'image_url')"""
    analyzer = get_vision_analyzer()
    result = analyzer.analyze_frame(input)
    result['image'] = image_to_data_uri(input, max_size=150)  # Smaller thumbnail
    result['image_path'] = input
    return result


# Approach 3: Original approach (for comparison)
@weave.op()
async def model_original(input: str) -> dict:
    """Original approach with image_url field"""
    analyzer = get_vision_analyzer()
    result = analyzer.analyze_frame(input)
    result['image_url'] = image_to_data_uri(input, max_size=200)
    result['image_path'] = input
    return result


# Approach 4: Return image at top level
@weave.op()
async def model_image_toplevel(input: str) -> dict:
    """Model that puts image at top level of output"""
    analyzer = get_vision_analyzer()
    result = analyzer.analyze_frame(input)

    # Create output with image at top level
    output = {
        "image": image_to_data_uri(input, max_size=150),
        "analysis": result,
        "image_path": input
    }
    return output


async def test_approach(approach_num: int, model_func, dataset, description: str):
    """Test a specific approach"""
    print(f"\n{'='*70}")
    print(f"🧪 Approach {approach_num}: {description}")
    print('='*70)

    try:
        # Call model for each item
        for item in dataset:
            if isinstance(item, dict) and 'input' in item:
                result = await model_func(item['input'])
            else:
                result = await model_func(item)
            print(f"✓ Processed: {result.get('image_path', 'unknown')[:50]}...")

        print(f"✓ Approach {approach_num} completed successfully")

    except Exception as e:
        print(f"❌ Approach {approach_num} failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    print("🔬 Testing Image Thumbnail Display in Weave Traces")
    print("="*70)

    # Initialize Weave
    entity = os.getenv("WANDB_ENTITY", "takasi-shibata")
    project = os.getenv("WANDB_PROJECT", "surgical-recap")
    weave.init(f"{entity}/{project}")
    print("✓ Weave initialized")

    # Load dataset
    loader = get_dataset_loader()
    if not loader:
        print("❌ Dataset not found!")
        return

    videos = loader.get_all_videos()
    test_video = videos[0]
    sequence = loader.load_sequence(test_video, load_images=False)

    # Get just 2 frames for quick testing
    frames = sequence[:2]

    print(f"✓ Dataset loaded: {len(frames)} frames")
    print()

    # Test Approach 1: Dict input with image
    print("\n" + "="*70)
    print("Testing Approach 1: Dict input with embedded image")
    print("="*70)
    dataset_1 = []
    for frame in frames:
        dataset_1.append({
            'image_path': frame['image_path'],
            'image': image_to_data_uri(frame['image_path'], max_size=150),
            'frame_id': frame['frame_id']
        })

    await test_approach(
        1,
        model_with_dict_input,
        dataset_1,
        "Dict input with 'image' field"
    )

    # Test Approach 2: 'image' field in output
    print("\n" + "="*70)
    print("Testing Approach 2: Output with 'image' field")
    print("="*70)
    dataset_2 = [frame['image_path'] for frame in frames]
    await test_approach(
        2,
        model_with_image_field,
        dataset_2,
        "Return 'image' field in output"
    )

    # Test Approach 3: Original 'image_url' field
    print("\n" + "="*70)
    print("Testing Approach 3: Original 'image_url' field")
    print("="*70)
    dataset_3 = [frame['image_path'] for frame in frames]
    await test_approach(
        3,
        model_original,
        dataset_3,
        "Return 'image_url' field in output"
    )

    # Test Approach 4: Image at top level
    print("\n" + "="*70)
    print("Testing Approach 4: Image at top level of output")
    print("="*70)
    dataset_4 = [frame['image_path'] for frame in frames]
    await test_approach(
        4,
        model_image_toplevel,
        dataset_4,
        "Image at top level with nested analysis"
    )

    # Summary
    print("\n" + "="*70)
    print("✅ All approaches tested!")
    print("="*70)
    print()
    print("📊 Results:")
    print(f"   View traces at: https://wandb.ai/{entity}/{project}/weave")
    print()
    print("🔍 How to check:")
    print("   1. Open the Weave Traces tab")
    print("   2. Look for the trace list view")
    print("   3. Check if any approach shows image thumbnails in the list")
    print()
    print("📝 Expected behaviors:")
    print("   - Approach 1: Dict input might show image in input preview")
    print("   - Approach 2: 'image' field might be recognized by Weave")
    print("   - Approach 3: 'image_url' (current method)")
    print("   - Approach 4: Top-level image field")
    print()
    print("⚠️  Note: Weave may not support thumbnails in trace list view.")
    print("   Images might only be visible in the detailed trace view.")


if __name__ == "__main__":
    asyncio.run(main())
