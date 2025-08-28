#!/usr/bin/env python3
"""
Test script for video database functionality
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from g_maker.video_manager import video_manager
from g_maker.models import PromptList, Prompt
from g_maker.utils import terminal

def test_database_functionality():
    """Test the database functionality without running the full pipeline."""
    
    terminal.print_separator("Testing Video Database Functionality")
    
    # Test 1: Create a video project
    terminal.print_status("Test 1: Creating video project", "PROCESSING")
    video_id = video_manager.create_video_project(
        title="Test Video",
        script="This is a test script for database functionality."
    )
    terminal.print_status(f"Created video project with ID: {video_id}", "SUCCESS")
    
    # Test 2: Add some prompts
    terminal.print_status("Test 2: Adding prompts", "PROCESSING")
    test_prompts = PromptList(prompts=[
        Prompt(prompt="A beautiful sunset over mountains", start_time=0.0, duration=3),
        Prompt(prompt="A flowing river through a forest", start_time=3.0, duration=4),
        Prompt(prompt="Birds flying in the sky", start_time=7.0, duration=2)
    ])
    
    for prompt in test_prompts.prompts:
        video_manager.db.add_prompt(
            video_id=video_id,
            prompt=prompt.prompt,
            start_time=prompt.start_time,
            duration=prompt.duration
        )
    terminal.print_status(f"Added {len(test_prompts.prompts)} prompts", "SUCCESS")
    
    # Test 3: Log some processing steps
    terminal.print_status("Test 3: Logging processing steps", "PROCESSING")
    steps = [
        ("audio_generation", "completed", "Audio generated successfully"),
        ("speaker_video", "completed", "Speaker video created"),
        ("subtitle_generation", "completed", "Subtitles generated"),
        ("prompt_generation", "completed", "AI prompts generated"),
        ("video_generation", "failed", "API rate limit exceeded")
    ]
    
    for step, status, message in steps:
        video_manager.db.log_processing_step(video_id, step, status, message)
    terminal.print_status("Logged processing steps", "SUCCESS")
    
    # Test 4: Update video status
    terminal.print_status("Test 4: Updating video status", "PROCESSING")
    video_manager.db.update_video_info(
        video_id=video_id,
        status="failed",
        metadata={"test": True, "error_reason": "API rate limit"}
    )
    terminal.print_status("Updated video status", "SUCCESS")
    
    # Test 5: Retrieve and display information
    terminal.print_status("Test 5: Retrieving video information", "PROCESSING")
    video_manager.print_video_info(video_id)
    
    # Test 6: Show database stats
    terminal.print_status("Test 6: Database statistics", "PROCESSING")
    video_manager.print_stats()
    
    # Test 7: Create another video for testing list functionality
    terminal.print_status("Test 7: Creating second video", "PROCESSING")
    video_id2 = video_manager.create_video_project(
        title="Another Test Video",
        script="This is another test script."
    )
    video_manager.db.update_video_info(video_id2, status="completed")
    terminal.print_status(f"Created second video with ID: {video_id2}", "SUCCESS")
    
    # Test 8: List videos
    terminal.print_status("Test 8: Listing videos", "PROCESSING")
    videos = video_manager.list_videos()
    print(f"\nFound {len(videos)} videos in database:")
    for video in videos:
        print(f"  ID {video.id}: {video.title} ({video.status})")
    
    terminal.print_separator("Database Tests Completed")
    terminal.print_status("All database functionality tests passed!", "SUCCESS")
    
    return video_id, video_id2

def test_cleanup(video_id1, video_id2):
    """Clean up test data."""
    terminal.print_status("Cleaning up test data", "PROCESSING")
    video_manager.delete_video(video_id1)
    video_manager.delete_video(video_id2)
    terminal.print_status("Test data cleaned up", "SUCCESS")

if __name__ == "__main__":
    try:
        video_id1, video_id2 = test_database_functionality()
        
        # Ask if user wants to keep test data
        keep_data = input("\nKeep test data in database? (y/n): ").strip().lower()
        if keep_data != 'y':
            test_cleanup(video_id1, video_id2)
    except Exception as e:
        terminal.print_status(f"Test failed: {e}", "ERROR")
        raise
