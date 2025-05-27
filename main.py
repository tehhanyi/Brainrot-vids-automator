import os
import subprocess

SOURCE_FILE = 'vids/source_video.mp4'
CLIPS_FOLDER = 'vids/tiktok_clips'
FONT_FILE = './MinecraftBold.otf'
def download_video(url, filename):
    if os.path.exists(filename):
        print("Video already downloaded.")
        return
    subprocess.run([
        'yt-dlp', '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]',  # Use MP4 and M4A formats
        '--merge-output-format', 'mp4',  # Merge without re-encoding
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
        'ffmpeg', '-i', filename,
        '-c', 'copy',
        '-map', '0',
        '-f', 'segment',
        '-segment_time', str(segment_duration),
        f'{output_folder}/clip_%03d.mp4'
    ], check=True)
def generate_thumbnail(video_file, output_file, timestamp="00:00",part_number=1,title=""):
     # Wrap the title into multiple lines (max 3 lines)
    max_line_length = 15
    words = title.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_line_length:
            current_line += (word + " ")
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    lines.append(current_line.strip())  # Add the last line

    # Limit to 4 lines max
    lines = lines[:4]
    wrapped_title = '\n'.join(lines)

    subprocess.run([
        'ffmpeg', '-ss', timestamp, '-i', video_file,  # Seek to the timestamp
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
    """
    Add a title at the top of the letterbox and "Part X" at the bottom of the letterbox.
    """
    output_file = os.path.join(output_file, f'part_{part_number}.mp4')

    subprocess.run([
        'ffmpeg', '-i', input_file,  # Input video
        '-vf', (
            'drawtext=text=\'{}\':'
            f'fontfile={FONT_FILE}:'
            'fontcolor=white:fontsize=32:'
            'borderw=1:bordercolor=black:'
            'x=(w-text_w)/2:y=10,'  # Title at the top of the letterbox
            'drawtext=text=\'Part {}\':'
            f'fontfile={FONT_FILE}:'
            'fontcolor=white:fontsize=64:'
            'borderw=2:bordercolor=black:'
            'x=(w-text_w)/2:y=h-60'.format(title, part_number)  # Part X at the bottom of the letterbox
        ),
        '-c:a', 'copy',  # Copy audio without re-encoding
        output_file
    ], check=True)

if __name__ == '__main__':
    youtube_url = input("Enter the YouTube URL: ")
    title = input("Enter the title for the thumbnails: ")
    duration = input("Enter the duration per clip in secs: ")
    download_video(youtube_url, SOURCE_FILE)
    
    split_video(SOURCE_FILE, CLIPS_FOLDER, segment_duration=duration)
        
    print("\n🎉 All clips are ready in the", CLIPS_FOLDER, "folder!")
    print("\nAdding captions and generating thumbnails now...\n")

    # Count the total number of clips
    clip_files = sorted([f for f in os.listdir(CLIPS_FOLDER) if f.endswith('.mp4')])
    total_clips = len(clip_files)
    print(f"Total clips: {total_clips}")

    # Generate captions and thumbnails for each clip
    for i, clip_file in enumerate(clip_files, start=1):
        clip_path = os.path.join(CLIPS_FOLDER, clip_file)
        thumbnail_file = os.path.join(CLIPS_FOLDER, f'thumbnail_part_{i}.jpg')
        generate_thumbnail(clip_path, thumbnail_file, part_number=i, title=title)
        add_captions_to_video(clip_path, CLIPS_FOLDER, title, i)


    # Optional: Cleanup temp clips
    # shutil.rmtree(temp_clips)