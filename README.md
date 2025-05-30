# Brainrot Videos Automator 🎥

Automatically process YouTube videos into TikTok-style vertical clips with captions and thumbnails.

## Prerequisites
- Python 3.x
- FFmpeg
- yt-dlp

## Installation
1. Install Python dependencies:
```bash
pip install yt-dlp
```
or
```bash
pip3 install yt-dlp
```

2. Download and install FFmpeg:
   - Windows: The script will automatically download FFmpeg
   - MacOS: `brew install ffmpeg`

## Usage
1. Create a `video_details.txt` file with the following format:
- Line 1: YouTube URL
- Line 2: Title for the clips
- Line 3: Duration per clip in seconds
```example
https://www.youtube.com/watch?v=YOUR_VIDEO_ID
Your Video Title
60
```

2. Run the script:
```bash
python windows.py
```

## Output

The script will:
- Download the YouTube video
- Split it into clips of specified duration
- Add captions and blur effects
- Generate thumbnails
- Save everything in the `vids` folder

## Folder Structure

```
├── vids/
│   ├── source_video.mp4
│   ├── temp_clips/
│   └── tiktok_clips/
├── video_details.txt
└── windows.py
```