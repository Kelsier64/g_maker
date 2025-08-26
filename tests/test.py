import pysubs2
import subprocess
import shlex
from subprocess import CalledProcessError

def srt_to_ass(srt_file_path, ass_file_path, style_dict=None):
    """
    Convert SRT subtitle file to ASS format.
    
    Args:
        srt_file_path (str): Path to input SRT file
        ass_file_path (str): Path to output ASS file
        style_dict (dict): Dictionary containing style parameters
    """
    # Load the SRT file
    subs = pysubs2.load(srt_file_path)
    
    if style_dict:
        # Create a custom style
        style = pysubs2.SSAStyle()
        
        # Apply style parameters from dictionary with defaults
        style.fontname = style_dict.get('fontname', 'Arial')
        style.fontsize = style_dict.get('fontsize', 20)
        style.primarycolour = style_dict.get('primarycolour', pysubs2.Color(255, 255, 255))  # White
        style.secondarycolour = style_dict.get('secondarycolour', pysubs2.Color(255, 0, 0))  # Red
        style.outlinecolour = style_dict.get('outlinecolour', pysubs2.Color(0, 0, 0))  # Black
        style.backcolour = style_dict.get('backcolour', pysubs2.Color(0, 0, 0))  # Black
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
        style.shadow = style_dict.get('shadow', 1)
        style.alignment = style_dict.get('alignment', 2)  # Bottom center
        style.marginl = style_dict.get('marginl', 0)
        style.marginr = style_dict.get('marginr', 0)
        style.marginv = style_dict.get('marginv', 30)
        
        # Add the style to the subtitle file
        subs.styles["Default"] = style
        
        # Apply the style to all lines
        for line in subs:
            line.style = "Default"
    
    # Save as ASS file
    subs.save(ass_file_path)
    
    print(f"Converted {srt_file_path} to {ass_file_path}")

def test_srt_to_ass_conversion():
    """
    Test function to demonstrate SRT to ASS conversion.
    """
    # Example usage
    input_srt = "example.srt"
    output_ass = "example.ass"
    
    # Example style dictionary
    custom_style = {
        'fontname': 'Times New Roman',
        'fontsize': 24,
        'primarycolour': pysubs2.Color.YELLOW,
        'bold': False,
        'italic': True,
        'outline': 3,
        'shadow': 2
    }
    
    try:
        srt_to_ass(input_srt, output_ass, style_dict=custom_style)
        print("Conversion successful!")
    except FileNotFoundError:
        print(f"Error: {input_srt} not found")
    except Exception as e:
        print(f"Error during conversion: {e}")

def burn_subtitle(input_video_path: str, ass_path: str, output_path: str):
    """
    Burn ASS subtitles into a video.
    Uses ASS file which contains all styling information.
    """

    # Quote the ass path so ffmpeg receives it safely
    ass_quoted = shlex.quote(ass_path)

    # Use ass filter for better styling support
    filter_str = f"ass={ass_quoted}"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        output_path
    ]

    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"ASS subtitles burned into video and saved as {output_path}")
    except CalledProcessError as e:
        raise RuntimeError("ffmpeg failed while burning ASS subtitles") from e

def test_complete_workflow():
    """
    Test the complete workflow: SRT -> ASS conversion -> burn into video.
    """
    # Test file paths
    input_srt = "test_data/script_timestamps.srt"
    output_ass = "test_output.ass"
    input_video = "test_data/blurred_video.mp4"
    output_video = "test_video_with_subs.mp4"
    
    try:
        
        # Define custom style for the ASS file
        custom_style = {
            'fontname': 'Arial',
            'fontsize': 10,
            'primarycolour': pysubs2.Color(0, 0, 0),  # Black text
            'outlinecolour': pysubs2.Color(255, 255, 255),  # White outline
            'bold': True,
            'outline': 3,
            'shadow': 2,
            'alignment': 2,  # Bottom center
            'marginv': 50
        }
        
        # Convert SRT to ASS with custom styling
        srt_to_ass(input_srt, output_ass, style_dict=custom_style)
        print("✓ SRT to ASS conversion completed")
        
        # Test burning subtitles (only if video file exists)
        import os
        if os.path.exists(input_video):
            burn_subtitle(input_video, output_ass, output_video)
            print("✓ Subtitle burning completed")
        else:
            print(f"⚠ Video file {input_video} not found, skipping burn test")
        
        print("✓ All tests completed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")

if __name__ == "__main__":
    test_complete_workflow()
