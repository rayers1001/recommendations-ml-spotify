import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from supabase import create_client
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

class SpotifyCollector:
    def __init__(self):
        """
        Initialize Spotify and Supabase clients
        """
        # Spotify setup with required scope
        scope = " ".join([
            "user-read-recently-played",
            "user-read-currently-playing",
            "user-top-read",
            "user-library-read",
            "user-read-private",
        ])
        
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                scope=scope,
                redirect_uri="http://127.0.0.1:8888/callback",
                open_browser=True
            )
        )
        
        # Supabase setup
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        self.supabase = create_client(supabase_url, supabase_key)

    def store_user(self):
        """Store current user in database"""
        user = self.sp.current_user()
        data = {
            'spotify_id': user['id'],
            'display_name': user['display_name']
        }
        
        # First try to get existing user
        result = self.supabase.table('users').select('id').eq('spotify_id', user['id']).execute()
        
        if result.data:
            # User exists, return their id
            return result.data[0]['id']
        else:
            # User doesn't exist, insert new
            result = self.supabase.table('users').insert(data).execute()
            return result.data[0]['id']

    def store_track(self, track_data):
        """Store track in database if not exists, return track_id"""
        # Check if track exists
        result = self.supabase.table('tracks').select('id').eq('spotify_id', track_data['track_id']).execute()
        
        if result.data:
            # Track exists, return existing id
            track_id = result.data[0]['id']
            print(f"Track already exists, using ID: {track_id}")
        else:
            # Track doesn't exist, insert new
            track = {
                'spotify_id': track_data['track_id'],
                'name': track_data['name'],
                'artist': track_data['artist'],
                'duration_ms': track_data['duration_ms']
            }
            result = self.supabase.table('tracks').insert(track).execute()
            track_id = result.data[0]['id']
            print(f"Created new track with ID: {track_id}")
        
        return track_id

    def update_play_count(self, user_id, track_id, played_at):
        """Update or create listening history with play count"""
        # First try to get existing record for this user and track
        result = self.supabase.table('listening_history')\
            .select('id, play_count')\
            .eq('user_id', user_id)\
            .eq('track_id', track_id)\
            .execute()
        
        if result.data:
            # Update existing record
            history_id = result.data[0]['id']
            play_count = result.data[0]['play_count'] + 1
            self.supabase.table('listening_history')\
                .update({'play_count': play_count, 'last_played_at': played_at})\
                .eq('id', history_id)\
                .execute()
            return f"Updated play count to {play_count}"
        else:
            # Create new record
            history_data = {
                'user_id': user_id,
                'track_id': track_id,
                'first_played_at': played_at,
                'last_played_at': played_at,
                'play_count': 1
            }
            self.supabase.table('listening_history').insert(history_data).execute()
            return "Created new listening record"

    def collect_and_process_data(self, limit=50):
        """
        Collect tracks and store in Supabase
        """
        print("Fetching user data...")
        user_id = self.store_user()

        print("\nFetching recent tracks...")
        results = self.sp.current_user_recently_played(limit=limit)
        tracks = results['items']
        print(f"Found {len(tracks)} tracks")

        # Process each track
        new_tracks = 0
        updated_tracks = 0
        
        for item in tracks:
            track = item['track']
            print(f"\nProcessing: {track['name']} by {track['artists'][0]['name']}")
            
            # Prepare track data
            track_data = {
                'track_id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'duration_ms': track['duration_ms']
            }
            
            try:
                track_id = self.store_track(track_data)
                result = self.update_play_count(user_id, track_id, item['played_at'])
                if "Updated" in result:
                    updated_tracks += 1
                else:
                    new_tracks += 1
            except Exception as e:
                print(f"Error processing track: {str(e)}")

        print(f"\nProcess complete!")
        print(f"New tracks: {new_tracks}")
        print(f"Updated tracks: {updated_tracks}")

if __name__ == "__main__":
    print("Initializing collector...")
    collector = SpotifyCollector()
    collector.collect_and_process_data() 