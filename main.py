from download import download_mp3_from_youtube
import os,sys
from openai import AzureOpenAI
from dotenv import load_dotenv
import requests
import yt_dlp
load_dotenv()
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
RESOURCE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

text = """
從前有一位名叫阿傑的年輕工程師，他對修理電子產品特別有一套。有一天，他在跳蚤市場上買到了一台老舊的烤麵包機，樣子古怪、又重又髒，標價只要10元。他想著：「拆開來看看也不虧。」

回家後，他擦乾淨機身，插上電源，一按下按鈕，竟然聽到「喀啦」一聲——不是機器聲，而是一個低沉的聲音說：

「終於有人喚醒我了…」

阿傑：「欸？誰在說話？」

烤麵包機：「我。是我。你面前的烤麵包機。」

阿傑以為自己幻聽，直到那台烤麵包機開始自我介紹，聲音像是英國老紳士。

烤麵包機：「我是阿爾弗雷德，前任皇家御廚的智能助手。被流放到這個跳蚤市場已經15年了。」

阿傑好奇地問：「你會做什麼？」

阿爾弗雷德：「我能分析你的心情，推薦適合的吐司厚度和果醬比例。還能講笑話。你要聽個嗎？」

阿傑笑著點頭。

阿爾弗雷德：「為什麼吐司從來不參加馬拉松？因為他總是在起跑線上就焦了！」

阿傑差點笑到吐司掉地上。從此，他和阿爾弗雷德每天早上都聊天、吃早餐、討論人生哲理。幾個月後，阿傑把這台會說話的烤麵包機拍成影片放到網路上，結果爆紅。

但有一天，阿爾弗雷德突然說：

「阿傑，我的任務完成了。我的真正使命，是幫助你開啟人生的味蕾。」

說完，他自動斷電，永遠沉睡。

阿傑很難過，但他決定創業，開了一家早餐店，名字叫：

「阿爾弗雷德的吐司」。

店裡每天都播著阿爾弗雷德留下的語音錄音——「記得把生活烤得恰到好處。」
"""

def gpt4o_transcribe(path):

    url = f"{RESOURCE_ENDPOINT}/openai/deployments/gpt-4o-transcribe/audio/transcriptions?api-version=2025-03-01-preview"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    files = {
        "file": open(path, "rb"),
    }
    data = {
        "model": "gpt-4o-transcribe",
    }
    response = requests.post(url, headers=headers, files=files, data=data)
    response.raise_for_status()
    result = response.json()
    return result["text"]

def download_yt_mp3(url, output_path="./sound.mp3"):
    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Extract filename without extension
    filename = os.path.splitext(os.path.basename(output_path))[0]
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',  # Standard quality
        }],
        'outtmpl': output_path.replace('.mp3', ''),  # yt-dlp will add .mp3 extension automatically
        'keepvideo': False,  # True if you want to keep the downloaded video
        'noplaylist': True,  # Download only the video, not playlist if URL is part of one
        'quiet': True, # Suppress console output from yt-dlp
        # 'no_warnings': True, # Suppress warnings
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"An error occurred: {e}")



def main(url):
    download_yt_mp3(url)
    
    text = gpt4o_transcribe("sound.mp3")
    print(text)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # url = sys.argv[1]
        # main(url)
        print(text)
        
    else:
        main()