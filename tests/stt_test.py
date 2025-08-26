from g_maker.services import ai_api_clients
from g_maker.processing import srt_processing
t = ai_api_clients.stt_elevenlabs("test_data/old/audio.mp3")
print(t)

srt_processing.generate_srt_file_11(t["words"], words_per_subtitle=1, output_path="output.srt")

