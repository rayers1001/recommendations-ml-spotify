import os
import random
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from supabase import create_client
from datetime import datetime

# Load environment variables
load_dotenv()

class SampleRecommender:
    def __init__(self):
        """
        Initialize Spotify and Supabase clients
        """
        # Spotify setup with broader scopes
        scope = "user-read-recently-played user-top-read playlist-modify-public playlist-modify-private"
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

    def get_user_db_id(self):
        """Get the user's database ID from their Spotify ID"""
        user_id = self.sp.current_user()['id']
        result = self.supabase.table('users').select('id').eq('spotify_id', user_id).execute()
        if not result.data:
            print("User not found in database")
            return None
        return result.data[0]['id']
        
    def get_recommendations_direct(self, count=20):
        """Get recommendations directly from Spotify using genres"""
        try:
            # Get available genres as seeds
            genres = self.sp.recommendation_genre_seeds()
            seed_genres = random.sample(genres['genres'], 5)
            print(f"Using seed genres: {seed_genres}")
            
            # Get recommendations based on genres
            recommendations = self.sp.recommendations(
                seed_genres=seed_genres,
                limit=count
            )
            
            return recommendations['tracks']
        except Exception as e:
            print(f"Error getting genre recommendations: {str(e)}")
            return []
    
    def get_user_top_tracks(self, count=20):
        """Get user's top tracks as fallback"""
        try:
            print("Trying to get user's top tracks...")
            # Try different time ranges
            for time_range in ['short_term', 'medium_term', 'long_term']:
                top_tracks = self.sp.current_user_top_tracks(limit=count, time_range=time_range)
                if top_tracks and len(top_tracks['items']) > 0:
                    print(f"Found {len(top_tracks['items'])} top tracks from {time_range}")
                    return top_tracks['items']
            return []
        except Exception as e:
            print(f"Error getting top tracks: {str(e)}")
            return []
    
    def get_new_releases(self, count=20):
        """Get new releases as another fallback"""
        try:
            print("Fetching new releases...")
            new_releases = self.sp.new_releases(limit=count)
            if new_releases and 'albums' in new_releases:
                # Get a track from each album
                tracks = []
                for album in new_releases['albums']['items']:
                    album_tracks = self.sp.album_tracks(album['id'])
                    if album_tracks and 'items' in album_tracks and len(album_tracks['items']) > 0:
                        tracks.append(album_tracks['items'][0])
                        if len(tracks) >= count:
                            break
                return tracks
            return []
        except Exception as e:
            print(f"Error getting new releases: {str(e)}")
            return []
    
    def generate_recommendations(self, count=20):
        """Generate sample recommendations using various methods"""
        db_user_id = self.get_user_db_id()
        if not db_user_id:
            print("User not found in database")
            return False
        
        # Try multiple methods to get recommendations
        recommended_tracks = []
        
        # Method 1: Direct genre recommendations
        if not recommended_tracks:
            recommended_tracks = self.get_recommendations_direct(count)
        
        # Method 2: Top tracks
        if not recommended_tracks:
            recommended_tracks = self.get_user_top_tracks(count)
            
        # Method 3: New releases
        if not recommended_tracks:
            recommended_tracks = self.get_new_releases(count)
        
        if not recommended_tracks:
            print("Failed to get any recommendations")
            return False
            
        print(f"Successfully found {len(recommended_tracks)} tracks to recommend")
        
        # Store each recommended track
        success_count = 0
        for track in recommended_tracks:
            try:
                # Get track details if only partial info available
                if 'duration_ms' not in track:
                    track = self.sp.track(track['id'])
                
                # Prepare track data - NO popularity field
                track_data = {
                    'spotify_id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'duration_ms': track['duration_ms']
                }
                
                # Check if track exists
                result = self.supabase.table('tracks')\
                    .select('id')\
                    .eq('spotify_id', track['id'])\
                    .execute()
                
                if result.data:
                    track_id = result.data[0]['id'] 
                else:
                    # Add new track
                    result = self.supabase.table('tracks')\
                        .insert(track_data)\
                        .execute()
                    track_id = result.data[0]['id']
                
                # Add to recommendations table (if not already there)
                recommendation_data = {
                    'user_id': db_user_id,
                    'track_id': track_id,
                    'added_at': datetime.now().isoformat(),
                    'rating': random.uniform(0.6, 1.0),  # Simulate model confidence
                    'source': 'sample_recommender'
                }
                
                # Check if recommendation already exists
                result = self.supabase.table('recommendations')\
                    .select('id')\
                    .eq('user_id', db_user_id)\
                    .eq('track_id', track_id)\
                    .execute()
                    
                if not result.data:
                    # Only add if it doesn't exist
                    self.supabase.table('recommendations')\
                        .insert(recommendation_data)\
                        .execute()
                    print(f"Added recommendation: {track['name']} by {track['artists'][0]['name']}")
                    success_count += 1
                else:
                    print(f"Recommendation already exists: {track['name']}")
                    
            except Exception as e:
                print(f"Error adding track {track.get('name', 'unknown')}: {str(e)}")
                continue
                
        print(f"Successfully added {success_count} recommendations to database")
        return success_count > 0

if __name__ == "__main__":
    recommender = SampleRecommender()
    success = recommender.generate_recommendations()
    if success:
        print("Sample recommendations added to database")
    else:
        print("Failed to add recommendations") 