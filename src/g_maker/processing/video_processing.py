import subprocess
from g_maker.models import Video

def burn_subtitle(input_video_path,srt_path,output_path):

    cmd = [
        "ffmpeg",
        "-i", input_video_path,
        "-vf", f"subtitles={srt_path}",
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Subtitles burned into video and saved as {output_path}")

def combine_videos(fps:int,base_video_path: str, video_list: list[Video], audio_path: str, output_path: str):
    """
    Combine base video with overlay videos using ffmpeg.
    Each overlay is enabled during between(start_time, start_time+duration).
    The provided audio_path is mapped to the output (replacing any base audio).
    """
    # Build input arguments: base video, overlay videos, then audio
    inputs = ["-y", "-i", base_video_path]
    for v in video_list:
        inputs += ["-i", v.path]
    inputs += ["-i", audio_path]

    # Build filter_complex: first reset overlay timestamps with setpts, then overlay them.
    filter_parts = []
    prev_label = "[0:v]"
    for idx, v in enumerate(video_list, start=1):
        inp_label = f"[{idx}:v]"
        ov_label = f"[ov{idx}]"
        out_label = f"[v{idx}]"
        start = float(v.start_time)
        end = float(v.start_time + v.duration)
        # reset overlay timestamps so the overlay plays from its own t=0,
        # shifted to start seconds on the main timeline
        filter_parts.append(f"{inp_label} setpts=PTS-STARTPTS+{start}/TB {ov_label}")
        # overlay the prepared overlay; enable only during the time window
        filter_parts.append(f"{prev_label}{ov_label} overlay=(W-w)/2:(H-h)/2:enable='between(t,{start},{end})' {out_label}")
        prev_label = out_label

    ff_filter = ";".join(filter_parts) if filter_parts else None

    # Determine final video stream map
    if ff_filter:
        filter_args = ["-filter_complex", ff_filter]
        map_video = ["-map", prev_label]
    else:
        filter_args = []
        map_video = ["-map", "0:v"]

    # Audio input index is base (0) + overlays (len(video_list)) => next is len(video_list)+1
    audio_input_index = len(video_list) + 1
    map_audio = ["-map", f"{audio_input_index}:a"]

    # Output encoding / options
    encoding_opts = [
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest"
    ]

    cmd = ["ffmpeg"] + inputs + filter_args + encoding_opts + map_video + map_audio + [output_path]

    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        # show ffmpeg output for debugging, then raise a clearer error
        print("ffmpeg stdout:\n", e.stdout)
        print("ffmpeg stderr:\n", e.stderr)
        raise RuntimeError("ffmpeg failed, see stderr above") from e

def blur_effect(input_path: str, output_path: str):
    """
    Create a blurred background (scaled to 1920p height), crop a 1080x1920 center background,
    scale the original to 1080 width, then overlay it centered on the blurred background.
    """
    filter_complex = (
        "[0:v]scale=-2:1920,boxblur=20:1[big];"
        "[big]crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2[bg];"
        "[0:v]scale=-2:1080[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
        "-c:a", "copy",
        output_path
    ]

    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Processed video saved as {output_path}")
    except subprocess.CalledProcessError as e:
        print("ffmpeg stdout:\n", e.stdout)
        print("ffmpeg stderr:\n", e.stderr)
        raise RuntimeError("ffmpeg failed while applying blurred background/overlay") from e