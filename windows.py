import os
import subprocess
import sys
import urllib.request
import zipfile
import shutil

FONT_FILE = './MinecraftBold.otf'
SOURCE_FILE = 'vids/source_video.mp4'
TEMP_CLIPS = 'vids/temp_clips'
THUMBNAIL_FOLDER = 'vids/thumbnails'
CLIPS_FOLDER = 'vids/tiktok_clips'

def setup_ffmpeg():
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
        
    print("FFmpeg setup complete!")
    return ffmpeg_path
ffmpeg_path = setup_ffmpeg()
def retrieve_video_details():
    try:
        with open('video_details.txt', 'r') as f:
            lines = f.read().splitlines()
            if len(lines) >= 3:
                return lines
            else:
                raise ValueError("video_details.txt must contain 3 lines: URL, title, and duration")
    except FileNotFoundError:
        print("Error: video_details.txt not found!")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
def download_video(url, filename):
    if os.path.exists(filename):
        print("Video already downloaded.")
        return
    # For Windows or Linux
    subprocess.run([
        sys.executable, '-m', 'yt_dlp',
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]',
        '--merge-output-format', 'mp4',
        '-o', filename, url
    ], check=True)
    # subprocess.run([
    #     'yt-dlp', '-f', 'bestvideo+bestaudio',
    #     '--merge-output-format', 'mp4',  # Ensure the output is in MP4 format
    #     '--postprocessor-args', 'ffmpeg:-c:v libx264 -c:a aac',  # Use compatible codecs
    #     '-o', filename, url
    # ], check=True)
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
    wrapped_title = wrap_title(title, max_line=4, max_line_length=15)
    subprocess.run([
        ffmpeg_path, '-ss', timestamp, '-i', video_file,  # Seek to the timestamp
        '-frames:v', '1',  # Capture a single frame
        '-vf', (
            'crop=480:640:(in_w-480)/2:(in_h-640)/2,'  # Crop to 4:3 portrait
            'drawtext=text=\'{}\':'
            f'fontfile={FONT_FILE}:'
            'fontcolor=black:fontsize=40:'
            'borderw=1:bordercolor=white:'
            'x=(w-text_w)/2:y=20,'
            'drawtext=text=\'Part {}\':'
            f'fontfile={FONT_FILE}:'
            'fontcolor=white:fontsize=80:'
            'borderw=3:bordercolor=black:'
            'x=(w-text_w)/2:y=h-100'.format(wrapped_title, part_number)
        ),
        '-q:v', '2',  # Set high-quality output
        output_file
    ], check=True)
def add_captions_to_video(input_file, output_file, title, part_number):
    wrapped_title = wrap_title(title, max_line=3, max_line_length=30)
    output_file = os.path.join(output_file, f'part_{part_number}.mp4')
    subprocess.run([
        ffmpeg_path, '-i', input_file,  # Input video
        '-vf', (
            # Split into two streams
            'split[original][blur];'
            # Create blurred background - scale to fill 9:16
            '[blur]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:20[bg];'
            # Scale original to fit in center while maintaining aspect ratio
            '[original]scale=1080:-2[fg];'
            # Overlay original in center
            '[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto,'
            # Add title in top blurred area
            'drawtext=text=\'{}\':'
            f'fontfile={FONT_FILE}:'
            'fontcolor=white:fontsize=56:'
            'borderw=2:bordercolor=black:'
            'x=(w-text_w)/2:y=500,'
            # 'x=(w-text_w)/2:y=(h-ih)/4,'  # Position in top blurred area
            # Add part number in bottom blurred area
            'drawtext=text=\'Part {}\':'
            f'fontfile={FONT_FILE}:'
            'fontcolor=white:fontsize=72:'
            'borderw=3:bordercolor=black:'
            # 'x=(w-text_w)/2:y=h-(h-ih)/4'
            'x=(w-text_w)/2:y=h-400'
            .format(wrapped_title, part_number)  # Position in bottom blurred area
        ),
        '-c:a', 'copy',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-y',
        output_file
    ], check=True)

if __name__ == '__main__':
    # youtube_url = input("Enter the YouTube URL: ")
    # title = input("Enter the title for the thumbnails: ")
    # duration = input("Enter the duration per clip in secs: ")
    lines = retrieve_video_details()
    youtube_url = lines[0].strip()
    title = lines[1].strip()
    duration = int(lines[2].strip())

    download_video(youtube_url, SOURCE_FILE)
    split_video(SOURCE_FILE, TEMP_CLIPS, segment_duration=duration)
        
    print("\nAll clips are splited in the", TEMP_CLIPS, "folder.")
    print("\nAdding captions and generating thumbnails next...\n")

    clip_files = sorted([f for f in os.listdir(TEMP_CLIPS) if f.endswith('.mp4')])
    total_clips = len(clip_files)
    # Generate captions and thumbnails for each clip
    for i, clip_file in enumerate(clip_files, start=1):
        clip_path = os.path.join(TEMP_CLIPS, clip_file)
        thumbnail_path = os.path.join(THUMBNAIL_FOLDER, f'part_{i}.jpg')
        generate_thumbnail(clip_path, thumbnail_path, part_number=i, title=title)
        add_captions_to_video(clip_path, CLIPS_FOLDER, title, i)

    print("\nAll clips are ready to be posted for brainrot!\n")

    response = input("Do you want to delete the clips? (y/n): ").lower()
    if response == 'y':
        shutil.rmtree(TEMP_CLIPS)
    else
        print("Temporary clips are kept in:", TEMP_CLIPS)