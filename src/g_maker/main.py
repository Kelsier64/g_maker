import os
import time
import warnings
from uuid import uuid4
from pysubs2 import Color

from g_maker.services import t2v_api_client
from g_maker.services import ai_api_clients
from g_maker.processing import make_speaker
from g_maker.processing import video_processing
from g_maker.processing import srt_processing
from g_maker.input import downloader
from g_maker.models import Prompt,PromptList,Video,Script,ScriptList
from g_maker.utils import terminal



warnings.filterwarnings("ignore", category=SyntaxWarning)

VIDEO_FPS = 16

# Add a single global PATHS dict for all built-in paths
PATHS = {
    "GENERATED_VIDEOS_DIR": "./generated_videos",
    "FINAL_VIDEOS_DIR": "./output",
    "TEMP_DIR": "./temp",
    "AUDIO_PATH": "./temp/audio.mp3",
    "BASE_VIDEO": "./temp/base_video.mp4",
    "COMBINED_VIDEO": "./temp/combined_video.mp4",
    "BLURRED_VIDEO": "./temp/blurred_video.mp4",
    "REF_AUDIO": "./temp/ref_audio.mp3",
    "SRT": "./temp/script_timestamps.srt",
    "ASS": "./temp/subtitles.ass",
    "CLOSE_JPG": "./static/close.jpg",
    "OPEN_JPG": "./static/open.jpg",
}

# AI Prompts
PROMPT_GENERATE_VIDEO = """
You are given a transcript with timestamps.
Your task: generate a list of video generation prompts for a text-to-video system.
Rules:
1. Only create a prompt when there is a **significant scene or visual change** — NOT for every dialogue line.
2. Ensure prompts are **aligned with transcript timings** and only capture **meaningful visual transitions**.
3. videos don't need to stick together.
4. dont make a video while the previous one is in duration.
5. dont write any words on the image, just describe the scene.
6. the video generation model is poor ,so keep the prompts simple and focused.
7. no timeline graphic or chart or other overlays.
Output format:
   - "prompt": a vivid scene description matching the transcript and context.
   - "start_time": float, scene start time in seconds.
   - "duration": integer, duration of the scene in seconds.(max:15)
"""

PROMPT_SHORT_VIDEO = """
you are a expert script writer
Please break down the following content into one or several short-form video scripts suitable for platforms like TikTok or YouTube Shorts.

Requirements:
- Each script should be less than 180 seconds in total.
- Each script should be self-contained and understandable without prior context.
- Each script should have enough content.
- You can output just one script if the content fits within the 180-second limit.
- Each output should be a dictionary with the following keys:
  - 'title': A short, catchy video title.
  - 'script': The full narration for the video, written in a natural, spoken tone.

Script Writing Guidelines:
- The tone should be conversational, energetic, and easy to follow.
- Use short sentences, rhetorical questions, and emotional hooks to keep viewers engaged.
- Start strong — grab attention within the first few seconds,the hook at the start should be eye-catching and intriguing.
- End with a thought-provoking idea or light call to action (e.g. "What do you think?" or "Share this with a friend").
- Avoid formal or academic wording.
"""

PROMPT_CONTENT_CLEAN = """
You are a video script cleaning assistant. Your task is to refine a transcript by preserving the main content while removing unnecessary parts. Please do the following:
- translate to english.
- Remove introductory and closing greetings, such as "Hi everyone" or "Thanks for watching."
- Remove channel promotions, like "Remember to like and subscribe."
- Remove unrelated small talk or off-topic banter.
- Keep the original wording and tone as much as possible, with minor edits for clarity.
- Output a cleaned and concise version of the script that still feels authentic and natural.
Return only the cleaned script, no additional commentary.
"""

def video_pipeline(script,output_path):
    terminal.print_separator("Video Production Pipeline")
    
    # Step 1: Generate audio
    terminal.print_status("Step 1/7: Generating audio", "PROCESSING")
    ai_api_clients.tts(script,output_path=PATHS["AUDIO_PATH"])

    # Step 2: Create speaker video
    terminal.print_status("Step 2/7: Creating speaker video", "PROCESSING")
    spinner = terminal.SpinnerThread("Animating speaker...")
    spinner.start()
    make_speaker.create_speaker_video(
        mp3_path=PATHS["AUDIO_PATH"],
        closed_mouth_jpg=PATHS["CLOSE_JPG"],
        open_mouth_jpg=PATHS["OPEN_JPG"],
        output_path=PATHS["BASE_VIDEO"]
    )
    spinner.stop()
    terminal.print_status("Speaker video created", "SUCCESS")
    
    # Step 3: Generate SRT
    terminal.print_status("Step 3/7: Generating subtitles", "PROCESSING")
    script_timestamps = ai_api_clients.whisper(PATHS["AUDIO_PATH"])
    script_timestamps = script_timestamps.segments

    srt_processing.generate_srt_file(script_timestamps, output_path=PATHS["SRT"])

    style={
        "name": "Subtitle",
        "fontname": "DejaVu Sans",
        "fontsize": 10,                       
        "primarycolor": Color(255, 255, 255), # white text
        "secondarycolor": Color(255, 255, 255),
        "outlinecolor": Color(0, 0, 0),       # black outline for contrast
        "backcolor": Color(0, 0, 0),          # black background (used for some renderers)
        "bold": True,
        "italic": False,
        "underline": False,
        "strikeout": False,
        "scalex": 100,
        "scaley": 100,
        "spacing": 0,
        "angle": 0,
        "borderstyle": 1,  # outline+shadow
        "outline": 2,      # thin outline for readability
        "shadow": 0,       # small shadow to lift text off backgrounds
        "alignment": 2,    # bottom-center
        "marginv": 50,     # vertical margin from bottom/top
    }

    srt_processing.srt_to_ass(PATHS["SRT"], style_dict=style, output_path=PATHS["ASS"], effects=["fade", "random_colors"])
    terminal.print_status(f"Subtitles generated with {len(script_timestamps)} segments", "SUCCESS")

    # Step 4: Generate video prompts
    terminal.print_status("Step 4/7: Generating video prompts", "PROCESSING")
    script_for_ai = []
    for segment in script_timestamps:
        script_for_ai.append({
            "start": round(segment.start,1),
            "end": round(segment.end,1),
            "text": segment.text.strip()
        })
    msg =[
        {"role": "system", "content": PROMPT_GENERATE_VIDEO},
        {"role": "user","content": script_for_ai.__str__()}
    ]
    prompt4video = ai_api_clients.gpt_request(msg,PromptList)
    terminal.print_status(f"Generated {len(prompt4video.prompts)} video prompts", "SUCCESS")

    # Step 5: Submit video generation tasks
    terminal.print_status("Step 5/7: Submitting video generation tasks", "PROCESSING")
    video_list: list[Video] = []
    task_map = {}
    
    # Submit all video generation tasks and map task_id to video info
    submission_progress = terminal.ProgressBar(len(prompt4video.prompts), "Submitting tasks")
    for i, prompt in enumerate(prompt4video.prompts):
        video_path = f"{PATHS['GENERATED_VIDEOS_DIR']}/{prompt.start_time}_{prompt.duration}.mp4"
        task_id = t2v_api_client.submit_video_generation(
            prompt=prompt.prompt,
            sample_steps=50,
            fps=VIDEO_FPS,
            num_frames=prompt.duration * VIDEO_FPS + 1,
        )
        if task_id:
            task_map[task_id] = {
                "video_path": video_path,
                "start_time": prompt.start_time,
                "duration": prompt.duration
            }
        submission_progress.update()
        time.sleep(0.5)
    submission_progress.finish()

    # Step 6: Monitor and download videos
    terminal.print_status("Step 6/7: Monitoring video generation", "PROCESSING")
    download_progress = terminal.ProgressBar(len(task_map), "Downloading videos")
    for task_id, info in task_map.items():
        spinner = terminal.SpinnerThread(f"Generating video ({download_progress.current + 1}/{len(task_map)})...")
        spinner.start()
        video_filename = t2v_api_client.monitor_task(task_id)
        spinner.stop()
        
        if not video_filename:
            terminal.print_status(f"Failed to generate video for task {task_id}", "ERROR")
            breakpoint()
        
        t2v_api_client.download_video(video_filename, output_path=info["video_path"])
        video_list.append(Video(
            path=info["video_path"],
            start_time=info["start_time"],
            duration=info["duration"]
        ))
        download_progress.update()
    download_progress.finish()

    # Step 7: Final video assembly
    terminal.print_status("Step 7/7: Assembling final video", "PROCESSING")
    
    spinner = terminal.SpinnerThread("Combining videos...")
    spinner.start()
    video_processing.combine_videos(VIDEO_FPS, PATHS["BASE_VIDEO"], video_list, PATHS["AUDIO_PATH"], PATHS["COMBINED_VIDEO"])
    spinner.stop()
    terminal.print_status("Videos combined", "SUCCESS")

    spinner = terminal.SpinnerThread("Applying blur effect...")
    spinner.start()
    video_processing.blur_effect(input_path=PATHS["COMBINED_VIDEO"], output_path=PATHS["BLURRED_VIDEO"])
    spinner.stop()
    terminal.print_status("Blur effect applied", "SUCCESS")

    spinner = terminal.SpinnerThread("Burning subtitles...")
    spinner.start()
    video_processing.burn_ass_subtitle(PATHS["BLURRED_VIDEO"], PATHS["ASS"], output_path=output_path)
    spinner.stop()
    terminal.print_status(f"Final video saved: {output_path}", "SUCCESS")

def init():
    """Initialize directories and clean up temporary files"""
    dirs_cleaned = 0
    files_removed = 0
    
    if os.path.exists(PATHS["GENERATED_VIDEOS_DIR"]):
        for filename in os.listdir(PATHS["GENERATED_VIDEOS_DIR"]):
            file_path = os.path.join(PATHS["GENERATED_VIDEOS_DIR"], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                files_removed += 1
        dirs_cleaned += 1
    else:
        os.makedirs(PATHS["GENERATED_VIDEOS_DIR"])

    if os.path.exists(PATHS["TEMP_DIR"]):
        for filename in os.listdir(PATHS["TEMP_DIR"]):
            file_path = os.path.join(PATHS["TEMP_DIR"], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                files_removed += 1
        dirs_cleaned += 1
    else:
        os.makedirs(PATHS["TEMP_DIR"])
    
    if files_removed > 0:
        terminal.print_status(f"Cleaned {files_removed} temporary files from {dirs_cleaned} directories", "INFO")

def main_pipeline(url):
    terminal.print_separator("CONTENT PROCESSING PIPELINE")
    
    # Step 1: Download reference video
    terminal.print_status("Step 1/4: Downloading reference video", "PROCESSING")
    spinner = terminal.SpinnerThread(f"Downloading from {url[:50]}...")
    spinner.start()
    downloader.download_yt(url, output_path=PATHS["REF_AUDIO"])
    spinner.stop()
    terminal.print_status("Reference video downloaded", "SUCCESS")

    terminal.print_separator()

    # Step 2: Transcribe reference video
    terminal.print_status("Step 2/4: Transcribing reference video", "PROCESSING")
    ref_text = ai_api_clients.whisper(PATHS["REF_AUDIO"])
    os.remove(PATHS["REF_AUDIO"])
    ref_text = ref_text.text
    terminal.print_status(f"Transcription completed ({len(ref_text)} characters)", "SUCCESS")
    print(f"\033[90m{ref_text[:200]}...\033[0m")  # Show preview in gray

    # Step 3: Clean and process content
    terminal.print_separator()
    terminal.print_status("Step 3/4: Processing content", "PROCESSING")
    writer_msg = [{"role": "system", "content": PROMPT_CONTENT_CLEAN}, {"role": "user", "content": ref_text}]
    content = ai_api_clients.gpt_request(writer_msg)
    terminal.print_status(f"Content processed ({len(content)} characters)", "SUCCESS")
    print(f"\033[90m{content[:200]}...\033[0m")  # Show preview in gray

    terminal.print_separator()

    # Step 4: Generate short video scripts
    terminal.print_status("Step 4/4: Generating short video scripts", "PROCESSING")
    sv_writer_msg = [{"role": "system", "content": PROMPT_SHORT_VIDEO}, {"role": "user", "content": content}]
    sv_scripts = ai_api_clients.gpt_request(sv_writer_msg, ScriptList)
    terminal.print_status(f"Generated {len(sv_scripts.scripts)} video scripts", "SUCCESS")

    terminal.print_separator("VIDEO PRODUCTION")

    # Video making loop
    details_path = os.path.join(PATHS["FINAL_VIDEOS_DIR"], "video_details.txt")
    uid = uuid4().hex

    with open(details_path, "a", encoding="utf-8") as details_file:
        details_file.write(f"\nSeriesUid: {uid}, Url: {url}\n")

        for index, i in enumerate(sv_scripts.scripts):
            terminal.print_separator(f"Video {index + 1}/{len(sv_scripts.scripts)}: {i.title}")
            terminal.print_status(f"Script preview: {i.script[:100]}...", "INFO")

            output_file = os.path.join(PATHS["FINAL_VIDEOS_DIR"], f"{uid}_{index}.mp4")
            
            start = time.perf_counter()
            video_pipeline(i.script, output_path=output_file)
            elapsed = time.perf_counter() - start
            details_file.write(f"   Video: {index}, Title: {i.title}, FileName: {output_file}, ElapsedSeconds:{elapsed:.2f}\n")

            terminal.print_status(f"Video {index + 1} completed in {elapsed:.1f}s", "SUCCESS")

    terminal.print_separator()
    terminal.print_status(f"Series {uid} completed successfully!", "SUCCESS")

def main():
    terminal.print_separator("G-MAKER VIDEO GENERATOR")
    terminal.print_status("Initializing system...", "PROCESSING")

    if not t2v_api_client.check_health():
        terminal.print_status("T2V API is not healthy. Exiting...", "ERROR")
        return

    terminal.print_status("T2V API is healthy", "SUCCESS")

    # init
    terminal.print_status("Cleaning up temporary files...", "PROCESSING")
    init()
    t2v_api_client.clean_queue()
    t2v_api_client.clean_all_video()
    terminal.print_status("Cleanup completed", "SUCCESS")

    # Ensure directories exist
    for dir_name, dir_path in [
        ("Final videos", PATHS["FINAL_VIDEOS_DIR"]),
        ("Generated videos", PATHS["GENERATED_VIDEOS_DIR"]),
        ("Temporary files", PATHS["TEMP_DIR"])
    ]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            terminal.print_status(f"{dir_name} directory created", "INFO")

    terminal.print_separator("READY TO PROCESS")

    while True:
        urls = []
        while True:
            print("\n\033[1m🎬 G-Maker Menu:\033[0m")
            print("1. Add a YouTube URL")
            print("2. Add multiple YouTube URLs (comma-separated)")
            print("3. Start processing")
            print("4. Clear output dir")
            print("5. Exit")
            choice = input("\n\033[36mEnter your choice: \033[0m").strip()

            if choice == "1":
                u = input("\033[36mEnter the YouTube URL: \033[0m").strip()
                if u:
                    urls.append(u)
                    terminal.print_status(f"Added URL: {u[:50]}...", "SUCCESS")
                else:
                    terminal.print_status("No URL entered", "WARNING")
            elif choice == "2":
                s = input("\033[36mEnter URLs separated by commas: \033[0m").strip()
                new_urls = [x.strip() for x in s.split(",") if x.strip()]
                if new_urls:
                    urls.extend(new_urls)
                    terminal.print_status(f"Added {len(new_urls)} URLs", "SUCCESS")
                else:
                    terminal.print_status("No URLs entered", "WARNING")
            elif choice == "3":
                if not urls:
                    terminal.print_status("No URLs provided. Please add at least one URL.", "WARNING")
                    continue
                terminal.print_status(f"Starting processing of {len(urls)} URLs...", "PROCESSING")
                break
            elif choice == "4":
                terminal.print_status("Clearing output directory...", "PROCESSING")
                files_removed = 0

                if os.path.exists(PATHS["FINAL_VIDEOS_DIR"]):
                    for filename in os.listdir(PATHS["FINAL_VIDEOS_DIR"]):
                        file_path = os.path.join(PATHS["FINAL_VIDEOS_DIR"], filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            files_removed += 1
                else:
                    os.makedirs(PATHS["FINAL_VIDEOS_DIR"])

                if files_removed > 0:
                    terminal.print_status(f"Cleared {files_removed} files from {PATHS['FINAL_VIDEOS_DIR']}", "SUCCESS")

            elif choice == "5":
                terminal.print_status("Exiting...", "INFO")
                return
            else:
                terminal.print_status("Invalid choice, please try again.", "WARNING")

        # Process URLs
        overall_progress = terminal.ProgressBar(len(urls), "Overall progress")
        for idx, url in enumerate(urls):
            try:
                terminal.print_separator(f"Processing URL {idx + 1}/{len(urls)}")
                terminal.print_status(f"URL: {url}", "INFO")
                main_pipeline(url)
                overall_progress.update()
            except Exception as e:
                terminal.print_status(f"Error processing {url}: {e}", "ERROR")
                overall_progress.update()

        overall_progress.finish()
        terminal.print_separator("BATCH COMPLETE")
        terminal.print_status("All URLs processed successfully!", "SUCCESS")

if __name__ == "__main__":
    main()