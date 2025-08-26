from pysubs2 import Color
from g_maker.processing import srt_processing

if __name__ == "__main__":
    input_srt="test_data/script_timestamps.srt"
    output_ass="test_data/subtitles.ass"
    custom_style = {
        "name": "Subtitle",
        "fontname": "DejaVu Sans",
        "fontsize": 10,                       # good for 1080p; lower for SD, higher for 4K
        "primarycolor": Color(255, 255, 255), # white text
        "secondarycolor": Color(255, 255, 255),
        "outlinecolor": Color(0, 0, 0),       # black outline for contrast
        "backcolor": Color(0, 0, 0),          # black background (used for some renderers)
        "bold": True,
        "italic": False,
        "underline": False,
        "strikeout": False,
        "scalex": 100,
        "scaley": 100,
        "spacing": 0,
        "angle": 0,
        "borderstyle": 1,  # outline+shadow
        "outline": 2,      # thin outline for readability
        "shadow": 0,       # small shadow to lift text off backgrounds
        "alignment": 2,    # bottom-center

        "marginv": 50,     # vertical margin from bottom/top
    }
    

    srt_processing.srt_to_ass(input_srt, output_ass, custom_style)


    