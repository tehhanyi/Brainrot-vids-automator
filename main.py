import os
import subprocess
import sys
import urllib.request
import zipfile
import shutil
import json
import platform

required_libs = ["yt-dlp", "python-dotenv"]
for package in required_libs:
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

from dotenv import load_dotenv

FONT_FILE = './MinecraftBold.otf'
SOURCE_FILE = 'vids/source_video.mp4'
TEMP_FOLDER = 'vids/temp'
PREVIEW_FOLDER = 'vids/preview'
THUMBNAIL_FOLDER = 'vids/thumbnails'
CLIPS_FOLDER = 'vids/tiktok_clips'

def setup_ffmpeg():
    system = platform.system()

    if system == "Windows":
        ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')
        # Check if ffmpeg already exists
        if os.path.exists(ffmpeg_path):
            return ffmpeg_path
            
        print("Downloading FFmpeg...")
        # Download FFmpeg
        ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        zip_path = os.path.join(os.path.dirname(__file__), 'ffmpeg.zip')
        
        # Download the zip file
        urllib.request.urlretrieve(ffmpeg_url, zip_path)
        
        # Extract ffmpeg.exe
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith('ffmpeg.exe'):
                    zip_ref.extract(file)
                    # Move ffmpeg.exe to root directory
                    shutil.move(file, ffmpeg_path)
                    break
        
        # Clean up
        os.remove(zip_path)
        if os.path.exists('ffmpeg-master-latest-win64-gpl'):
            shutil.rmtree('ffmpeg-master-latest-win64-gpl')
    elif system == "Darwin":
        ffmpeg_path = 'ffmpeg'
    else:
        print("This computer is running Linux or another Unix-like OS.")

    return ffmpeg_path
ffmpeg_path = setup_ffmpeg()
def retrieve_video_details():
    if not os.path.exists('.env'):
        print("Error: .env file not found!")
        sys.exit(1)

    load_dotenv()
    try:
        youtube_url = os.getenv("YOUTUBE_URL")
        video_title = os.getenv("VIDEO_TITLE")
        clip_duration = os.getenv("CLIP_PER_DURATION")
        sponsor_start = os.getenv("SPONSOR_START_TIME")
        sponsor_end = os.getenv("SPONSOR_END_TIME")

        if not youtube_url or not video_title or not clip_duration:
            raise ValueError("Missing required environment variables at .env: YOUTUBE_URL, VIDEO_TITLE, or CLIP_PER_DURATION")

        # Convert duration to integer
        clip_duration = int(clip_duration)

        # Treat empty strings as None
        sponsor_start = sponsor_start if sponsor_start else None
        sponsor_end = sponsor_end if sponsor_end else None #and sponsor_end.lower() != "null"
        return youtube_url, video_title, clip_duration, sponsor_start, sponsor_end
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

def download_video(url, filename):
    try:
        result = subprocess.run([
            sys.executable, '-m', 'yt_dlp',
            '--skip-download',  # Don't download, just check metadata
            '--dump-json',      # Get video info as JSON
            url
        ], capture_output=True, text=True, check=True)
        
        video_info = json.loads(result.stdout)
        # Check for content ID matches
        if video_info.get('content_id_claims'):
            print("\nWARNING: Copyright claims detected!")
            print("The following content matches were found:")
            for claim in video_info['content_id_claims']:
                print(f"- {claim.get('claim', 'Unknown claim')}")    
            while True:
                response = input("\nDo you want to continue downloading? Tiktok may potential mute your videos (y/n): ").lower()
                if response in ['y', 'n']:
                    if response == 'n':
                        sys.exit(0)
                    break
                print("Please enter 'y' for yes or 'n' for no.")
        else:
            print("No copyright claims detected. Proceeding with download...")
    except subprocess.CalledProcessError:
        print("Warning: Could not check for copyright claims. Proceeding with download...")

    if os.path.exists(filename):
        print("Video already downloaded.")
        return
    # For Windows or Linux
    subprocess.run([
        sys.executable, '-m', 'yt_dlp',
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]',
        '--merge-output-format', 'mp4',
        '--write-auto-sub',  # Download auto-generated subtitles
        '--write-sub',       # Download manual subtitles if available
        '--sub-format', 'vtt',  # Get subtitles in WebVTT format
        '--embed-subs',      # Embed subtitles in the video file
        '-o', filename, url
    ], check=True)
    # subprocess.run([
    #     'yt-dlp', '-f', 'bestvideo+bestaudio',
    #     '--merge-output-format', 'mp4',  # Ensure the output is in MP4 format
    #     '--postprocessor-args', 'ffmpeg:-c:v libx264 -c:a aac',  # Use compatible codecs
    #     '-o', filename, url
    # ], check=True)
def remove_ads(filename, cut_start, cut_end):
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    # Get the first part before the cut
    subprocess.run([
        ffmpeg_path, '-ss', '00:00:00',  # Start from the beginning
        '-i', filename,
        '-to', cut_start,  # Cut until the specified start time
        '-map', '0',  # Include all streams (video, audio, subtitles)
        '-c:v', 'libx264',  # Re-encode video
        '-c:a', 'aac',      # Re-encode audio
        '-c:s', 'mov_text', # Re-encode subtitles
        '-preset', 'medium',
        '-y', f'{TEMP_FOLDER}/first.mp4'
    ], check=True)
    
    # Get the second part after the cut
    subprocess.run([
        ffmpeg_path, '-ss', cut_end,  # Start from the specified end time
        '-i', filename,
        '-map', '0',  # Include all streams (video, audio, subtitles)
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-c:s', 'mov_text',
        '-preset', 'medium',
        '-y', f'{TEMP_FOLDER}/second.mp4'
    ], check=True)
    
    # Create a file list for concatenation
    with open(f'{TEMP_FOLDER}/list.txt', 'w') as f:
        f.write("file 'first.mp4'\n")
        f.write("file 'second.mp4'\n")
    
    # Concatenate the parts
    subprocess.run([
        ffmpeg_path, '-f', 'concat',
        '-safe', '0',
        '-i', f'{TEMP_FOLDER}/list.txt',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-c:s', 'mov_text',
        '-preset', 'medium',
        '-y', filename
    ], check=True)

    shutil.rmtree(TEMP_FOLDER)
def split_video(filename, output_folder, segment_duration=60):
    os.makedirs(output_folder, exist_ok=True)
    subprocess.run([
        ffmpeg_path, '-i', filename,
        '-c', 'copy',
        '-map', '0',
        '-f', 'segment',
        '-segment_time', str(segment_duration),
        f'{output_folder}/clip_%03d.mp4'
    ], check=True)
def wrap_title(title,max_line=4, max_line_length=15):
    words = title.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_line_length:
            current_line += (word + " ")
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    lines.append(current_line.strip())

    return '\n'.join(lines[:max_line])
def generate_thumbnail(video_file, output_file, timestamp="00:00",part_number=1,title=""):
    os.makedirs(output_file, exist_ok=True)
    wrapped_title = wrap_title(title, max_line=4, max_line_length=15)
    subprocess.run([
        ffmpeg_path, '-ss', timestamp, '-i', video_file,  # Seek to the timestamp
        '-frames:v', '1',  # Capture a single frame
        '-vf', (
            'crop=480:640:(in_w-480)/2:(in_h-640)/2,'  # Crop to 4:3 portrait
            'drawtext=text=\'{}\':text_shaping=1:text_align=center:'
            f'fontfile={FONT_FILE}:'
            'fontcolor=white:fontsize=40:'
            'borderw=2:bordercolor=black:'
            'x=(w-text_w)/2:y=50,'
            'drawtext=text=\'Part {}\':'
            f'fontfile={FONT_FILE}:'
            'fontcolor=white:fontsize=80:'
            'borderw=3:bordercolor=black:'
            'x=(w-text_w)/2:y=h-200'.format(wrapped_title, part_number)
        ),
        '-q:v', '2',  # Set high-quality output
        os.path.join(output_file, f'part_{part_number}.jpg')
    ], check=True)
def add_captions_to_video(input_file, output_file, total_clips, part_number=1, title=""):
    os.makedirs(output_file, exist_ok=True)
    wrapped_title = wrap_title(title, max_line=3, max_line_length=25)
    
    # Base filter chain
    filter_chain = (
        'split[original][blur];'
        '[blur]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:20[bg];'
        '[original]scale=1080:1080:force_original_aspect_ratio=increase[fg];' # '[original]scale=1080:-2[fg];'
        '[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto,'
        f'drawtext=text=\'{wrapped_title}\':text_shaping=1:text_align=center:'
        f'fontfile={FONT_FILE}:'
        'fontcolor=white:fontsize=56:'
        'borderw=2:bordercolor=black:'
        'x=(w-text_w)/2:y=250'
    )
    # Add part number only if there's more than one clip
    if total_clips > 1:
        filter_chain += (
            ',drawtext=text=\'Part {}\':'
            f'fontfile={FONT_FILE}:'
            'fontcolor=white:fontsize=72:'
            'borderw=3:bordercolor=black:'
            'x=(w-text_w)/2:y=h-400'
            .format(part_number)
        )
    subprocess.run([
        ffmpeg_path, '-i', input_file,
        '-vf', filter_chain,
        '-c:a', 'copy',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-y',
        os.path.join(output_file, f'part_{part_number}.mp4')
    ], check=True)
def create_preview():
    temp_preview = f'{PREVIEW_FOLDER}/temp.mp4'   
    os.makedirs(PREVIEW_FOLDER, exist_ok=True)
    subprocess.run([
        'ffmpeg', '-i', f'{TEMP_FOLDER}/clip_000.mp4',  # Use the first clip for preview
        '-t', '3',  # Only take first second
        '-c:v', 'libx264',
        '-preset', 'ultrafast',  # Fast encoding for preview
        '-y',
        temp_preview
    ], check=True)

    add_captions_to_video(temp_preview, PREVIEW_FOLDER, total_clips=2, title="Preview Title Preview Title Preview Title", part_number=1)
    generate_thumbnail(temp_preview, PREVIEW_FOLDER, title="Preview Title Preview Title Preview Title")
    print(f"\nPreview generated at: {PREVIEW_FOLDER}")
    os.startfile(os.path.realpath(PREVIEW_FOLDER))

    while True:
        response = input("\nDo you want to continue processing? (y/n): ").lower()
        if response in ['y', 'n']:
            # shutil.rmtree(TEMP_FOLDER)
            shutil.rmtree(PREVIEW_FOLDER)
            break
        print("Please en-+ter 'y' for yes or 'n' for no.")
    if response == 'n':
        print("Processing cancelled.")
        sys.exit(0)
    print("\nContinuing with full video processing...")
    
if __name__ == '__main__':
    # youtube_url = input("Enter the YouTube URL: ")
    # title = input("Enter the title for the thumbnails: ")
    # duration = input("Enter the duration per clip in secs: ")
    youtube_url, title, duration, ads_start, ads_end = retrieve_video_details()
    download_video(youtube_url, SOURCE_FILE)
    if ads_start and ads_end:
        print("\nRemoving ads from the video...")
        remove_ads(SOURCE_FILE, ads_start, ads_end)
    
    split_video(SOURCE_FILE, TEMP_FOLDER, segment_duration=duration)
    print("\nAll clips are splited in the", TEMP_FOLDER, "folder.\nAdding captions and generating thumbnails next...")
    create_preview()
    clip_files = sorted([f for f in os.listdir(TEMP_FOLDER) if f.endswith('.mp4')])
    total_clips = len(clip_files)

    # Generate captions and thumbnails for each clip
    for i, clip_file in enumerate(clip_files, start=1):
        clip_path = os.path.join(TEMP_FOLDER, clip_file)
        generate_thumbnail(clip_path, THUMBNAIL_FOLDER, part_number=i, title=title)
        add_captions_to_video(clip_path, CLIPS_FOLDER, total_clips, part_number=i, title=title)

    print("\nAll clips are ready to be posted for brainrot!\n")

    # response = input("Do you want to delete the clips? (y/n): ").lower()
    # if response == 'y':
    shutil.rmtree(TEMP_FOLDER)
    sys.exit(1)
    # else:
    #     print("Temporary clips are kept in:", TEMP_FOLDER)