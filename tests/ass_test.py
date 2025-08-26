from pysubs2 import Color
from g_maker.processing import srt_processing

if __name__ == "__main__":
    input_srt="test_data/script_timestamps.srt"
    output_ass="test_data/subtitles.ass"
    custom_style = {
            'fontname': 'Arial',
            'fontsize': 10,
            'primarycolor': Color(0,0,0),
            'outlinecolor': Color(255, 255, 255),  
            'bold': True,
            'outline': 1,
            'shadow': 2,
            'alignment': 2,  # Bottom center
            'marginv': 50
        }
    srt_processing.srt_to_ass(input_srt, output_ass, custom_style)


    