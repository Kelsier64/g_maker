import yt_dlp
import os
import sys

def download_mp3_from_youtube(url, output_path="./sound.mp3", output_to_stdout=False):
    """
    Downloads audio from a YouTube URL as an MP3 file.

    Args:
        url (str): The YouTube video URL.
        output_path (str): The path where to save the MP3 file.
        output_to_stdout (bool): Whether to output binary data to stdout instead of saving to file.
    """
    if output_to_stdout:
        # For stdout output, we'll use a temporary file
        temp_path = os.path.join(os.path.dirname(__file__), "temp_audio")
        output_path = f"{temp_path}.mp3"
        
    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Extract filename without extension
    filename = os.path.splitext(os.path.basename(output_path))[0]
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',  # Standard quality
        }],
        'outtmpl': output_path.replace('.mp3', ''),  # yt-dlp will add .mp3 extension automatically
        'keepvideo': False,  # True if you want to keep the downloaded video
        'noplaylist': True,  # Download only the video, not playlist if URL is part of one
        'quiet': True, # Suppress console output from yt-dlp
        # 'no_warnings': True, # Suppress warnings
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Check if a URL was provided as a command-line argument
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
        download_mp3_from_youtube(video_url)
        with open("./sound.mp3", "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
    else:
        # Original behavior when no arguments are provided
        video_url = input("Enter the YouTube video URL: ")
        if video_url:
            download_mp3_from_youtube(video_url)
        else:
            print("No URL provided.")
