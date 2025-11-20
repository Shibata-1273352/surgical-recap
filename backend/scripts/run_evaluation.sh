#!/bin/bash

# Surgical-Recap Evaluation Script
# Run vision analysis and evaluation pipeline end-to-end

set -e  # Exit on error

# Get the script directory and backend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$BACKEND_DIR/.." && pwd)"

# Load environment variables from .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
elif [ -f "$BACKEND_DIR/.env" ]; then
    export $(cat "$BACKEND_DIR/.env" | grep -v '^#' | xargs)
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
FRAMES=3
VIDEO_INDEX=0
WITH_IMAGES=false
EVALUATION_SCRIPT="test_weave_evals.py"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--frames)
            FRAMES="$2"
            shift 2
            ;;
        -v|--video)
            VIDEO_INDEX="$2"
            shift 2
            ;;
        -i|--with-images)
            WITH_IMAGES=true
            EVALUATION_SCRIPT="test_weave_images_correct.py"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -f, --frames N       Number of frames to evaluate (default: 3)"
            echo "  -v, --video INDEX    Video index to use (default: 0)"
            echo "  -i, --with-images    Include images in evaluation results"
            echo "  -h, --help           Show this help message"
            echo ""
            echo "Environment variables required:"
            echo "  SAMBANOVA_API_KEY       SambaNova Cloud API key"
            echo "  AZURE_OPENAI_API_KEY    Azure OpenAI API key"
            echo "  AZURE_OPENAI_ENDPOINT   Azure OpenAI endpoint"
            echo "  WANDB_API_KEY           Weights & Biases API key"
            echo ""
            echo "Example:"
            echo "  $0 --frames 5 --video 0"
            echo "  $0 --frames 10 --with-images"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Print banner
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Surgical-Recap Evaluation Pipeline${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check environment variables
echo -e "${YELLOW}[1/5] Checking environment variables...${NC}"
MISSING_VARS=0

if [ -z "$SAMBANOVA_API_KEY" ]; then
    echo -e "${RED}  ❌ SAMBANOVA_API_KEY is not set${NC}"
    MISSING_VARS=1
fi

if [ -z "$AZURE_OPENAI_API_KEY" ]; then
    echo -e "${RED}  ❌ AZURE_OPENAI_API_KEY is not set${NC}"
    MISSING_VARS=1
fi

if [ -z "$AZURE_OPENAI_ENDPOINT" ]; then
    echo -e "${RED}  ❌ AZURE_OPENAI_ENDPOINT is not set${NC}"
    MISSING_VARS=1
fi

if [ -z "$WANDB_API_KEY" ]; then
    echo -e "${YELLOW}  ⚠️  WANDB_API_KEY is not set - Weave tracking may not work${NC}"
fi

if [ $MISSING_VARS -eq 1 ]; then
    echo ""
    echo -e "${RED}Error: Missing required environment variables${NC}"
    echo "Please set them in .env file or export them before running this script"
    exit 1
fi

echo -e "${GREEN}  ✓ All required credentials configured${NC}"
echo ""

# Check if dataset exists
echo -e "${YELLOW}[2/5] Checking dataset...${NC}"

DATASET_PATH="$BACKEND_DIR/data/cholecseg8k"
if [ ! -d "$DATASET_PATH" ]; then
    echo -e "${RED}  ❌ Dataset not found at $DATASET_PATH${NC}"
    echo -e "${YELLOW}  Run 'uv run python scripts/download_dataset.py' first${NC}"
    exit 1
fi

VIDEO_DIR="$DATASET_PATH/video01"
if [ ! -d "$VIDEO_DIR" ]; then
    echo -e "${RED}  ❌ Video directory not found${NC}"
    exit 1
fi

FRAME_COUNT=$(find "$VIDEO_DIR" -name "*.jpg" -o -name "*.png" | wc -l)
echo -e "${GREEN}  ✓ Dataset found: $FRAME_COUNT frames available${NC}"

if [ $FRAMES -gt $FRAME_COUNT ]; then
    echo -e "${YELLOW}  ⚠️  Requested $FRAMES frames, but only $FRAME_COUNT available${NC}"
    echo -e "${YELLOW}  Using $FRAME_COUNT frames instead${NC}"
    FRAMES=$FRAME_COUNT
fi
echo ""

# Show evaluation settings
echo -e "${YELLOW}[3/5] Evaluation settings:${NC}"
echo -e "  Frames to evaluate: ${GREEN}$FRAMES${NC}"
echo -e "  Video index: ${GREEN}$VIDEO_INDEX${NC}"
echo -e "  Include images: ${GREEN}$WITH_IMAGES${NC}"
echo -e "  Evaluation script: ${GREEN}$EVALUATION_SCRIPT${NC}"
echo ""

# Estimate time and cost
ESTIMATED_TIME=$((FRAMES * 2))  # ~2 seconds per frame
ESTIMATED_COST=$(echo "scale=2; $FRAMES * 0.01" | bc)  # ~$0.01 per frame
echo -e "${BLUE}📊 Estimates:${NC}"
echo -e "  Time: ~${ESTIMATED_TIME} seconds"
echo -e "  Cost: ~\$$ESTIMATED_COST (Azure OpenAI)"
echo ""

# Confirmation
echo -e "${YELLOW}Press Enter to continue, or Ctrl+C to cancel...${NC}"
read -r

# Create temporary Python script with custom frame count
echo -e "${YELLOW}[4/5] Preparing evaluation...${NC}"

TEMP_SCRIPT="$BACKEND_DIR/.run_evaluation_temp.py"
cat > "$TEMP_SCRIPT" << EOF
"""Temporary evaluation script with custom settings"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import weave

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
load_dotenv(dotenv_path=Path(__file__).parent / ".env" if (Path(__file__).parent / ".env").exists() else Path(__file__).parent.parent / ".env")

async def main():
    # Settings from shell script
    FRAMES = int(os.environ.get('EVAL_FRAMES', '3'))
    VIDEO_INDEX = int(os.environ.get('EVAL_VIDEO_INDEX', '0'))
    WITH_IMAGES = os.environ.get('EVAL_WITH_IMAGES', 'false') == 'true'

    print("Surgical-Recap Evaluation")
    print("=" * 70)

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

    print("✓ Dataset loaded")

    # Get vision analyzer
    analyzer = get_vision_analyzer()
    if not analyzer:
        print("❌ Vision analyzer not available!")
        return

    print("✓ Vision analyzer initialized")
    print()

    # Prepare evaluation dataset
    videos = loader.get_all_videos()
    if VIDEO_INDEX >= len(videos):
        print(f"❌ Video index {VIDEO_INDEX} out of range (0-{len(videos)-1})")
        return

    test_video = videos[VIDEO_INDEX]
    sequence = loader.load_sequence(test_video, load_images=False)

    # Create evaluation dataset
    eval_dataset = []
    for i in range(min(FRAMES, len(sequence))):
        frame = sequence[i]
        eval_dataset.append({
            "input": frame['image_path'],
            "frame_id": frame['frame_id'],
        })

    print(f"📊 Evaluation Dataset: {len(eval_dataset)} frames from {test_video}")
    print("-" * 70)
    print()
    print("🚀 Running evaluation...")
    print()

    try:
        results = await run_evaluation(
            dataset=eval_dataset,
            analyzer=analyzer,
            scorers=[
                medical_accuracy_scorer,
                guideline_compliance_scorer,
                clarity_scorer,
                educational_value_scorer,
                total_score_scorer
            ]
        )

        print()
        print("=" * 70)
        print("✓ Evaluation completed!")
        print()
        print("📈 Results:")
        print()

        # Pretty print results
        for scorer_name, metrics in results.items():
            if scorer_name == 'model_latency':
                print(f"  ⏱️  Model Latency: {metrics['mean']:.2f}s")
            else:
                for metric_name, values in metrics.items():
                    mean_value = values['mean']
                    if 'accuracy' in metric_name or 'compliance' in metric_name or 'clarity' in metric_name or 'value' in metric_name:
                        print(f"  📊 {metric_name.replace('_', ' ').title()}: {mean_value:.2f}/5")
                    elif 'score' in metric_name:
                        print(f"  📊 {metric_name.replace('_', ' ').title()}: {mean_value:.2f}/20")

        print()
        print("🔗 View detailed results:")
        print(f"   https://wandb.ai/{entity}/{project}/weave")
        print()

    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
EOF

echo -e "${GREEN}  ✓ Evaluation prepared${NC}"
echo ""

# Run evaluation
echo -e "${YELLOW}[5/5] Running evaluation pipeline...${NC}"
echo ""

# Export settings as environment variables
export EVAL_FRAMES=$FRAMES
export EVAL_VIDEO_INDEX=$VIDEO_INDEX
export EVAL_WITH_IMAGES=$WITH_IMAGES

# Change to backend directory and run
cd "$BACKEND_DIR" || exit 1

if uv run python "$TEMP_SCRIPT"; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ Evaluation completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"

    # Cleanup
    rm -f "$TEMP_SCRIPT"

    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ❌ Evaluation failed!${NC}"
    echo -e "${RED}========================================${NC}"

    # Cleanup
    rm -f "$TEMP_SCRIPT"

    exit 1
fi
