#!/usr/bin/env python3
"""
G-Maker Video Database Manager
Command-line utility for managing video database
"""

import argparse
import sys
import os
from typing import Optional

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from g_maker.video_manager import video_manager
from g_maker.utils import terminal

def list_videos(status: Optional[str] = None, limit: Optional[int] = None):
    """List videos in the database."""
    videos = video_manager.list_videos(status=status, limit=limit)
    
    if not videos:
        terminal.print_status("No videos found", "INFO")
        return
    
    print(f"\n{'ID':<5} {'Status':<12} {'Title':<40} {'Duration':<10} {'Size':<10} {'Created':<20}")
    print("-" * 100)
    
    for video in videos:
        duration_str = f"{video.duration:.1f}s" if video.duration else "N/A"
        size_str = f"{video.file_size/(1024*1024):.1f}MB" if video.file_size else "N/A"
        created_str = video.created_at.strftime("%Y-%m-%d %H:%M") if video.created_at else "N/A"
        
        print(f"{video.id:<5} {video.status:<12} {video.title[:38]:<40} {duration_str:<10} {size_str:<10} {created_str:<20}")

def show_video_details(video_id: int):
    """Show detailed information about a video."""
    video_manager.print_video_info(video_id)

def show_stats():
    """Show database statistics."""
    video_manager.print_stats()

def delete_video(video_id: int, force: bool = False):
    """Delete a video from the database."""
    video = video_manager.get_video(video_id)
    if not video:
        terminal.print_status(f"Video with ID {video_id} not found", "ERROR")
        return
    
    if not force:
        print(f"\nVideo to delete:")
        print(f"  ID: {video.id}")
        print(f"  Title: {video.title}")
        print(f"  Status: {video.status}")
        print(f"  File: {video.file_path}")
        
        confirm = input("\nAre you sure you want to delete this video? (yes/no): ").strip().lower()
        if confirm != "yes":
            terminal.print_status("Deletion cancelled", "INFO")
            return
    
    if video_manager.delete_video(video_id):
        terminal.print_status(f"Video '{video.title}' deleted successfully", "SUCCESS")
    else:
        terminal.print_status("Failed to delete video", "ERROR")

def cleanup_failed():
    """Remove all failed video records."""
    failed_videos = video_manager.list_videos(status="failed")
    
    if not failed_videos:
        terminal.print_status("No failed videos found", "INFO")
        return
    
    print(f"\nFound {len(failed_videos)} failed videos:")
    for video in failed_videos:
        print(f"  ID {video.id}: {video.title}")
    
    confirm = input(f"\nDelete all {len(failed_videos)} failed videos? (yes/no): ").strip().lower()
    if confirm != "yes":
        terminal.print_status("Cleanup cancelled", "INFO")
        return
    
    deleted_count = 0
    for video in failed_videos:
        if video_manager.delete_video(video.id):
            deleted_count += 1
    
    terminal.print_status(f"Deleted {deleted_count} failed videos", "SUCCESS")

def export_database(output_file: str):
    """Export database to JSON."""
    import json
    from datetime import datetime
    
    videos = video_manager.list_videos()
    
    export_data = {
        "export_date": datetime.now().isoformat(),
        "total_videos": len(videos),
        "videos": []
    }
    
    for video in videos:
        video_data = video.model_dump()
        # Get prompts and logs
        prompts = video_manager.get_video_prompts(video.id)
        logs = video_manager.get_processing_logs(video.id)
        
        video_data["prompts"] = [p.model_dump() for p in prompts]
        video_data["processing_logs"] = [l.model_dump() for l in logs]
        
        export_data["videos"].append(video_data)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    terminal.print_status(f"Database exported to {output_file}", "SUCCESS")

def main():
    parser = argparse.ArgumentParser(description="G-Maker Video Database Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List videos")
    list_parser.add_argument("--status", choices=["created", "processing", "completed", "failed"], 
                           help="Filter by status")
    list_parser.add_argument("--limit", type=int, help="Maximum number of videos to show")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show video details")
    show_parser.add_argument("video_id", type=int, help="Video ID")
    
    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a video")
    delete_parser.add_argument("video_id", type=int, help="Video ID to delete")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    
    # Cleanup command
    subparsers.add_parser("cleanup", help="Remove all failed videos")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export database to JSON")
    export_parser.add_argument("output_file", help="Output JSON file path")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_videos(status=args.status, limit=args.limit)
    elif args.command == "show":
        show_video_details(args.video_id)
    elif args.command == "stats":
        show_stats()
    elif args.command == "delete":
        delete_video(args.video_id, force=args.force)
    elif args.command == "cleanup":
        cleanup_failed()
    elif args.command == "export":
        export_database(args.output_file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
