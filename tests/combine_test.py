from g_maker.processing import video_processing
from g_maker.models import Video

video_list = [
    Video(path="./generated_videos/0.0_4.mp4", start_time=0.0, duration=4),
    Video(path="./generated_videos/9.1_5.mp4", start_time=9.1, duration=5),
    Video(path="./generated_videos/23.3_7.mp4", start_time=23.3, duration=7),
    Video(path="./generated_videos/34.6_5.mp4", start_time=34.6, duration=5),
    Video(path="./generated_videos/43.6_5.mp4", start_time=43.6, duration=5),
    Video(path="./generated_videos/55.3_7.mp4", start_time=55.3, duration=7)
]


video_processing.combine_videos(16,"./temp/base_video.mp4",video_list,"temp/audio.mp3","test.mp4")