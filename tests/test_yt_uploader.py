from g_maker.services import yt_uploader

r = yt_uploader.upload_video_to_youtube("test_data/old/blurred_video.mp4", "Test Video", "This is a test video.", ["test", "video"], "public")
print(r)