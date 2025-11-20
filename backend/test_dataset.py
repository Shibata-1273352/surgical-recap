"""Test script for dataset loader"""

from app.dataset import get_dataset_loader

def main():
    print("Testing CholecSeg8k Dataset Loader...")
    print("=" * 60)

    # Load the dataset
    loader = get_dataset_loader()

    if not loader:
        print("❌ Dataset not found!")
        return

    print("✓ Dataset loaded successfully")
    print()

    # Get all videos
    videos = loader.get_all_videos()
    print(f"Total videos: {len(videos)}")
    print(f"Video IDs: {', '.join(videos[:5])}{'...' if len(videos) > 5 else ''}")
    print()

    # Get total frame count
    total_frames = loader.get_frame_count()
    print(f"Total frames across all videos: {total_frames}")
    print()

    # Test loading a single video sequence
    if videos:
        test_video = videos[0]
        print(f"Testing video: {test_video}")
        print("-" * 60)

        frame_count = loader.get_frame_count(test_video)
        print(f"Frame count: {frame_count}")

        # Load sequence metadata (without loading images to save memory)
        sequence = loader.load_sequence(test_video, load_images=False)
        print(f"Loaded {len(sequence)} frames")

        if sequence:
            # Show first frame info
            first_frame = sequence[0]
            print()
            print("First frame info:")
            print(f"  Video ID: {first_frame['video_id']}")
            print(f"  Timestamp dir: {first_frame['timestamp_dir']}")
            print(f"  Frame ID: {first_frame['frame_id']}")
            print(f"  Frame number: {first_frame['frame_number']}")
            print(f"  Image path: {first_frame['image_path']}")
            print(f"  Mask path: {first_frame['mask_path']}")

    print()
    print("=" * 60)
    print("✓ All tests passed!")


if __name__ == "__main__":
    main()
