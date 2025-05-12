# lastfm_collector.py
import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='lastfm_collector.log'
)

# Load environment variables
load_dotenv()

class LastFmMetadataCollector:
    def __init__(self):
        # Last.fm API setup
        self.api_key = os.getenv('LASTFM_API_KEY')
        if not self.api_key:
            raise ValueError("LASTFM_API_KEY not found in environment variables")
            
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        
        # Supabase setup
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        self.supabase = create_client(supabase_url, supabase_key)
    
    def get_tracks_needing_metadata(self):
        """Get tracks that don't have metadata yet"""
        # Get all tracks
        all_tracks = self.supabase.table('tracks').select('id, name, artist').execute()
        
        # Get tracks that already have metadata
        metadata_tracks = self.supabase.table('track_metadata').select('track_id').execute()
        
        # Create a set of track_ids that already have metadata
        metadata_track_ids = set(item['track_id'] for item in metadata_tracks.data)
        
        # Filter tracks that don't have metadata
        tracks_needing_metadata = [
            track for track in all_tracks.data 
            if track['id'] not in metadata_track_ids
        ]
        
        # Limit to 50 tracks
        return tracks_needing_metadata[:50]
    
    def get_track_info(self, track_name, artist_name):
        """Get track info from Last.fm API"""
        params = {
            'method': 'track.getInfo',
            'api_key': self.api_key,
            'artist': artist_name,
            'track': track_name,
            'format': 'json',
            'autocorrect': 1
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error getting track info: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logging.error(f"Exception getting track info: {str(e)}")
            return None
    
    def get_track_similar(self, track_name, artist_name):
        """Get similar tracks from Last.fm API"""
        params = {
            'method': 'track.getSimilar',
            'api_key': self.api_key,
            'artist': artist_name,
            'track': track_name,
            'format': 'json',
            'limit': 10,
            'autocorrect': 1
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error getting similar tracks: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logging.error(f"Exception getting similar tracks: {str(e)}")
            return None
    
    def collect_track_metadata(self, tracks):
        """Collect metadata for tracks and store in database"""
        if not tracks:
            logging.info("No tracks need metadata")
            return 0
            
        logging.info(f"Collecting metadata for {len(tracks)} tracks")
        
        success_count = 0
        for track in tracks:
            try:
                db_track_id = track['id']
                track_name = track['name']
                artist_name = track['artist']
                
                logging.info(f"Processing track: {track_name} by {artist_name}")
                
                # Get track info from Last.fm
                track_info = self.get_track_info(track_name, artist_name)
                if not track_info or 'track' not in track_info:
                    logging.warning(f"No info found for {track_name} by {artist_name}")
                    continue
                
                # Get similar tracks
                similar_tracks = self.get_track_similar(track_name, artist_name)
                
                # Extract metadata
                track_data = track_info['track']
                
                # Extract tags
                tags = []
                if 'toptags' in track_data and 'tag' in track_data['toptags']:
                    tags = [tag['name'] for tag in track_data['toptags']['tag']]
                
                # Extract similar tracks
                similar = []
                if similar_tracks and 'similartracks' in similar_tracks and 'track' in similar_tracks['similartracks']:
                    similar = [f"{t['name']} by {t['artist']['name']}" for t in similar_tracks['similartracks']['track']]
                
                # Extract wiki summary if available
                wiki_summary = ""
                if 'wiki' in track_data and 'summary' in track_data['wiki']:
                    wiki_summary = track_data['wiki']['summary']
                    # Remove HTML tags if present
                    wiki_summary = wiki_summary.split('<a href')[0].strip()
                
                # Prepare metadata
                metadata = {
                    'track_id': db_track_id,
                    'listeners': int(track_data.get('listeners', 0)),
                    'playcount': int(track_data.get('playcount', 0)),
                    'tags': tags,
                    'similar_tracks': similar,
                    'wiki_summary': wiki_summary,
                    'updated_at': datetime.now().isoformat()
                }
                
                # Store in database
                self.supabase.table('track_metadata').insert(metadata).execute()
                
                logging.info(f"Stored metadata for {track_name} by {artist_name}")
                success_count += 1
                
                # Respect API rate limits
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Error collecting metadata for {track.get('name')}: {str(e)}")
                
        return success_count
    
    def run(self):
        """Run the metadata collection process"""
        logging.info("Starting metadata collection")
        
        tracks = self.get_tracks_needing_metadata()
        logging.info(f"Found {len(tracks)} tracks needing metadata")
        success_count = self.collect_track_metadata(tracks)
        
        logging.info(f"Completed metadata collection. Processed {success_count} tracks.")
        return success_count

if __name__ == "__main__":
    try:
        collector = LastFmMetadataCollector()
        collector.run()
    except Exception as e:
        print(f"Error: {str(e)}")