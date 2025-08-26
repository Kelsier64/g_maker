from g_maker.processing import video_processing
from g_maker.models import Video

video_list = [
    Video(path="./test_data/0.0_3.mp4", start_time=0.0, duration=3),
    Video(path="./test_data/3.2_5.mp4", start_time=3.2, duration=5),
    Video(path="./test_data/13.6_7.mp4", start_time=13.6, duration=7),
    Video(path="./test_data/42.0_8.mp4", start_time=42.0, duration=8),
    Video(path="./test_data/66.9_10.mp4", start_time=66.9, duration=10)
]


video_processing.combine_videos(60,"test_data/base_video.mp4",video_list,"test_data/audio.mp3","test.mp4")