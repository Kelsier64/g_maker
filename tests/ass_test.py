import pysubs2
import random

def apply_fade_effects(subs, fade_in_ms=100, fade_out_ms=100):
    """
    Apply fade in/out effects to subtitle lines.
    
    Args:
        subs: pysubs2.SSAFile object
        fade_in_ms (int): Fade in duration in milliseconds
        fade_out_ms (int): Fade out duration in milliseconds
    """
    for line in subs:
        if fade_in_ms > 0 or fade_out_ms > 0:
            fade_tag = ""
            if fade_in_ms > 0 and fade_out_ms > 0:
                fade_tag = f"{{\\fad({fade_in_ms},{fade_out_ms})}}"
            elif fade_in_ms > 0:
                fade_tag = f"{{\\fad({fade_in_ms},0)}}"
            elif fade_out_ms > 0:
                fade_tag = f"{{\\fad(0,{fade_out_ms})}}"
            
            line.text = fade_tag + line.text


def apply_random_colors(subs):
    """
    Apply random colorful colors to each subtitle line.
    
    Args:
        subs: pysubs2.SSAFile object
    """
    colors = [
        "00FFFF",
        "7FFFD4",
        "AAFF00",
        "7C7C00",
        "0FFF50",
        "00FF7F",
        "FF00FF",
        "E0B0FF"
    ]
    
    for line in subs:
        color = random.choice(colors)
        color_tag = f"{{\\c&H{color}&}}"
        line.text = color_tag + line.text


def srt_to_ass(srt_file_path, output_path, style_dict=None, effects: list[str] = None):
    """
    Convert SRT subtitle file to ASS format.
    
    Args:
        srt_file_path (str): Path to input SRT file
        output_path (str): Path to output ASS file
        style_dict (dict): Dictionary containing style parameters
        effects (list[str]): List of effects to apply. Supported values (case-insensitive):
                             "fade", "random_colors", "fade_colors" (legacy: applies both)
    """
    # Load the SRT file
    subs = pysubs2.load(srt_file_path)
    
    if style_dict:
        # Create a custom style
        style = pysubs2.SSAStyle()

        # Apply style parameters from dictionary with defaults
        style.fontname = style_dict.get('fontname', 'Arial')
        style.fontsize = style_dict.get('fontsize', 10)
        style.primarycolor = style_dict.get('primarycolor', pysubs2.Color(255, 255,255))
        style.secondarycolor = style_dict.get('secondarycolor', pysubs2.Color(255, 0, 0))
        style.outlinecolor = style_dict.get('outlinecolor', pysubs2.Color(0, 0, 0))
        style.backcolor = style_dict.get('backcolor', pysubs2.Color(0, 0, 0))
        style.bold = style_dict.get('bold', True)
        style.italic = style_dict.get('italic', False)
        style.underline = style_dict.get('underline', False)
        style.strikeout = style_dict.get('strikeout', False)
        style.scalex = style_dict.get('scalex', 100)
        style.scaley = style_dict.get('scaley', 100)
        style.spacing = style_dict.get('spacing', 0)
        style.angle = style_dict.get('angle', 0)
        style.borderstyle = style_dict.get('borderstyle', 1)
        style.outline = style_dict.get('outline', 2)
        style.shadow = style_dict.get('shadow', 0)
        style.alignment = style_dict.get('alignment', 2)  # Bottom center
        style.marginl = style_dict.get('marginl', 0)
        style.marginr = style_dict.get('marginr', 0)
        style.marginv = style_dict.get('marginv', 50)

        subs.styles["Default"] = style
        
        # Apply the style to all lines
        for line in subs:
            line.style = "Default"
    
    # Normalize effects input
    effects = [e.lower() for e in effects] if effects else []
    if "fade" in effects:
        apply_fade_effects(subs, 20, 100)
    
    if "random_colors" in effects:
        apply_random_colors(subs)

    
    # Save as ASS file
    subs.save(output_path)


if __name__ == "__main__":
    input_srt="test_data/script_timestamps.srt"
    output_ass="test_data/subtitles.ass"
    custom_style = {
        "name": "Subtitle",
        "fontname": "DejaVu Sans",
        "fontsize": 10,                       # good for 1080p; lower for SD, higher for 4K
        "primarycolor": pysubs2.Color(255, 255, 255), # white text
        "secondarycolor": pysubs2.Color(255, 255, 255),
        "outlinecolor": pysubs2.Color(0, 0, 0),       # black outline for contrast
        "backcolor": pysubs2.Color(0, 0, 0),          # black background (used for some renderers)
        "bold": True,
        "italic": False,
        "underline": False,
        "strikeout": False,
        "scalex": 100,
        "scaley": 100,
        "spacing": 0,
        "angle": 0,
        "borderstyle": 1,  # outline+shadow
        "outline": 1,      # thin outline for readability
        "shadow": 0,       # small shadow to lift text off backgrounds
        "alignment": 2,    # bottom-center

        "marginv": 50,     # vertical margin from bottom/top
    }

    srt_to_ass(input_srt, output_ass, custom_style, effects=["fade", "random_colors"])