from g_maker.services import ai_api_clients

# text = ai_api_clients.whisper_text("test_data/audio.mp3")

# print(text)

script_timestamps = ai_api_clients.whisper_timestamp("temp/audio.mp3")

print(script_timestamps)