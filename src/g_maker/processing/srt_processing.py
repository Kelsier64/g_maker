import os
import pysubs2
import random
from g_maker.config import STT_MODE

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (00:00:00,000)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60
    milliseconds = int((seconds_remainder - int(seconds_remainder)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{int(seconds_remainder):02d},{milliseconds:03d}"

def generate_srt_file(timestamps, output_path):

    """
    Generate an SRT subtitle file from transcript segments.
    
    Args:
        segments: List of transcript segments with start, end, and text properties
        output_path: Path to save the SRT file
    
    Returns:
        Path to the generated SRT file
    """
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_path, "w", encoding="utf-8") as f:
        prev_end_time = 0
        for i, segment in enumerate(timestamps, start=1):
            start_time = segment.start
            end_time = segment.end
            
            if end_time == start_time:
                # Get next segment's start time if available
                if i < len(timestamps):
                    end_time = timestamps[i].start
                    start_time = prev_end_time

            prev_end_time = end_time


            if STT_MODE == "word":
                text = segment.word
            elif STT_MODE == "segment":
                text = segment.text.strip()

            # Format timestamps as SRT format (00:00:00,000)
            start_formatted = format_timestamp(start_time)
            end_formatted = format_timestamp(end_time)
            
            # Write the subtitle entry
            f.write(f"{i}\n")
            f.write(f"{start_formatted} --> {end_formatted}\n")
            f.write(f"{text}\n\n")
    
    return output_path

def generate_srt_file_11(words, output_path):
    """
    Create an SRT file from word data.
    
    Args:
        words: List of word dictionaries with 'text', 'start', 'end' keys
        output_path: Path for the output SRT file
    """
    srt_content = []
    subtitle_number = 1
    
    # Filter out spacing elements and group words, excluding commas and periods
    word_data = [w for w in words if w.get('type') == 'word' ]
    
    # Always use 1 word per subtitle
    for word in word_data:
        start_time = word['start']
        end_time = word['end']
        t: str = word['text']
        text = t.rstrip('.,')
        
        start_formatted = format_timestamp(start_time)
        end_formatted = format_timestamp(end_time)
        
        srt_content.append(f"{subtitle_number}")
        srt_content.append(f"{start_formatted} --> {end_formatted}")
        srt_content.append(text)
        srt_content.append("")  # Empty line between subtitles
        
        subtitle_number += 1
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(srt_content))
    


def apply_fade_effects(subs, fade_in_ms=100, fade_out_ms=100, min_duration_ms=200):
    """
    Apply fade in/out effects to subtitle lines.
    
    Args:
        subs: pysubs2.SSAFile object
        fade_in_ms (int): Fade in duration in milliseconds
        fade_out_ms (int): Fade out duration in milliseconds
        min_duration_ms (int): Minimum duration required to apply fade effects
    """
    for line in subs:
        # Calculate line duration in milliseconds
        duration_ms = line.end - line.start
        
        # Only apply fade if duration is sufficient
        if duration_ms >= min_duration_ms and (fade_in_ms > 0 or fade_out_ms > 0):
            # Adjust fade times if they exceed half the duration
            actual_fade_in = min(fade_in_ms, duration_ms // 2)
            actual_fade_out = min(fade_out_ms, duration_ms // 2)
            
            fade_tag = ""
            if actual_fade_in > 0 and actual_fade_out > 0:
                fade_tag = f"{{\\fad({actual_fade_in},{actual_fade_out})}}"
            elif actual_fade_in > 0:
                fade_tag = f"{{\\fad({actual_fade_in},0)}}"
            elif actual_fade_out > 0:
                fade_tag = f"{{\\fad(0,{actual_fade_out})}}"
            
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

def apply_popup_effect(subs, scale_duration_ms=100):
    """
    Apply popup effect to subtitle lines (scale from small to normal size).
    
    Args:
        subs: pysubs2.SSAFile object
        scale_duration_ms (int): Duration of the scaling animation in milliseconds
    """
    for line in subs:
        # Create scaling animation from 0% to 100% over the specified duration
        popup_tag = f"{{\\t(0,{scale_duration_ms},\\fscx0\\fscy0)\\t(0,{scale_duration_ms},\\fscx100\\fscy100)}}"
        line.text = popup_tag + line.text


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
        
    if "popup" in effects:
        apply_popup_effect(subs, 100)

    
    # Save as ASS file
    subs.save(output_path)