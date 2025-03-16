#!/bin/bash

# === USAGE FUNCTION ===
usage() {
  echo "Usage: $0 INPUT_VIDEO [OUTPUT_VIDEO]"
  echo "  INPUT_VIDEO: Path to the input video file to be edited"
  echo "  OUTPUT_VIDEO: (Optional) Path for the output video file (default: final_output.mp4)"
  exit 1
}

# === HANDLE COMMAND LINE ARGUMENTS ===
# Check if at least input video is provided
if [ $# -lt 1 ]; then
  echo "Error: Input video file is required"
  usage
fi

# Set input video from first argument
INPUT_VIDEO="$1"

# Check if input file exists
if [ ! -f "$INPUT_VIDEO" ]; then
  echo "Error: Input video file '$INPUT_VIDEO' not found"
  exit 1
fi

# Set output video from second argument or use default
OUTPUT_VIDEO="${2:-final_output.mp4}"

# === CONFIGURATION ===
# List of cuts: format "start_time end_time"
# Add as many as you want, following the "start end" pattern
CUTS=(
  "00:00:10 00:00:30"
  "00:01:00 00:01:20"
  "00:02:15 00:02:45"
)

# === SCRIPT START ===
echo "Input video: $INPUT_VIDEO"
echo "Output video: $OUTPUT_VIDEO"

# Create a temporary directory to store cut parts
TMP_DIR="video_parts"
mkdir -p "$TMP_DIR"

# Remove any existing mylist.txt
LIST_FILE="mylist.txt"
> "$LIST_FILE"

# Counter for naming parts
COUNT=1

echo "Cutting parts from $INPUT_VIDEO..."

# Loop over CUTS and create individual parts
for TIME_RANGE in "${CUTS[@]}"; do
  START=$(echo $TIME_RANGE | cut -d' ' -f1)
  END=$(echo $TIME_RANGE | cut -d' ' -f2)
  PART="$TMP_DIR/part$COUNT.mp4"

  echo "Cutting from $START to $END -> $PART"
  ffmpeg -y -i "$INPUT_VIDEO" -ss "$START" -to "$END" -c copy "$PART"

  # Add to list file for concatenation
  echo "file '$PART'" >> "$LIST_FILE"

  COUNT=$((COUNT + 1))
done

# === CONCATENATE PARTS ===

echo "Combining parts into $OUTPUT_VIDEO..."
ffmpeg -f concat -safe 0 -i "$LIST_FILE" -c copy "$OUTPUT_VIDEO"

echo "✅ Done! Final video saved as $OUTPUT_VIDEO"

# Clean up temporary files
echo "Cleaning up temporary files..."
rm -rf "$TMP_DIR" "$LIST_FILE"
