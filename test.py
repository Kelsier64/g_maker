import subprocess
from pydantic import BaseModel
VIDEO_FPS = 16
class Video(BaseModel):
    path: str
    start_time: float
    duration: float


def combine_videos(base_video_path: str, video_list: list[Video], audio_path: str, output_path: str):
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
        filter_parts.append(f"{prev_label}{ov_label} overlay=0:0:enable='between(t,{start},{end})' {out_label}")
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
        "-r", str(VIDEO_FPS),
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


def main():
    video_list = [Video(path="generated_videos/0.0_4.mp4", start_time=0.0, duration=4.0),
                  Video(path="generated_videos/4.0_5.mp4", start_time=4.0, duration=5.0),
                  Video(path="generated_videos/12.0_3.mp4", start_time=12.0, duration=3.0),
                  Video(path="generated_videos/26.0_6.mp4", start_time=26.0, duration=6.0),
                  Video(path="generated_videos/63.0_7.mp4", start_time=63.0, duration=7.0),
                  Video(path="generated_videos/78.0_7.mp4", start_time=78.0, duration=7.0),
                  Video(path="generated_videos/94.0_6.mp4", start_time=94.0, duration=6.0),
                  ]


    combine_videos(base_video_path = "speaker_video.mp4", video_list = video_list, audio_path="sound.mp3", output_path="output_video.mp4")

if __name__ == "__main__":
    main()

