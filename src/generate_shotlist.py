#!/usr/bin/env python3
import json
import os
import asyncio
import argparse
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure OpenAI configuration
AZURE_ENDPOINT = "https://ai-coe-openai-models-latest.openai.azure.com/"
AZURE_MODEL = "gpt-4o-mini"
AZURE_DEPLOYMENT = "gpt-4o-mini"
AZURE_API_VERSION = "2024-12-01-preview"

# Create OpenAI client
openai_client = AzureOpenAI(
    api_version=AZURE_API_VERSION,
    azure_endpoint=AZURE_ENDPOINT,
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

def validate_shot_list_format(shot_list, all_filenames=None):
    """
    Validate that the shot list JSON matches the expected format.
    
    Args:
        shot_list: Dictionary containing the shot list
        all_filenames: Optional list of all filenames that should be included
        
    Returns:
        tuple: (is_valid, error_message) where is_valid is a boolean and error_message is None if valid
    """
    # Check required top-level keys
    required_keys = ["project_name", "narrative_theme", "shots"]
    for key in required_keys:
        if key not in shot_list:
            return False, f"Missing required key: '{key}'"
    
    # Check shots array
    if not isinstance(shot_list["shots"], list):
        return False, "'shots' must be an array"
    
    if len(shot_list["shots"]) == 0:
        return False, "'shots' array cannot be empty"
    
    # Check each shot
    for i, shot in enumerate(shot_list["shots"]):
        # Check required shot keys
        shot_keys = ["filename", "description", "start_time", "end_time", "duration", 
                     "transition_in", "transition_out"]
        for key in shot_keys:
            if key not in shot:
                return False, f"Shot {i+1} is missing required key: '{key}'"
        
        # Validate time format (HH:MM:SS)
        time_keys = ["start_time", "end_time", "duration"]
        for key in time_keys:
            time_str = shot[key]
            if not isinstance(time_str, str):
                return False, f"Shot {i+1}: '{key}' must be a string"
            
            # Check time format
            parts = time_str.split(":")
            if len(parts) != 3:
                return False, f"Shot {i+1}: '{key}' must be in format 'HH:MM:SS'"
            
            try:
                hours, minutes, seconds = map(int, parts)
                if not (0 <= hours and 0 <= minutes < 60 and 0 <= seconds < 60):
                    return False, f"Shot {i+1}: '{key}' contains invalid time values"
            except ValueError:
                return False, f"Shot {i+1}: '{key}' must contain numeric values"
    
    # Check if all filenames are included
    if all_filenames:
        shot_filenames = [shot["filename"] for shot in shot_list["shots"]]
        missing_files = [f for f in all_filenames if f not in shot_filenames]
        
        if missing_files:
            return False, f"Shot list is missing the following files: {', '.join(missing_files)}"
    
    return True, None

def generate_shot_list_from_json(input_json_path, output_json_path=None, storyline_guidance=None):
    """
    Generate a shot list narrative in JSON format based on an existing JSON file with video descriptions.
    
    Args:
        input_json_path: Path to the input JSON file with video descriptions
        output_json_path: Optional path to save the shot list JSON file
        storyline_guidance: Optional string with creative direction for the storyline
        
    Returns:
        Dictionary containing the shot list in JSON format
    """
    print(f"\nLoading video descriptions from: {input_json_path}")
    
    try:
        # Load the input JSON file
        with open(input_json_path, 'r') as f:
            analysis_data = json.load(f)
        
        if not analysis_data or "videos" not in analysis_data or not analysis_data["videos"]:
            print("No video data found in the input JSON file")
            return None
        
        # Extract relevant information for the prompt
        videos_info = []
        all_filenames = []
        
        for video in analysis_data["videos"]:
            # Keep track of all filenames
            if "filename" in video:
                all_filenames.append(video["filename"])
            
            # Try different possible field names for the description
            description = None
            for field in ["video_description", "content_analysis", "description", "content"]:
                if field in video and video[field]:
                    description = video[field]
                    break
            
            # If no description field found, check if there are first_frame and last_frame descriptions
            if not description and "first_frame" in video and "last_frame" in video:
                first_desc = video["first_frame"].get("description", "")
                last_desc = video["last_frame"].get("description", "")
                if first_desc and last_desc:
                    description = f"First frame: {first_desc}\n\nLast frame: {last_desc}"
            
            if description:
                # Get metadata if available
                metadata = video.get("metadata", {})
                duration_formatted = metadata.get("duration_formatted", "unknown")
                duration = metadata.get("duration", 0)
                
                video_info = {
                    "filename": video["filename"],
                    "content": description,
                    "duration": duration_formatted,
                    "duration_seconds": duration
                }
                videos_info.append(video_info)
        
        if not videos_info:
            print("No usable video descriptions found in the input JSON file")
            return None
        
        print(f"Found {len(videos_info)} videos with descriptions")
        
        # Create a prompt for the AI to generate a shot list
        videos_text = ""
        for i, video in enumerate(videos_info):
            videos_text += f"Video {i+1}: {video['filename']}\n"
            videos_text += f"Duration: {video['duration']}\n"
            videos_text += f"Content: {video['content']}\n\n"
        
        # Add storyline guidance if provided
        guidance_text = ""
        if storyline_guidance:
            guidance_text = f"\nStoryline Guidance:\n{storyline_guidance}\n\n"
            print(f"Using provided storyline guidance: {storyline_guidance}")
        
        print("Generating shot list...")
        
        # Call Azure OpenAI API to generate shot list
        response = openai_client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=[
                {"role": "system", "content": """You are a professional video editor. 
                Your task is to create a shot list in JSON format that tells a coherent story using the available footage.
                Analyze the content of each video and suggest an order, timestamps, and transitions that would create a compelling narrative.
                
                IMPORTANT: You MUST include EVERY SINGLE video file in your shot list. Do not skip any footage.
                
                The output should be valid JSON with the following structure:
                {
                  "project_name": "A descriptive name based on the content",
                  "narrative_theme": "A brief description of the story or theme",
                  "shots": [
                    {
                      "filename": "original_filename.mp4",
                      "description": "Brief description of this shot's purpose in the narrative",
                      "start_time": "HH:MM:SS",
                      "end_time": "HH:MM:SS",
                      "duration": "HH:MM:SS",
                      "transition_in": "fade in/dissolve/cut/etc",
                      "transition_out": "fade out/dissolve/cut/etc"
                    }
                  ]
                }
                Use realistic timestamps based on the actual duration of each video.
                Be creative but practical in your suggestions.
                If the user provides storyline guidance, follow it closely while creating your shot list.
                
                Remember: EVERY video file must be included in the shot list."""},
                {"role": "user", "content": f"""Here are the videos available for editing:{guidance_text}
                
                {videos_text}
                
                Based on these videos, create a shot list in JSON format that tells a coherent story.
                The shot list should suggest an order for the footage, with appropriate in/out points and transitions.
                
                IMPORTANT: You MUST include ALL {len(videos_info)} video files in your shot list.
                
                Return ONLY the JSON with no additional text."""}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        # Extract and parse the JSON response
        shot_list_text = response.choices[0].message.content
        
        # Clean up the response to ensure it's valid JSON
        # Remove any markdown code block indicators and extra text
        if "```json" in shot_list_text:
            shot_list_text = shot_list_text.split("```json")[1].split("```")[0].strip()
        elif "```" in shot_list_text:
            shot_list_text = shot_list_text.split("```")[1].split("```")[0].strip()
        
        try:
            shot_list = json.loads(shot_list_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print("Raw response:")
            print(shot_list_text)
            return None
        
        # Validate the shot list format
        is_valid, error_message = validate_shot_list_format(shot_list, all_filenames)
        if not is_valid:
            print(f"Warning: Generated shot list does not match expected format: {error_message}")
            print("Attempting to fix the format...")
            
            # Try to fix common issues
            if "shots" not in shot_list:
                shot_list["shots"] = []
            
            if "project_name" not in shot_list:
                shot_list["project_name"] = "Video Project"
                
            if "narrative_theme" not in shot_list:
                shot_list["narrative_theme"] = "Compilation of available footage"
            
            # Check for missing files and add them if needed
            if all_filenames:
                shot_filenames = [shot["filename"] for shot in shot_list["shots"]]
                missing_files = [f for f in all_filenames if f not in shot_filenames]
                
                if missing_files:
                    print(f"Adding missing files to shot list: {', '.join(missing_files)}")
                    
                    # Add missing files to the shot list
                    for filename in missing_files:
                        # Find the video info for this file
                        video_info = next((v for v in videos_info if v["filename"] == filename), None)
                        
                        if video_info:
                            # Add a basic shot for this file
                            shot_list["shots"].append({
                                "filename": filename,
                                "description": f"Added shot from {filename}",
                                "start_time": "00:00:00",
                                "end_time": video_info.get("duration_formatted", "00:01:00"),
                                "duration": video_info.get("duration_formatted", "00:01:00"),
                                "transition_in": "cut",
                                "transition_out": "cut"
                            })
            
            # Validate again after fixes
            is_valid, error_message = validate_shot_list_format(shot_list, all_filenames)
            if not is_valid:
                print(f"Could not fix format issues: {error_message}")
                print("Proceeding with the generated shot list anyway.")
        else:
            print("Shot list format validation successful!")
            
        # Check if all files are included
        shot_filenames = [shot["filename"] for shot in shot_list["shots"]]
        print(f"Shot list includes {len(shot_filenames)} out of {len(all_filenames)} video files")
        
        # Save to JSON file if requested
        if output_json_path:
            with open(output_json_path, 'w') as f:
                json.dump(shot_list, f, indent=2)
            print(f"Shot list saved to {output_json_path}")
        else:
            # If no output path specified, print the shot list
            print("\nGenerated Shot List:")
            print(json.dumps(shot_list, indent=2))
        
        return shot_list
    
    except Exception as e:
        print(f"Error generating shot list: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Generate a shot list from a JSON file with video descriptions')
    parser.add_argument('input_json', help='Path to the input JSON file with video descriptions')
    parser.add_argument('--output', '-o', help='Path to save the shot list JSON file')
    parser.add_argument('--api-key', help='Azure OpenAI API key (if not set in environment variables)')
    parser.add_argument('--storyline', '-s', help='Creative direction or storyline guidance for the shot list')
    parser.add_argument('--storyline-file', '-sf', help='Path to a text file containing storyline guidance')
    
    args = parser.parse_args()
    
    # Set API key from command line if provided
    if args.api_key:
        os.environ["AZURE_OPENAI_API_KEY"] = args.api_key
    
    # Check if API key is set
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("Error: Azure OpenAI API key not set. Please set the AZURE_OPENAI_API_KEY environment variable or use the --api-key option.")
        return
    
    # Set default output path if not specified
    output_path = args.output
    if not output_path:
        base_path = os.path.splitext(args.input_json)[0]
        output_path = f"{base_path}_shot_list.json"
    
    # Get storyline guidance from command line or file
    storyline_guidance = None
    if args.storyline:
        storyline_guidance = args.storyline
    elif args.storyline_file:
        try:
            with open(args.storyline_file, 'r') as f:
                storyline_guidance = f.read().strip()
        except Exception as e:
            print(f"Error reading storyline file: {e}")
    
    generate_shot_list_from_json(args.input_json, output_path, storyline_guidance)

if __name__ == "__main__":
    main()