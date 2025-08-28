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
from g_maker.video_manager import video_manager
from g_maker.utils import terminal
from g_maker.prompts import PROMPT_GENERATE_VIDEO, PROMPT_SHORT_VIDEO, PROMPT_CONTENT_CLEAN
from g_maker.config import PATHS, VIDEO_FPS,STT_MODE,G_VIDEO_FPS

warnings.filterwarnings("ignore", category=SyntaxWarning)

def video_pipeline(script, output_path, title="Generated Video"):
    terminal.print_separator("Video Production Pipeline")
    
    # Create video project in database
    video_id = video_manager.create_video_project(title=title, script=script)
    
    try:
        # Step 1: Generate audio
        video_manager.start_processing(video_id, "audio_generation", "Generating speech from script")
        terminal.print_status("Step 1/7: Generating audio", "PROCESSING")
        ai_api_clients.tts(script, output_path=PATHS["AUDIO_PATH"])
        video_manager.complete_processing_step(video_id, "audio_generation", "Audio generated successfully")

        # Step 2: Create speaker video
        video_manager.start_processing(video_id, "speaker_video", "Creating animated speaker video")
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
        video_manager.complete_processing_step(video_id, "speaker_video", "Speaker video created")
        
        # Step 3: Generate SRT
        video_manager.start_processing(video_id, "subtitle_generation", f"Generating subtitles using {STT_MODE} mode")
        terminal.print_status("Step 3/7: Generating subtitles", "PROCESSING")
        if STT_MODE == "segment":
            script_timestamps = ai_api_clients.whisper_timestamp(PATHS["AUDIO_PATH"])
            srt_processing.generate_srt_file(script_timestamps, output_path=PATHS["SRT"])

        elif STT_MODE == "word":
            response_11 = ai_api_clients.stt_elevenlabs(PATHS["AUDIO_PATH"])
            srt_processing.generate_srt_file_11(response_11["words"], output_path=PATHS["SRT"])

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

        srt_processing.srt_to_ass(PATHS["SRT"], style_dict=style, output_path=PATHS["ASS"], effects=["popup", "random_colors"])
        terminal.print_status(f"Subtitles generated", "SUCCESS")
        video_manager.complete_processing_step(video_id, "subtitle_generation", "Subtitles generated successfully")

        # Step 4: Generate video prompts
        video_manager.start_processing(video_id, "prompt_generation", "Generating AI video prompts")
        terminal.print_status("Step 4/7: Generating video prompts", "PROCESSING")
        script_for_ai = []
        if STT_MODE == "segment":
            for segment in script_timestamps:
                script_for_ai.append({
                    "start": round(segment.start,1),
                    "end": round(segment.end,1),
                    "text": segment.text.strip()
            })
                
        elif STT_MODE=="word":
            for word in response_11["words"]:
                script_for_ai.append({
                    "start": round(word["start"],1),
                    "end": round(word["end"],1),
                    "text": word["text"].strip()
                })

        msg =[
            {"role": "system", "content": PROMPT_GENERATE_VIDEO},
            {"role": "user","content": script_for_ai.__str__()}
        ]
        prompt4video = ai_api_clients.gpt_request(msg,PromptList)
        terminal.print_status(f"Generated {len(prompt4video.prompts)} video prompts", "SUCCESS")
        
        # Store prompts in database
        for prompt in prompt4video.prompts:
            video_manager.db.add_prompt(
                video_id=video_id,
                prompt=prompt.prompt,
                start_time=prompt.start_time,
                duration=prompt.duration
            )
        video_manager.complete_processing_step(video_id, "prompt_generation", f"Generated {len(prompt4video.prompts)} video prompts")

        # Step 5: Submit video generation tasks
        video_manager.start_processing(video_id, "video_generation", "Submitting video generation tasks")
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
                fps=G_VIDEO_FPS,
                num_frames=prompt.duration * G_VIDEO_FPS + 1,
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
                error_msg = f"Failed to generate video for task {task_id}"
                terminal.print_status(error_msg, "ERROR")
                video_manager.fail_processing_step(video_id, "video_generation", error_msg)
                raise Exception(error_msg)
            
            t2v_api_client.download_video(video_filename, output_path=info["video_path"])
            video_list.append(Video(
                path=info["video_path"],
                start_time=info["start_time"],
                duration=info["duration"]
            ))
            download_progress.update()
        download_progress.finish()
        video_manager.complete_processing_step(video_id, "video_generation", f"Generated {len(video_list)} video segments")

        # Step 7: Final video assembly
        video_manager.start_processing(video_id, "video_assembly", "Assembling final video")
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
        
        # Register final video in database
        video_manager.set_video_file(video_id, output_path)
        video_manager.complete_processing_step(video_id, "video_assembly", f"Final video saved to {output_path}")
        
        return video_id
        
    except Exception as e:
        error_msg = f"Video pipeline failed: {str(e)}"
        terminal.print_status(error_msg, "ERROR")
        video_manager.fail_processing_step(video_id, "pipeline_error", error_msg)
        raise

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
    ref_text = ai_api_clients.whisper_text(PATHS["REF_AUDIO"])
    os.remove(PATHS["REF_AUDIO"])

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
            init()
            video_id = video_pipeline(i.script, output_path=output_file, title=i.title)
            elapsed = time.perf_counter() - start
            details_file.write(f"   Video: {index}, Title: {i.title}, FileName: {output_file}, ElapsedSeconds:{elapsed:.2f}, VideoID: {video_id}\n")

            terminal.print_status(f"Video {index + 1} completed in {elapsed:.1f}s", "SUCCESS")

    terminal.print_separator()
    terminal.print_status(f"Series {uid} completed successfully!", "SUCCESS")

def main():
    terminal.print_separator("G-MAKER VIDEO GENERATOR")
    terminal.print_status("Initializing system...", "PROCESSING")


    # if not t2v_api_client.check_health():
    #     terminal.print_status("T2V API is not healthy. Exiting...", "ERROR")
    #     return
    # terminal.print_status("T2V API is healthy", "SUCCESS")

    # # init
    # terminal.print_status("Cleaning up temporary files...", "PROCESSING")
    # init()
    # t2v_api_client.clean_queue()
    # t2v_api_client.clean_all_video()
    # terminal.print_status("Cleanup completed", "SUCCESS")

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
            print("5. View video database")
            print("6. Show database stats")
            print("7. View video details")
            print("8. Delete video")
            print("9. Exit")
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
                # View video database
                videos = video_manager.list_videos(limit=20)
                if not videos:
                    terminal.print_status("No videos in database", "INFO")
                else:
                    print(f"\n\033[1m📹 Recent Videos (showing {len(videos)}):\033[0m")
                    for video in videos:
                        status_color = {"completed": "32", "processing": "33", "failed": "31", "created": "36"}.get(video.status, "37")
                        duration_str = f"{video.duration:.1f}s" if video.duration else "N/A"
                        size_str = f"{video.file_size/(1024*1024):.1f}MB" if video.file_size else "N/A"
                        print(f"  ID: {video.id} | \033[{status_color}m{video.status.upper()}\033[0m | {video.title[:40]:<40} | {duration_str} | {size_str}")
                
            elif choice == "6":
                # Show database stats
                video_manager.print_stats()
                
            elif choice == "7":
                # View video details
                try:
                    video_id = int(input("\033[36mEnter video ID: \033[0m").strip())
                    video_manager.print_video_info(video_id)
                except ValueError:
                    terminal.print_status("Invalid video ID", "ERROR")
                    
            elif choice == "8":
                # Delete video
                try:
                    video_id = int(input("\033[36mEnter video ID to delete: \033[0m").strip())
                    video = video_manager.get_video(video_id)
                    if video:
                        confirm = input(f"\033[33mAre you sure you want to delete '{video.title}'? (yes/no): \033[0m").strip().lower()
                        if confirm == "yes":
                            if video_manager.delete_video(video_id):
                                terminal.print_status("Video deleted successfully", "SUCCESS")
                            else:
                                terminal.print_status("Failed to delete video", "ERROR")
                        else:
                            terminal.print_status("Deletion cancelled", "INFO")
                    else:
                        terminal.print_status("Video not found", "ERROR")
                except ValueError:
                    terminal.print_status("Invalid video ID", "ERROR")

            elif choice == "9":
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