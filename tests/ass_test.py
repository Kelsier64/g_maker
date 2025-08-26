from pysubs2 import Color
from g_maker.processing import srt_processing

if __name__ == "__main__":
    input_srt="test_data/script_timestamps.srt"
    output_ass="test_data/subtitles.ass"
    custom_style = {
            'fontname': 'Arial',
            'fontsize': 10,
            'primarycolour': Color(0,255,0),
            'outlinecolour': Color(0, 0, 255),  # White outline
            'bold': True,
            'outline': 3,
            'shadow': 2,
            'alignment': 2,  # Bottom center
            'marginv': 50
        }
    srt_processing.srt_to_ass(input_srt, output_ass, custom_style)


    