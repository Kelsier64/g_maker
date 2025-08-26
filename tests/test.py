import os

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def create_srt_from_words(words, output_path="output.srt", words_per_subtitle=5):
    """
    Create an SRT file from word data.
    
    Args:
        words: List of word dictionaries with 'text', 'start', 'end' keys
        output_path: Path for the output SRT file
        words_per_subtitle: Number of words to group per subtitle line
    """
    srt_content = []
    subtitle_number = 1
    
    # Filter out spacing elements and group words
    word_data = [w for w in words if w.get('type') == 'word']
    
    for i in range(0, len(word_data), words_per_subtitle):
        group = word_data[i:i + words_per_subtitle]
        
        start_time = group[0]['start']
        end_time = group[-1]['end']
        
        text = ' '.join(word['text'] for word in group)
        
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
    
    print(f"SRT file created: {output_path}")

# Test with your data
words = [
    {
        "text": "Ever",
        "start": 0.14,
        "end": 0.28,
        "type": "word",
        "logprob": 0
    },
    {
        "text": " ",
        "start": 0.28,
        "end": 0.339,
        "type": "spacing",
        "logprob": 0
    },
    {
        "text": "wondered",
        "start": 0.34,
        "end": 0.579,
        "type": "word",
        "logprob": 0
    }
]

# Create SRT file
create_srt_from_words(words, "example.srt", words_per_subtitle=2)
