from gpt_sovits_python import TTS, TTS_Config  # 根据需要调整导入
import soundfile as sf
import nltk
nltk.download('averaged_perceptron_tagger_eng')

# ...existing TTS pipeline code...
config_dict = {
    "default": {
        "device": "cuda",
        "is_half": True,
        "t2s_weights_path": "models/gpt.ckpt",
        "vits_weights_path": "models/sovits.pth",
        "cnhuhbert_base_path": "models/chinese-hubert-base",
        "bert_base_path": "models/chinese-roberta-wwm-ext-large",
    }
}
tts_config = TTS_Config(config_dict)
tts_pipeline = TTS(tts_config)

params = {
    "text": "爲什麽不找找自己的問題呢",
    "text_lang": "zh",
    "ref_audio_path": "ref.wav",
    "top_k": 5,
    "text_split_method": "cut2",
}

sr, audio_data = next(tts_pipeline.run(params))

sf.write("test.wav", audio_data, sr)