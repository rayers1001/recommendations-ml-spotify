#!/usr/bin/env python3
# run_endtoendprocess.py

import os
import subprocess
import time
from datetime import datetime

def run_command(command, description):
    """Run a command and print its output"""
    print(f"\n{'='*80}")
    print(f"STEP: {description}")
    print(f"COMMAND: {command}")
    print(f"TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'-'*80}\n")
    
    process = subprocess.run(command, shell=True, text=True)
    
    if process.returncode == 0:
        print(f"\nSUCCESS: {description} completed successfully")
    else:
        print(f"\nERROR: {description} failed with return code {process.returncode}")
    
    return process.returncode

def main():
    print(f"Starting recommendation process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Collect Spotify listening history
    run_command("python3 spotify_collector.py", "Collecting Spotify listening history")
    
    # Step 2: Collect metadata from Last.fm
    run_command("python3 lastfm_collector.py", "Collecting Last.fm metadata")
    
    # Step 3: Generate recommendations
    run_command("python3 recommendations_creator.py", "Generating recommendations")
    
    # Step 4: Update playlist
    run_command("python3 -c \"from playlist_creator import PlaylistCreator; creator = PlaylistCreator(); creator.update_recommendation_playlist_with_lastfm()\"", "Updating Spotify playlist")
    
    print(f"\nRecommendation process completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
