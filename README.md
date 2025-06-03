# Brainrot Videos Automator 🎥

Automatically process YouTube videos into TikTok-style vertical clips with captions and thumbnails.

## Prerequisites
- Python 3.x
- FFmpeg

## Installation
1. Download Python[https://www.python.org/downloads/]
2. Install FFmpeg:
   - Windows: The script will automatically download FFmpeg
   - MacOS: `brew install ffmpeg`

## Usage
1. Rename `.env-example` file to `.env` and add on the following details:
- YouTube URL
- Title for the clips
- Duration per clip in seconds
- (Optional) Sponsor shoutout start time
- (Optional) Sponsor shoutout end time

```example
https://www.youtube.com/watch?v=YOUR_VIDEO_ID
Your Video Title
60
```

2. Run the script:
```bash
python main.py
```

## Output

The script will:
- Download the YouTube video
- Split it into clips of specified duration
- Add captions and blur effects
- Generate thumbnails
- Burn subtitles onto clips
- Save everything in the `vids/` folder

## Folder Structure

```
├── vids/
│   ├── source_video.mp4
│   ├── temp_clips/
│   └── tiktok_clips/
├── .env
└── main.py
```