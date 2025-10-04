import os
import subprocess

def speed_up_video(input_path, speed_factor=1.25):
    """
    Speeds up a video using ffmpeg.

    Args:
        input_path (str): The path to the input video file.
        speed_factor (int, optional): The factor by which to speed up the video. Defaults to 2.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    directory, filename = os.path.split(input_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(directory, f"{name}_fast_{speed_factor}x{ext}")

    # Construct the ffmpeg command
    # -i: input file
    # -filter:v "setpts=PTS/{speed_factor}": speeds up the video by the given factor
    # -filter:a "atempo={speed_factor}": speeds up the audio by the given factor
    # -y: overwrite output file if it exists
    command = [
        "ffmpeg",
        "-i", input_path,
        "-vf", f"setpts=PTS/{speed_factor}",
        "-af", f"atempo={speed_factor}",
        "-y",
        output_path,
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Video successfully sped up and saved to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error during ffmpeg execution: {e}")
    except FileNotFoundError:
        print("Error: ffmpeg is not installed or not in your PATH.")

if __name__ == "__main__":
    # Example usage:
    # Replace with the actual path to your video file
    video_path = input("Enter the path to the video file: ")
    speed_up_video(video_path, speed_factor=1.25)
