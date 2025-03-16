import subprocess
import json
import os
import datetime
import argparse

def generate_shot_list(raw_footage_info):
    """
    Simulates an LLM-generated shot list based on raw footage metadata.
    In a real-world scenario, this might involve calling an LLM API.
    
    Returns a dictionary (could be in JSON format) that defines the film sequence.
    """
    shot_list = {
        "shots": [
            {
                "filename": "clip1.mp4",
                "start": "00:00:05",
                "end": "00:00:20",
                "transition": "fade"  # Placeholder for transition type
            },
            {
                "filename": "clip2.mp4",
                "start": "00:00:10",
                "end": "00:00:30",
                "transition": "dissolve"
            }
            # Add additional shots as needed.
        ],
        "audio": {
            "bgm": "bgm.mp3",  # Background music
            "sound_effects": []  # List additional sound effects if necessary.
        }
    }
    return shot_list

def run_ffmpeg_command(command):
    """
    Helper function to run an FFmpeg command.
    """
    print("Running command:", " ".join(command))
    subprocess.run(command, check=True)

def trim_video(input_file, start_time, end_time, output_file):
    """
    Trims the input video based on start and end times.
    Uses FFmpeg's copy codec to avoid re-encoding if possible.
    """
    command = [
        "ffmpeg", "-y", "-i", input_file,
        "-ss", start_time,
        "-to", end_time,
        "-c", "copy",
        output_file
    ]
    run_ffmpeg_command(command)
    return output_file

def add_transition(clip1, clip2, transition, output_file):
    """
    Adds a transition effect between two clips.
    
    For demonstration, this function simply concatenates two clips.
    A real implementation might use FFmpeg filter_complex to implement a fade or dissolve.
    """
    # This is a simplified version; real transitions require more advanced FFmpeg filters.
    command = [
        "ffmpeg", "-y",
        "-i", clip1,
        "-i", clip2,
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0",
        output_file
    ]
    run_ffmpeg_command(command)
    return output_file

def combine_clips(clip_files, output_file):
    """
    Combines multiple video clips into one file.
    
    Creates a temporary text file listing all the clips.
    """
    list_filename = "clips.txt"
    with open(list_filename, "w") as f:
        for clip in clip_files:
            f.write(f"file '{os.path.abspath(clip)}'\n")
    
    command = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_filename,
        "-c", "copy",
        output_file
    ]
    run_ffmpeg_command(command)
    os.remove(list_filename)
    return output_file

def add_audio(input_video, audio_file, output_file):
    """
    Adds background music or other audio to the combined video.
    
    This function maps the video from the input and the audio from the provided audio file.
    """
    command = [
        "ffmpeg", "-y", "-i", input_video, "-i", audio_file,
        "-c:v", "copy", "-c:a", "aac",
        "-map", "0:v:0", "-map", "1:a:0",
        output_file
    ]
    run_ffmpeg_command(command)
    return output_file


def get_video_resolution(video_file):
    """
    Gets the resolution of a video file using FFmpeg.
    
    Args:
        video_file: Path to the video file.
        
    Returns:
        A tuple of (width, height) as integers.
    """
    command = [
        "ffmpeg", "-i", video_file,
        "-hide_banner", "-loglevel", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        width, height = map(int, result.stdout.strip().split(','))
        return width, height
    except subprocess.CalledProcessError as e:
        print(f"Error getting video resolution: {e}")
        return None, None

def get_resolution_dimensions(resolution_name):
    """
    Converts a resolution name to width and height dimensions.
    
    Args:
        resolution_name: String like '1080p', '4k', '720p', etc.
        
    Returns:
        Tuple of (width, height) for the specified resolution.
    """
    resolutions = {
        '480p': (854, 480),
        '720p': (1280, 720),
        '1080p': (1920, 1080),
        '2k': (2048, 1080),
        '4k': (3840, 2160),
        '8k': (7680, 4320)
    }
    
    # Default to 1080p if resolution not found
    return resolutions.get(resolution_name.lower(), (1920, 1080))


def reverse_video(input_file, output_file, with_audio=False):
    """
    Reverses a video file using FFmpeg.
    
    Args:
        input_file: Path to the input video file.
        output_file: Path to save the reversed video.
        with_audio: Boolean indicating whether to reverse audio as well. Default is False.
        
    Returns:
        Path to the reversed video file.
    """
    import subprocess
    
    print(f"Reversing video: {input_file}")
    
    if with_audio:
        # Reverse both video and audio
        command = [
            "ffmpeg", "-y", "-i", input_file,
            "-vf", "reverse", "-af", "areverse",
            output_file
        ]
    else:
        # Reverse only video, keep audio as is (if any)     
        command = [
            "ffmpeg", "-y", "-i", input_file,
            "-vf", "reverse", "-c:a", "copy",
            output_file
        ]
    
    try:
        subprocess.run(command, check=True, capture_output=True)
        print(f"Successfully reversed video to: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error reversing video: {e}")
        print(f"Error output: {e.stderr.decode() if e.stderr else 'None'}")
        return None


def scale_video(input_file, output_file, target_resolution='1080p'):
    """
    Scales a video to the target resolution while maintaining aspect ratio.
    
    Args:
        input_file: Path to the input video file.
        output_file: Path to save the scaled video.
        target_resolution: String like '1080p', '4k', etc. Default is '1080p'.
    
    Returns:
        Path to the scaled video file.
    """
    target_width, target_height = get_resolution_dimensions(target_resolution)
    
    # Get current resolution
    current_width, current_height = get_video_resolution(input_file)
    
    if current_width is None or current_height is None:
        print(f"Could not determine resolution for {input_file}, skipping scaling")
        return input_file
    
    # Check if scaling is needed
    if current_width == target_width and current_height == target_height:
        print(f"Video {input_file} already at target resolution {target_resolution} ({target_width}x{target_height})")
        return input_file
    
    print(f"Scaling {input_file} from {current_width}x{current_height} to {target_resolution} ({target_width}x{target_height})")
    
    # Scale video maintaining aspect ratio with padding if needed
    command = [
        "ffmpeg", "-y", "-i", input_file,
        "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "copy",
        output_file
    ]
    
    run_ffmpeg_command(command)
    return output_file


def normalize_video_resolutions(video_files, output_dir, target_resolution='1080p'):
    """
    Ensures all videos in a list have the same resolution by scaling them as needed.
    
    Args:
        video_files: List of paths to video files.
        output_dir: Directory to save the scaled videos.
        target_resolution: String like '1080p', '4k', etc. Default is '1080p'.
    
    Returns:
        List of paths to the normalized video files.
    """
    os.makedirs(output_dir, exist_ok=True)
    normalized_files = []
    
    target_width, target_height = get_resolution_dimensions(target_resolution)
    
    for i, video_file in enumerate(video_files):
        width, height = get_video_resolution(video_file)
        
        if width is None or height is None:
            print(f"Skipping {video_file} due to resolution detection failure")
            normalized_files.append(video_file)
            continue
            
        if width == target_width and height == target_height:
            print(f"Video {video_file} already at target resolution {target_resolution}")
            normalized_files.append(video_file)
        else:
            output_file = os.path.join(output_dir, f"normalized_{i}_{os.path.basename(video_file)}")
            scaled_file = scale_video(video_file, output_file, target_resolution)
            normalized_files.append(scaled_file)
    
    return normalized_files


def add_noise_to_video(input_video_path, output_video_path, noise_strength=25):
    """
    Adds noise to the video using ffmpeg.

    Parameters:
    - input_video_path: str, path to the input video file
    - output_video_path: str, path where the output video will be saved
    - noise_strength: int, strength of the noise to be added (default is 25)
    """
    try:
        # Construct the ffmpeg command
        command = [
            "ffmpeg",
            "-i", input_video_path,
            "-vf", f"noise=c0s={noise_strength}:c0f=t+u:c1s=0:c1f=0:c2s=0:c2f=0",
            "-c:a", "copy",
            output_video_path
        ]

        # Execute the command
        subprocess.run(command, check=True)
        print(f"Noise added successfully to {output_video_path}")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")


def extract_video_metadata(video_file):
    """
    Extracts metadata from a single video file using ffmpeg.

    Args:
        video_file: Path to the video file.

    Returns:
        A dictionary containing clean, formatted metadata relevant for video editing.
    """
    # Get basic stream and format information
    command = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,bit_rate,size:stream=width,height,codec_name,codec_type,avg_frame_rate,display_aspect_ratio",
        "-of", "json", video_file
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        raw_metadata = json.loads(result.stdout)
        
        # Initialize a clean metadata dictionary
        metadata = {
            "filename": os.path.basename(video_file),
            "filepath": os.path.abspath(video_file),
            "filesize_mb": 0,
            "duration": 0,
            "resolution": "unknown",
            "aspect_ratio": "unknown",
            "video_codec": "unknown",
            "audio_codec": "unknown",
            "bitrate": "unknown",
            "fps": 0
        }
        
        # Extract format information
        if "format" in raw_metadata:
            format_info = raw_metadata["format"]
            
            # Duration in seconds
            if "duration" in format_info:
                duration_sec = float(format_info["duration"])
                metadata["duration"] = duration_sec
                
                # Format duration as HH:MM:SS
                hours, remainder = divmod(duration_sec, 3600)
                minutes, seconds = divmod(remainder, 60)
                metadata["duration_formatted"] = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            
            # File size in MB
            if "size" in format_info:
                size_bytes = int(format_info["size"])
                metadata["filesize_mb"] = round(size_bytes / (1024 * 1024), 2)
            
            # Bitrate in Mbps
            if "bit_rate" in format_info and format_info["bit_rate"].isdigit():
                bitrate_bps = int(format_info["bit_rate"])
                metadata["bitrate"] = f"{round(bitrate_bps / 1000000, 2)} Mbps"
        
        # Extract stream information
        if "streams" in raw_metadata:
            for stream in raw_metadata["streams"]:
                # Video stream
                if stream.get("codec_type") == "video":
                    # Resolution
                    if "width" in stream and "height" in stream:
                        width = stream["width"]
                        height = stream["height"]
                        metadata["resolution"] = f"{width}x{height}"
                        
                        # Determine common resolution name
                        if width >= 7680 and height >= 4320:
                            metadata["resolution_name"] = "8K"
                        elif width >= 3840 and height >= 2160:
                            metadata["resolution_name"] = "4K"
                        elif width >= 2560 and height >= 1440:
                            metadata["resolution_name"] = "2K"
                        elif width >= 1920 and height >= 1080:
                            metadata["resolution_name"] = "1080p"
                        elif width >= 1280 and height >= 720:
                            metadata["resolution_name"] = "720p"
                        elif width >= 854 and height >= 480:
                            metadata["resolution_name"] = "480p"
                        else:
                            metadata["resolution_name"] = "SD"
                    
                    # Aspect ratio
                    if "display_aspect_ratio" in stream:
                        metadata["aspect_ratio"] = stream["display_aspect_ratio"]
                    
                    # Video codec
                    if "codec_name" in stream:
                        metadata["video_codec"] = stream["codec_name"]
                    
                    # Frame rate
                    if "avg_frame_rate" in stream:
                        frame_rate = stream["avg_frame_rate"]
                        if "/" in frame_rate:
                            num, den = map(int, frame_rate.split("/"))
                            if den != 0:  # Avoid division by zero
                                metadata["fps"] = round(num / den, 2)
                
                # Audio stream
                elif stream.get("codec_type") == "audio":
                    # Audio codec
                    if "codec_name" in stream:
                        metadata["audio_codec"] = stream["codec_name"]
        
        return metadata
    
    except subprocess.CalledProcessError as e:
        print(f"Error extracting metadata from {video_file}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON metadata from {video_file}: {e}")
        return None

def extract_metadata_from_folder(folder_path, output_json=None):
    """
    Extracts metadata from all video files in a specified folder.

    Args:
        folder_path: Path to the folder containing video files.
        output_json: Optional path to save the JSON output file.

    Returns:
        A dictionary with clean metadata for all videos in the folder.
    """
    print(f"Scanning folder: {folder_path}")
    
    # Dictionary to store all video metadata
    all_metadata = {
        "folder": os.path.abspath(folder_path),
        "scan_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_videos": 0,
        "total_duration_seconds": 0,
        "videos": []
    }
    
    # Supported video extensions
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v')
    
    # Find all video files in the folder
    video_files = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(video_extensions):
            video_files.append(os.path.join(folder_path, filename))
    
    # Update total videos count
    all_metadata["total_videos"] = len(video_files)
    
    # Process each video file
    for i, video_path in enumerate(video_files):
        print(f"Processing video {i+1}/{len(video_files)}: {os.path.basename(video_path)}")
        metadata = extract_video_metadata(video_path)
        
        if metadata:
            all_metadata["videos"].append(metadata)
            
            # Add to total duration
            if "duration" in metadata:
                all_metadata["total_duration_seconds"] += metadata["duration"]
    
    # Format total duration
    total_seconds = all_metadata["total_duration_seconds"]
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    all_metadata["total_duration_formatted"] = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    
    # Save to JSON file if requested
    if output_json:
        with open(output_json, 'w') as f:
            json.dump(all_metadata, f, indent=2)
        print(f"Metadata saved to {output_json}")
    
    return all_metadata

def main():
    # Example raw footage metadata (could be extended with more details)
    raw_footage_info = {
        "files": ["clip1.mp4", "clip2.mp4"]
    }
    
    # Generate a shot list (this is where you'd call your LLM if integrated)
    shot_list = generate_shot_list(raw_footage_info)
    
    processed_clips = []
    
    # Process each shot from the shot list
    for idx, shot in enumerate(shot_list["shots"]):
        trimmed_file = f"trimmed_{idx}.mp4"
        print(f"Trimming {shot['filename']} from {shot['start']} to {shot['end']}")
        trim_video(shot["filename"], shot["start"], shot["end"], trimmed_file)
        processed_clips.append(trimmed_file)
    
    # Combine the processed clips into one video file
    combined_file = "combined.mp4"
    print("Combining clips into", combined_file)
    combine_clips(processed_clips, combined_file)
    
    # Example: Optionally add audio if background music is provided in the shot list
    if "audio" in shot_list and shot_list["audio"].get("bgm"):
        final_output = "final_output.mp4"
        print("Adding background music from", shot_list["audio"]["bgm"])
        add_audio(combined_file, shot_list["audio"]["bgm"], final_output)
    else:
        final_output = combined_file
    
    print("Video editing completed. Final output file:", final_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract metadata from video files in a folder')
    parser.add_argument('folder', help='Path to the folder containing video files')
    parser.add_argument('--output', '-o', help='Path to save the JSON output file')
    
    args = parser.parse_args()
    
    metadata = extract_metadata_from_folder(args.folder, args.output)
    
    if not args.output:
        # Print a summary to console if not saving to file
        print("\nVideo Metadata Summary:")
        print(f"Total videos: {metadata['total_videos']}")
        print(f"Total duration: {metadata['total_duration_formatted']}")
        
        # Print table of videos
        if metadata['videos']:
            print("\nVideos:")
            print(f"{'Filename':<30} {'Resolution':<12} {'Duration':<10} {'Size (MB)':<10}")
            print("-" * 65)
            for video in metadata['videos']:
                print(f"{video['filename'][:30]:<30} {video['resolution']:<12} {video.get('duration_formatted', '00:00:00'):<10} {video['filesize_mb']:<10}")
