"""Test script for Vision Analysis"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from app.vision import VisionAnalyzer, get_vision_analyzer
from app.dataset import get_dataset_loader

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def main():
    print("Testing Vision Analysis with cholecSeg8k Dataset...")
    print("=" * 60)

    # Check if API key is set
    api_key = os.getenv("SAMBANOVA_API_KEY")
    if not api_key:
        print("❌ SAMBANOVA_API_KEY is not set!")
        print("Please set your API key in .env file:")
        print("  SAMBANOVA_API_KEY=your_api_key_here")
        return

    # Load dataset
    loader = get_dataset_loader()
    if not loader:
        print("❌ Dataset not found!")
        return

    print("✓ Dataset loaded")
    print()

    # Get analyzer
    try:
        analyzer = get_vision_analyzer()
        if not analyzer:
            print("❌ Failed to create VisionAnalyzer")
            return
        print("✓ VisionAnalyzer initialized")
        print()
    except Exception as e:
        print(f"❌ Error initializing VisionAnalyzer: {e}")
        return

    # Get first video
    videos = loader.get_all_videos()
    test_video = videos[0]
    print(f"Testing with video: {test_video}")
    print("-" * 60)

    # Load sequence (without loading actual images to save memory)
    sequence = loader.load_sequence(test_video, load_images=False)

    if not sequence:
        print("❌ No frames found!")
        return

    # Test with first 3 frames
    print(f"Analyzing first 3 frames...")
    print()

    for i in range(min(3, len(sequence))):
        frame = sequence[i]
        image_path = frame['image_path']

        print(f"Frame {i+1}/{min(3, len(sequence))}")
        print(f"  Path: {image_path}")

        try:
            # Analyze frame
            result = analyzer.analyze_frame(image_path)

            # Display results
            if "error" in result:
                print(f"  ❌ Error: {result['error']}")
                if "raw_content" in result:
                    print(f"  Raw response: {result['raw_content'][:200]}...")
            else:
                print(f"  ✓ Analysis successful")
                print(f"    Step: {result.get('step', 'Unknown')}")
                print(f"    Instruments: {', '.join(result.get('instruments', []))}")
                print(f"    Risk: {result.get('risk', 'Unknown')}")
                print(f"    Description: {result.get('description', 'N/A')}")

            print()

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            print()
            import traceback
            traceback.print_exc()
            break

    print("=" * 60)
    print("✓ Vision analysis test completed!")


if __name__ == "__main__":
    main()
