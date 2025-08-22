from g_maker.processing import video_processing

video_processing.burn_subtitle("./test_data/blurred_video.mp4", "./test_data/script_timestamps.srt", "test_output.mp4", fontsize=10, margin_v=50)