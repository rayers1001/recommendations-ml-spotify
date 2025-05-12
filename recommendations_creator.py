import os
import random
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from supabase import create_client
from datetime import datetime

# Load environment variables
load_dotenv()

class LastFmRecommender:
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
    
    def get_tag_based_recommendations(self, count=20):
        """Get recommendations based on Last.fm tags"""
        print("Getting tag-based recommendations...")
        user_id = self.get_user_db_id()
        if not user_id:
            return []
        
        # Get user's top tracks from listening history
        top_tracks_query = self.supabase.table('listening_history')\
            .select('track_id, play_count')\
            .eq('user_id', user_id)\
            .order('play_count', desc=True)\
            .limit(10)\
            .execute()
        
        if not top_tracks_query.data:
            print("No listening history found")
            return []
        
        top_track_ids = [item['track_id'] for item in top_tracks_query.data]
        
        # Get metadata for these tracks
        metadata_query = self.supabase.table('track_metadata')\
            .select('track_id, tags')\
            .in_('track_id', top_track_ids)\
            .execute()
        
        # Extract all tags and count them
        all_tags = []
        for item in metadata_query.data:
            if item['tags']:
                all_tags.extend(item['tags'])
        
        # Count tag occurrences
        tag_counts = {}
        for tag in all_tags:
            if tag not in tag_counts:
                tag_counts[tag] = 0
            tag_counts[tag] += 1
        
        # Get top tags
        favorite_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        favorite_tag_names = [tag for tag, count in favorite_tags]
        
        if not favorite_tag_names:
            print("No tags found for your top tracks")
            return []
        
        print(f"Your favorite tags: {favorite_tag_names}")
        
        # Get all tracks with metadata
        all_metadata = self.supabase.table('track_metadata')\
            .select('track_id, tags')\
            .execute()
        
        # Filter tracks that match favorite tags and aren't in top_track_ids
        matching_track_ids = []
        for item in all_metadata.data:
            if item['track_id'] in top_track_ids:
                continue
                
            if not item['tags']:
                continue
                
            # Count how many favorite tags match
            matches = sum(1 for tag in item['tags'] if tag in favorite_tag_names)
            if matches > 0:
                matching_track_ids.append((item['track_id'], matches))
        
        # Sort by number of matching tags
        matching_track_ids.sort(key=lambda x: x[1], reverse=True)
        matching_track_ids = matching_track_ids[:count]
        
        if not matching_track_ids:
            print("No tag-based recommendations found")
            return []
        
        # Get track details
        recommendations = []
        for track_id, _ in matching_track_ids:
            track_query = self.supabase.table('tracks')\
                .select('spotify_id, name, artist')\
                .eq('id', track_id)\
                .execute()
            
            if track_query.data:
                try:
                    track = self.sp.track(track_query.data[0]['spotify_id'])
                    recommendations.append(track)
                    print(f"Added tag-based recommendation: {track['name']} by {track['artists'][0]['name']}")
                except Exception as e:
                    print(f"Error getting track {track_query.data[0]['spotify_id']}: {str(e)}")
        
        print(f"Found {len(recommendations)} tag-based recommendations")
        return recommendations
    
    def get_similar_track_recommendations(self, count=20):
        """Get recommendations based on Last.fm's similar tracks"""
        print("Getting similar track recommendations...")
        user_id = self.get_user_db_id()
        if not user_id:
            return []
        
        # Get user's recent tracks
        recent_tracks_query = self.supabase.table('listening_history')\
            .select('track_id')\
            .eq('user_id', user_id)\
            .order('last_played_at', desc=True)\
            .limit(5)\
            .execute()
        
        if not recent_tracks_query.data:
            print("No recent listening history found")
            return []
        
        recent_track_ids = [item['track_id'] for item in recent_tracks_query.data]
        
        # Get metadata for these tracks
        metadata_query = self.supabase.table('track_metadata')\
            .select('track_id, similar_tracks')\
            .in_('track_id', recent_track_ids)\
            .execute()
        
        # Collect all similar tracks
        similar_tracks = []
        for item in metadata_query.data:
            if item['similar_tracks']:
                similar_tracks.extend(item['similar_tracks'])
        
        if not similar_tracks:
            print("No similar tracks found")
            return []
        
        # Get most frequently occurring similar tracks
        similar_track_counts = {}
        for track in similar_tracks:
            if track not in similar_track_counts:
                similar_track_counts[track] = 0
            similar_track_counts[track] += 1
        
        # Sort by frequency
        sorted_similar_tracks = sorted(
            similar_track_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:count]
        
        # Search Spotify for these tracks
        recommendations = []
        for track_info, _ in sorted_similar_tracks:
            try:
                # Parse "Track Name by Artist Name" format
                parts = track_info.split(' by ')
                if len(parts) == 2:
                    track_name, artist_name = parts
                    
                    # Search Spotify for this track
                    search_results = self.sp.search(
                        q=f'track:"{track_name}" artist:"{artist_name}"', 
                        type='track', 
                        limit=1
                    )
                    
                    if search_results['tracks']['items']:
                        track = search_results['tracks']['items'][0]
                        recommendations.append(track)
                        print(f"Added similar track: {track['name']} by {track['artists'][0]['name']}")
                        
                        # Store this track in our database for future use
                        self.store_track(track)
            except Exception as e:
                print(f"Error processing similar track {track_info}: {str(e)}")
        
        print(f"Found {len(recommendations)} similar track recommendations")
        return recommendations
    
    def store_track(self, track):
        """Store a track in the database if it doesn't exist"""
        try:
            # Check if track exists
            result = self.supabase.table('tracks')\
                .select('id')\
                .eq('spotify_id', track['id'])\
                .execute()
            
            if result.data:
                return result.data[0]['id']
            
            # Add new track
            track_data = {
                'spotify_id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'duration_ms': track['duration_ms']
            }
            
            result = self.supabase.table('tracks')\
                .insert(track_data)\
                .execute()
                
            return result.data[0]['id']
        except Exception as e:
            print(f"Error storing track: {str(e)}")
            return None
    
    def get_top_tracks(self, count=20):
        """Get user's top tracks from Spotify"""
        print("Getting top tracks from Spotify...")
        try:
            # Try different time ranges
            for time_range in ['short_term', 'medium_term', 'long_term']:
                top_tracks = self.sp.current_user_top_tracks(limit=count, time_range=time_range)
                if top_tracks and 'items' in top_tracks and len(top_tracks['items']) > 0:
                    print(f"Found {len(top_tracks['items'])} top tracks from {time_range}")
                    return top_tracks['items']
            return []
        except Exception as e:
            print(f"Error getting top tracks: {str(e)}")
            return []
    
    def generate_recommendations(self, count=20):
        """Generate recommendations using Last.fm metadata"""
        db_user_id = self.get_user_db_id()
        if not db_user_id:
            print("User not found in database")
            return False
        
        # Try multiple methods to get recommendations
        recommended_tracks = []
        
        # Method 1: Tag-based recommendations
        if len(recommended_tracks) < count:
            tag_recommendations = self.get_tag_based_recommendations(count - len(recommended_tracks))
            recommended_tracks.extend(tag_recommendations)
        
        # Method 2: Similar track recommendations
        if len(recommended_tracks) < count:
            similar_recommendations = self.get_similar_track_recommendations(count - len(recommended_tracks))
            recommended_tracks.extend(similar_recommendations)
        
        # Method 3: Top tracks (fallback)
        if len(recommended_tracks) < count:
            top_tracks = self.get_top_tracks(count - len(recommended_tracks))
            recommended_tracks.extend(top_tracks)
        
        if not recommended_tracks:
            print("Failed to get any recommendations")
            return False
            
        print(f"Successfully found {len(recommended_tracks)} tracks to recommend")
        
        # Store each recommended track in recommendations table
        success_count = 0
        for track in recommended_tracks:
            try:
                # Get track details if only partial info available
                if 'duration_ms' not in track:
                    track = self.sp.track(track['id'])
                
                # Store track in database
                track_id = self.store_track(track)
                if not track_id:
                    continue
                
                # Add to recommendations table (if not already there)
                recommendation_data = {
                    'user_id': db_user_id,
                    'track_id': track_id,
                    'added_at': datetime.now().isoformat(),
                    'rating': random.uniform(0.6, 1.0),  # Simulate model confidence
                    'source': 'lastfm_recommender'
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
    
    def update_playlist(self, playlist_name="Randy's AI Recommendations", count=30):
        """Update a Spotify playlist with recommendations"""
        print(f"Updating playlist: {playlist_name}")
        
        # Get user ID
        user_id = self.sp.current_user()['id']
        
        # Find existing playlist or create new one
        playlists = self.sp.user_playlists(user_id)
        playlist_id = None
        
        for playlist in playlists['items']:
            if playlist['name'] == playlist_name:
                playlist_id = playlist['id']
                print(f"Found existing playlist: {playlist_name}")
                break
        
        if not playlist_id:
            print(f"Creating new playlist: {playlist_name}")
            playlist = self.sp.user_playlist_create(
                user=user_id,
                name=playlist_name,
                public=True,
                description="AI-powered music recommendations based on your listening history and Last.fm data."
            )
            playlist_id = playlist['id']
        
        # Get recommendations from database
        db_user_id = self.get_user_db_id()
        if not db_user_id:
            print("User not found in database")
            return False
            
        recommendations_query = self.supabase.table('recommendations')\
            .select('track_id')\
            .eq('user_id', db_user_id)\
            .order('added_at', desc=True)\
            .limit(count)\
            .execute()
            
        if not recommendations_query.data:
            print("No recommendations found in database")
            return False
            
        track_ids = [item['track_id'] for item in recommendations_query.data]
        
        # Get Spotify IDs for these tracks
        spotify_ids = []
        for track_id in track_ids:
            track_query = self.supabase.table('tracks')\
                .select('spotify_id')\
                .eq('id', track_id)\
                .execute()
                
            if track_query.data:
                spotify_ids.append(track_query.data[0]['spotify_id'])
        
        if not spotify_ids:
            print("No Spotify IDs found for recommendations")
            return False
            
        # Create track URIs
        track_uris = [f"spotify:track:{id}" for id in spotify_ids]
        
        # Replace playlist tracks
        self.sp.playlist_replace_items(playlist_id, track_uris)
        print(f"Updated playlist with {len(track_uris)} tracks")
        
        return True

if __name__ == "__main__":
    recommender = LastFmRecommender()
    
    # Generate new recommendations
    print("Generating recommendations...")
    recommender.generate_recommendations(count=30)
    
    # Update the playlist
    print("\nUpdating playlist...")
    recommender.update_playlist()
