import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from supabase import create_client
from datetime import datetime
import base64

# Load environment variables from .env file
load_dotenv()

class PlaylistCreator:
    def __init__(self):
        """
        Initialize Spotify and Supabase clients
        """
        # Spotify setup with required scope
        scope = " ".join([
            "user-read-recently-played",
            "user-library-read",
            "user-read-private",
            "playlist-modify-public",
            "playlist-modify-private",
            "ugc-image-upload"  # Required for image upload
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
        
        # Set project directory paths
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.images_dir = os.path.join(self.project_dir, "images")
        
        # Create images directory if it doesn't exist
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
            print(f"Created images directory at: {self.images_dir}")
        
    def get_or_create_playlist(self):
        """
        Get or create the "Randy's AI Recommendations" playlist
        """
        user_id = self.sp.current_user()['id']
        playlist_name = "Randy's AI Recommendations"
        
        # Check if playlist already exists
        playlists = self.sp.user_playlists(user_id)
        for playlist in playlists['items']:
            if playlist['name'] == playlist_name:
                print(f"Found existing playlist: {playlist['name']}")
                return playlist['id']
        
        # Create new playlist if it doesn't exist
        print(f"Creating new playlist: {playlist_name}")
        playlist = self.sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=True,
            description="AI-Powered recommendations based on your personallistening history."
        )
        return playlist['id']
    
    def get_recent_tracks(self, limit=20):
        """
        Get the user's most recently played tracks
        """
        user_id = self.sp.current_user()['id']
        
        # Get user's database ID
        result = self.supabase.table('users').select('id').eq('spotify_id', user_id).execute()
        if not result.data:
            raise Exception("User not found in database")
        db_user_id = result.data[0]['id']
        
        # Get most recent tracks from database
        result = self.supabase.table('listening_history')\
            .select('track_id, last_played_at')\
            .eq('user_id', db_user_id)\
            .order('last_played_at', desc=True)\
            .limit(limit)\
            .execute()
        
        if not result.data:
            print("No listening history found in database")
            return []
        
        track_db_ids = [item['track_id'] for item in result.data]
        
        # Get Spotify IDs for these tracks
        tracks = []
        for track_db_id in track_db_ids:
            result = self.supabase.table('tracks')\
                .select('spotify_id')\
                .eq('id', track_db_id)\
                .execute()
            
            if result.data:
                tracks.append(result.data[0]['spotify_id'])
        
        return tracks
    
    def update_recommendation_playlist(self, image_filename="cover.jpg"):
        """
        Update playlist and set a static cover image from the images directory
        
        Parameters:
            image_filename (str): Filename of the image in the images directory
        """
        # 1. Get or create the playlist
        playlist_id = self.get_or_create_playlist()
        
        # 2. Update the playlist tracks
        track_ids = self.get_recent_tracks(limit=20)
        if track_ids:
            self.sp.playlist_replace_items(playlist_id, track_ids)
            print(f"Added {len(track_ids)} tracks to playlist")
        else:
            print("No tracks to add to playlist")
        
        # 3. Set the static cover image from project files
        image_path = os.path.join(self.images_dir, image_filename)
        self.set_static_cover_image(playlist_id, image_path)
        
    def set_static_cover_image(self, playlist_id, image_path):
        """
        Set a static cover image for the playlist
        """
        # Check if image exists
        if not os.path.exists(image_path):
            print(f"Error: Image file not found at {image_path}")
            print(f"Please add an image file to: {self.images_dir}")
            return
            
        try:
            # Read and encode the image
            with open(image_path, "rb") as image_file:
                # Convert binary data to base64 string
                b64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Upload the image to Spotify
            self.sp.playlist_upload_cover_image(playlist_id, b64_image)
            print(f"Successfully set playlist cover image")
            
        except Exception as e:
            print(f"Error setting cover image: {str(e)}")

if __name__ == "__main__":
    print("Initializing playlist creator...")
    creator = PlaylistCreator()
    
    # Update playlist with the default image (cover.jpg)
    creator.update_recommendation_playlist()
    
    # Alternatively, specify a different image from your images directory:
    # creator.update_recommendation_playlist(image_filename="alternate_cover.jpg") 