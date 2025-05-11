import os
import base64
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from supabase import create_client
from PIL import Image
import io

# Load environment variables from .env file
load_dotenv()

class PlaylistCreator:
    def __init__(self):
        """Initialize Spotify client with required scopes"""
        # Spotify setup with required scope
        scope = " ".join([
            "user-read-recently-played",
            "user-library-read", 
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
        
        # Set the path to the cover image in the images directory
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.images_dir = os.path.join(self.project_dir, "images")
        self.cover_image_path = os.path.join(self.images_dir, "cover.jpg")
        
        # Verify the cover image exists
        if os.path.exists(self.cover_image_path):
            print(f"Found cover image at: {self.cover_image_path}")
        else:
            print(f"Warning: Cover image not found at {self.cover_image_path}")
            print(f"Expected path: {self.cover_image_path}")
        
    def create_or_update_playlist(self, name="Randy's AI Recommendations", description=None):
        """
        Create or update a playlist with tracks and custom cover image
        
        Parameters:
            name (str): Name of the playlist
            description (str): Description of the playlist
        """
        user_id = self.sp.current_user()['id']
        
        # Default description if none provided
        if description is None:
            description = "AI-powered music recommendations based on your listening history."
        
        # Check if playlist already exists
        playlist_id = None
        playlists = self.sp.user_playlists(user_id)
        for playlist in playlists['items']:
            if playlist['name'] == name:
                print(f"Found existing playlist: {playlist['name']}")
                playlist_id = playlist['id']
                
                # Update description if needed
                if playlist.get('description') != description:
                    self.sp.playlist_change_details(
                        playlist_id,
                        description=description
                    )
                break
        
        # Create new playlist if it doesn't exist
        if not playlist_id:
            print(f"Creating new playlist: {name}")
            playlist = self.sp.user_playlist_create(
                user=user_id,
                name=name,
                public=True,
                description=description,
                collaborative=False
            )
            playlist_id = playlist['id']
            
        # Add recent tracks to the playlist
        track_ids = self.get_recent_tracks(limit=20)
        if track_ids:
            self.sp.playlist_replace_items(playlist_id, track_ids)
            print(f"Added {len(track_ids)} tracks to playlist")
        else:
            print("No tracks to add to playlist")
        
        # Set the custom cover image (this must be done after playlist creation)
        self.set_cover_image(playlist_id)
        
        return playlist_id
        
    def set_cover_image(self, playlist_id):
        """
        Set a custom cover image optimized to fit under Spotify's 256KB limit
        """
        if not os.path.exists(self.cover_image_path):
            print(f"Warning: Cover image not found at {self.cover_image_path}")
            return False
        
        try:
            # Open the image
            img = Image.open(self.cover_image_path)
            original_size = img.size
            print(f"Original image: {original_size[0]}x{original_size[1]}")
            
            # Target a file size that will stay under 256KB after base64 encoding
            # Base64 increases size by ~33%, so aim for around 180KB
            target_size_kb = 180
            
            # First, just try reducing quality
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            buffer.seek(0)
            image_data = buffer.read()
            
            size_kb = len(image_data) / 1024
            print(f"First attempt: {size_kb:.1f}KB at 85% quality")
            
            # If still too large, resize the image
            if size_kb > target_size_kb:
                # Try 450x450px at 80% quality
                new_size = (450, 450)
                new_img = img.resize(new_size, Image.LANCZOS)
                
                buffer = io.BytesIO()
                new_img.save(buffer, format="JPEG", quality=80)
                buffer.seek(0)
                image_data = buffer.read()
                
                size_kb = len(image_data) / 1024
                print(f"Second attempt: {size_kb:.1f}KB at {new_size[0]}x{new_size[1]}, 80% quality")
                
                # If still too large, try 300x300 at 75% quality
                if size_kb > target_size_kb:
                    new_size = (300, 300)
                    new_img = img.resize(new_size, Image.LANCZOS)
                    
                    buffer = io.BytesIO()
                    new_img.save(buffer, format="JPEG", quality=75)
                    buffer.seek(0)
                    image_data = buffer.read()
                    
                    size_kb = len(image_data) / 1024
                    print(f"Third attempt: {size_kb:.1f}KB at {new_size[0]}x{new_size[1]}, 75% quality")
            
            # Convert to base64
            b64_image = base64.b64encode(image_data).decode('utf-8')
            b64_size_kb = len(b64_image) / 1024
            print(f"Final file size: {size_kb:.1f}KB")
            print(f"Base64 encoded size: {b64_size_kb:.1f}KB")
            
            # Double-check if we're still over the limit
            if b64_size_kb > 250:
                print(f"Warning: Base64 size still large at {b64_size_kb:.1f}KB")
                print("Creating a minimal image as last resort...")
                
                # Create a minimal image
                minimal_img = Image.new('RGB', (200, 200), color=(30, 30, 30))
                buffer = io.BytesIO()
                minimal_img.save(buffer, format="JPEG", quality=70)
                buffer.seek(0)
                image_data = buffer.read()
                b64_image = base64.b64encode(image_data).decode('utf-8')
                
                size_kb = len(image_data) / 1024
                b64_size_kb = len(b64_image) / 1024
                print(f"Minimal image: {size_kb:.1f}KB, Base64: {b64_size_kb:.1f}KB")
            
            # Get token
            token = self.sp.auth_manager.get_access_token(as_dict=False)
            
            # Set up the request
            url = f"https://api.spotify.com/v1/playlists/{playlist_id}/images"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'text/plain'
            }
            
            # Send the request
            import requests
            response = requests.put(url, headers=headers, data=b64_image)
            
            # Print detailed response
            print(f"Response status: {response.status_code}")
            if response.text:
                print(f"Response body: {response.text}")
            
            if response.status_code == 202:
                print("Successfully set custom cover image for playlist")
                return True
            else:
                print(f"Failed to set cover image: HTTP {response.status_code}")
                return False
            
        except Exception as e:
            print(f"Error setting cover image: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    def get_recent_tracks(self, limit=20):
        """
        Get the user's most recently played tracks
        """
        user_id = self.sp.current_user()['id']
        
        # Get user's database ID
        result = self.supabase.table('users').select('id').eq('spotify_id', user_id).execute()
        if not result.data:
            print("User not found in database")
            return []
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

if __name__ == "__main__":
    # Create the playlist creator
    creator = PlaylistCreator()
    
    # Create or update playlist with tracks and cover image in one step
    playlist_id = creator.create_or_update_playlist()
    
    print(f"Playlist ready! ID: {playlist_id}") 