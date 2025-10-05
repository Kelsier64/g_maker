import yt_dlp
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

def download_yt(url, output_path, format_type="mp3"):
    """
    Download YouTube video as mp3 or mp4 and ensure the final file matches output_path.

    Args:
        url: YouTube URL
        output_path: desired final path (e.g. "temp/ref_audio.mp3")
        format_type: "mp3" or "mp4"
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    base_no_ext = os.path.splitext(output_path)[0]
    outtmpl = base_no_ext + ".%(ext)s"

    if format_type == "mp3":
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "outtmpl": outtmpl,
            "keepvideo": False,
            "noplaylist": True,
            "quiet": True,
        }
    else:  # mp4
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
        }

    try:
        # Completely suppress all yt-dlp output including warnings
        with redirect_stderr(StringIO()), redirect_stdout(StringIO()):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Suppress all possible output methods
                ydl.report_warning = lambda *a, **kw: None
                ydl.report_error = lambda *a, **kw: None
                ydl.to_screen = lambda *a, **kw: None
                info = ydl.extract_info(url, download=True)


        # Determine expected final path
        if format_type == "mp3":
            final_path = base_no_ext + ".mp3"
        else:
            # try to infer extension from info; default to mp4
            ext = (info.get("ext") if isinstance(info, dict) else None) or "mp4"
            final_path = base_no_ext + f".{ext}"

        if os.path.exists(final_path):
            return final_path

        # fallback: find any file that starts with the base name
        base_name = os.path.basename(base_no_ext)
        for fname in os.listdir(os.path.dirname(output_path) or "."):
            if fname.startswith(base_name):
                return os.path.join(os.path.dirname(output_path) or ".", fname)

        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None