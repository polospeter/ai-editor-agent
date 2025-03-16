import os
import subprocess
import json
import base64
import tempfile
from dotenv import load_dotenv
from openai import AzureOpenAI
import asyncio
from PIL import Image
import io
import ffmpeg_utils

# Load environment variables
load_dotenv()

# Azure OpenAI configuration
AZURE_ENDPOINT = "https://ai-coe-openai-models-latest.openai.azure.com/"
AZURE_MODEL = "gpt-4o-mini"
AZURE_DEPLOYMENT = "gpt-4o-mini"
AZURE_API_VERSION = "2024-12-01-preview"

# Get API key from environment variable or set it directly
# IMPORTANT: For security, it's better to use environment variables than hardcoding the key
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")

# Create OpenAI client using Azure OpenAI with API key authentication
try:
    openai_client = AzureOpenAI(
        api_version=AZURE_API_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
    )
    print("Initialized Azure OpenAI client with API key authentication")
except Exception as e:
    print(f"Error initializing Azure OpenAI client: {e}")

async def test_api_connection():
    """
    Test the connection to the Azure OpenAI API.
    
    Returns:
        tuple: (success, message) where success is a boolean indicating if the connection was successful
               and message contains details about the connection status
    """
    print("Testing connection to Azure OpenAI API...")
    print(f"Endpoint: {AZURE_ENDPOINT}")
    print(f"Model: {AZURE_MODEL}")
    print(f"Deployment: {AZURE_DEPLOYMENT}")
    
    # Check if API key is set
    if not AZURE_API_KEY:
        return False, "API key is not set. Please set the AZURE_OPENAI_API_KEY environment variable."
    
    try:
        # Simple API call to test connection
        response = openai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "I am going to Paris, what should I see?"}
            ],
            max_tokens=4096,
            temperature=1.0,
            top_p=1.0,
            model=AZURE_DEPLOYMENT
        )
        
        # Print the response for verification
        print("\nAPI Test Response:")
        print(f"Response: {response.choices[0].message.content[:100]}...")
        
        # If we get here, the connection was successful
        return True, "Successfully connected to Azure OpenAI API"
    
    except Exception as e:
        error_message = str(e)
        
        # Provide more helpful error messages for common issues
        if "401" in error_message:
            return False, f"Authentication error: Invalid API key. Error: {error_message}"
        elif "404" in error_message:
            return False, f"Resource not found: Check your deployment name and endpoint. Error: {error_message}"
        elif "429" in error_message:
            return False, f"Rate limit exceeded: Too many requests. Error: {error_message}"
        else:
            return False, f"Connection error: {error_message}"

async def extract_frame(video_path, time_position, output_path=None):
    """
    Extract a frame from a video at a specific time position.
    
    Args:
        video_path: Path to the video file
        time_position: Time position in format "HH:MM:SS.mmm" or seconds
        output_path: Path to save the extracted frame (optional)
        
    Returns:
        Path to the extracted frame image
    """
    if output_path is None:
        # Create a temporary file if no output path is provided
        fd, output_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
    
    try:
        command = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(time_position),
            "-frames:v", "1",
            output_path
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error extracting frame: {e}")
        print(f"Error output: {e.stderr.decode() if e.stderr else 'None'}")
        return None

async def encode_image_to_base64(image_path):
    """
    Encode an image file to base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string of the image
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def describe_image(image_path):
    """
    Use Azure OpenAI to describe an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Description of the image
    """
    try:
        # Encode image to base64
        base64_image = await encode_image_to_base64(image_path)
        
        # Call Azure OpenAI API
        response = openai_client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a detailed image analyzer. Describe what you see in the image with specific details about the scene, people, objects, lighting, and atmosphere."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Describe this image in detail."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error describing image: {e}")
        return "Error: Could not generate description."

async def analyze_video_content(first_frame_description, last_frame_description, video_metadata=None):
    """
    Use Azure OpenAI to analyze what happens in a video based on first and last frame descriptions.
    
    Args:
        first_frame_description: Description of the first frame
        last_frame_description: Description of the last frame
        video_metadata: Optional metadata about the video (duration, etc.)
        
    Returns:
        Analysis of what likely happens in the video
    """
    try:
        metadata_text = ""
        if video_metadata:
            metadata_text = f"Video duration: {video_metadata.get('duration_formatted', 'unknown')}\n"
            metadata_text += f"Resolution: {video_metadata.get('resolution', 'unknown')}\n"
        
        response = openai_client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a video content analyzer. Based on descriptions of the first and last frames of a video, infer what likely happens during the footage. Be creative but realistic in your analysis."},
                {"role": "user", "content": f"""
                {metadata_text}
                
                First frame description:
                {first_frame_description}
                
                Last frame description:
                {last_frame_description}
                
                Based on these descriptions, what likely happens in this video footage? Provide a narrative that connects the first and last frames.
                """}
            ],
            max_tokens=800
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error analyzing video content: {e}")
        return "Error: Could not generate analysis."

async def analyze_video(video_path):
    """
    Analyze a video by extracting and describing its first and last frames,
    then generating a description of what happens in the footage.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Dictionary containing the analysis results
    """
    print(f"\nAnalyzing video: {os.path.basename(video_path)}")
    
    # Get video metadata
    metadata = ffmpeg_utils.extract_video_metadata(video_path)
    
    if not metadata:
        return {
            "filename": os.path.basename(video_path),
            "error": "Could not extract metadata"
        }
    
    # Extract first frame (at 0 seconds)
    first_frame_path = await extract_frame(video_path, 0)
    
    # Extract last frame (1 second before the end to avoid black frames)
    duration = metadata.get("duration", 0)
    last_time = max(0, duration - 1)
    last_frame_path = await extract_frame(video_path, last_time)
    
    results = {
        "filename": os.path.basename(video_path),
        "metadata": metadata,
        "first_frame": {
            "path": first_frame_path,
            "description": None
        },
        "last_frame": {
            "path": last_frame_path,
            "description": None
        },
        "content_analysis": None
    }
    
    # Describe first frame
    print("Describing first frame...")
    if first_frame_path:
        results["first_frame"]["description"] = await describe_image(first_frame_path)
    
    # Describe last frame
    print("Describing last frame...")
    if last_frame_path:
        results["last_frame"]["description"] = await describe_image(last_frame_path)
    
    # Analyze video content based on frame descriptions
    if results["first_frame"]["description"] and results["last_frame"]["description"]:
        print("Analyzing video content...")
        results["content_analysis"] = await analyze_video_content(
            results["first_frame"]["description"],
            results["last_frame"]["description"],
            metadata
        )
    
    return results

async def analyze_videos_in_folder(folder_path, output_json=None):
    """
    Analyze all videos in a folder by extracting and describing their first and last frames,
    then generating descriptions of what happens in each footage.
    
    Args:
        folder_path: Path to the folder containing video files
        output_json: Optional path to save the JSON output file
        
    Returns:
        Dictionary containing the analysis results for all videos
    """
    print(f"Scanning folder: {folder_path}")
    
    # Test API connection before starting
    connection_success, connection_message = await test_api_connection()
    
    if not connection_success:
        print(f"ERROR: {connection_message}")
        print("Cannot proceed with video analysis due to API connection issues.")
        return {
            "folder": os.path.abspath(folder_path),
            "scan_date": ffmpeg_utils.datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": connection_message,
            "total_videos": 0,
            "videos": []
        }
    
    print(f"API Connection: {connection_message}")
    
    # Dictionary to store all video analyses
    all_analyses = {
        "folder": os.path.abspath(folder_path),
        "scan_date": ffmpeg_utils.datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_videos": 0,
        "videos": []
    }
    
    # Supported video extensions
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v')
    
    # Find all video files in the folder
    video_files = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(video_extensions):
            video_files.append(os.path.join(folder_path, filename))
    
    if not video_files:
        print(f"No video files found in {folder_path}")
        return all_analyses
    
    # Update total videos count
    all_analyses["total_videos"] = len(video_files)
    print(f"Found {len(video_files)} video files to analyze")
    
    # Process each video file
    for i, video_path in enumerate(video_files):
        print(f"\nProcessing video {i+1}/{len(video_files)}: {os.path.basename(video_path)}")
        analysis = await analyze_video(video_path)
        
        if analysis:
            all_analyses["videos"].append(analysis)
    
    # Save to JSON file if requested
    if output_json:
        with open(output_json, 'w') as f:
            # Create a simplified version for JSON output (without image paths)
            json_output = all_analyses.copy()
            for video in json_output["videos"]:
                if "first_frame" in video and "path" in video["first_frame"]:
                    video["first_frame"].pop("path", None)
                if "last_frame" in video and "path" in video["last_frame"]:
                    video["last_frame"].pop("path", None)
            
            json.dump(json_output, f, indent=2)
        print(f"Analysis saved to {output_json}")
    
    return all_analyses

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze videos in a folder using Azure OpenAI')
    
    # Simple folder argument
    parser.add_argument('folder', help='Path to the folder containing video files')
    
    # Other arguments
    parser.add_argument('--output', '-o', help='Path to save the JSON output file (defaults to [folder_name]_analysis.json in the input folder)')
    parser.add_argument('--test-only', action='store_true', help='Only test the API connection without analyzing videos')
    parser.add_argument('--api-key', help='Azure OpenAI API key (overrides environment variable)')
    
    args = parser.parse_args()
    
    # Override API key if provided
    if args.api_key:
        global AZURE_API_KEY
        global openai_client
        AZURE_API_KEY = args.api_key
        openai_client = AzureOpenAI(
            api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_ENDPOINT,
            api_key=AZURE_API_KEY,
        )
        print("Using API key provided via command line")
    
    # If test-only flag is set or no arguments provided, just test the API connection
    if args.test_only or args.folder == 'test':
        print("Running API connection test...")
        success, message = await test_api_connection()
        if success:
            print(f"\n✅ {message}")
        else:
            print(f"\n❌ {message}")
        return
    
    folder_path = args.folder
    
    # Check if folder exists
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist or is not a directory")
        return
    
    # Set default output path to be in the same folder as the videos
    output_path = args.output
    if not output_path:
        folder_name = os.path.basename(os.path.normpath(folder_path))
        output_path = os.path.join(folder_path, f"{folder_name}_analysis.json")
        print(f"Output will be saved to: {output_path}")
    
    analyses = await analyze_videos_in_folder(folder_path, output_path)
    
    # Check if there was an API error
    if "error" in analyses:
        print(f"\n❌ Analysis failed: {analyses['error']}")
        return
    
    # Print a summary to console
    print("\nVideo Analysis Summary:")
    print(f"Total videos analyzed: {analyses['total_videos']}")
    
    # Print table of videos
    if analyses['videos']:
        for video in analyses['videos']:
            print(f"\n--- {video['filename']} ---")
            print("\nContent Analysis:")
            print(video.get('content_analysis', 'No analysis available'))
            print("\n" + "-" * 80)
    
    if analyses['total_videos'] > 0:
        print(f"\nFull analysis saved to: {output_path}")

if __name__ == "__main__":
    # If script is run directly, run the test function
    if len(os.sys.argv) == 1:
        print("No arguments provided. Running API test...")
        asyncio.run(test_api_connection())
    else:
        asyncio.run(main())
