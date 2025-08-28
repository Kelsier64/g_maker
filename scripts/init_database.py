#!/usr/bin/env python3
"""
Simple script to initialize the SQLite database
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from g_maker.database import VideoDatabase

def main():
    print("Initializing G-Maker video database...")
    
    # Create database instance (this will initialize the database)
    db = VideoDatabase()
    
    print(f"Database initialized at: {db.db_path}")
    print("Database tables created successfully!")
    
    # Test basic functionality
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\nCreated tables:")
        for table in tables:
            print(f"  - {table[0]}")

if __name__ == "__main__":
    main()
