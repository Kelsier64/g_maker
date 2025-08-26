import pysubs2
from g_maker.processing import srt_processing


if __name__ == "__main__":
    input_srt="test_data/script_timestamps.srt"
    output_ass="test_output.ass"
    custom_style = {
            'fontname': 'Arial',
            'fontsize': 10,
            'primarycolour': (0,0,0),
            'outlinecolour': (255, 255, 255),  # White outline
            'bold': True,
            'outline': 3,
            'shadow': 2,
            'alignment': 2,  # Bottom center
            'marginv': 50
        }
    srt_processing.srt_to_ass(input_srt, custom_style, output_ass)
