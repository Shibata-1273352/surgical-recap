"""
Test script for two-stage filtering system using test.mp4
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.vision import VisionAnalyzer
from app.analize_sequence.pipeline import TwoStagePipeline

def main():
    # Setup
    test_frames_dir = Path("app/analize_sequence/test_frames")
    frame_paths = sorted(list(test_frames_dir.glob("frame_*.jpg")))

    print(f"Found {len(frame_paths)} frames")
    print(f"First frame: {frame_paths[0]}")
    print(f"Last frame: {frame_paths[-1]}")
    print()

    # Initialize vision analyzer
    print("Initializing VisionAnalyzer...")
    analyzer = VisionAnalyzer()
    print("✓ VisionAnalyzer initialized")
    print()

    # Create pipeline
    print("Creating TwoStagePipeline...")
    pipeline = TwoStagePipeline(
        vision_analyzer=analyzer,
        window_size=5,
        overlap=2
    )
    print("✓ TwoStagePipeline created")
    print()

    # Run two-stage filtering
    print("=" * 60)
    print("Running Two-Stage Filtering")
    print("=" * 60)

    manifest, final_manifest = pipeline.process(
        video_id="test_video",
        frame_paths=[str(p) for p in frame_paths],
        job_id="test_job_001"
    )

    # Print Stage1 results
    print()
    print("=" * 60)
    print("Stage1 Results (DINOv3 Dummy)")
    print("=" * 60)
    print(f"Total frames: {manifest.total_frames}")
    print(f"Selected frames: {len(manifest.frames)}")
    print(f"Keep indices: {manifest.keep_indices}")
    print()

    for frame in manifest.frames:
        print(f"  Frame {frame.frame_number}: {frame.timestamp:.1f}s - {Path(frame.file_path).name}")

    # Print Stage2 results
    print()
    print("=" * 60)
    print("Stage2 Results (VLM Semantic Filtering)")
    print("=" * 60)
    print(f"Stage1 frame count: {final_manifest.stage1_frame_count}")
    print(f"Final selected count: {final_manifest.selected_frame_count}")
    print()

    for selected in final_manifest.selected_frames:
        print(f"  Frame {selected.global_index} (batch {selected.batch_id}, local {selected.local_index_in_batch})")
        print(f"    Path: {Path(selected.file_path).name}")

    # Analyze selected frames
    print()
    print("=" * 60)
    print("Analyzing Selected Frames")
    print("=" * 60)

    from app.vision import SURGICAL_VISION_SYSTEM_PROMPT, SURGICAL_VISION_USER_PROMPT

    for i, selected in enumerate(final_manifest.selected_frames):
        print(f"\n[{i+1}/{len(final_manifest.selected_frames)}] Analyzing frame {selected.global_index}...")

        try:
            result = analyzer.analyze_frame(
                image_path=selected.file_path,
                system_prompt=SURGICAL_VISION_SYSTEM_PROMPT,
                user_prompt=SURGICAL_VISION_USER_PROMPT
            )

            print(f"  Step: {result.get('step', 'N/A')}")
            print(f"  Instruments: {', '.join(result.get('instruments', []))}")
            print(f"  Risk: {result.get('risk', 'N/A')}")
            print(f"  Description: {result.get('description', 'N/A')}")

        except Exception as e:
            print(f"  Error: {e}")

    print()
    print("=" * 60)
    print("Test completed successfully! ✓")
    print("=" * 60)

if __name__ == "__main__":
    main()
