# Randy's AI Music Recommendations

An AI-powered music recommendation system that uses Spotify listening history and Last.fm metadata to create personalized playlists.

## Overview

This project collects your Spotify listening history, enriches it with metadata from Last.fm, and uses machine learning techniques to generate personalized music recommendations. These recommendations are automatically added to a Spotify playlist called "Randy's AI Recommendations".

## System Architecture

The system consists of four main components:

1. **Data Collection** (`spotify_collector.py`): Collects your Spotify listening history and stores it in a Supabase database.
2. **Metadata Enrichment** (`lastfm_collector.py`): Fetches additional metadata (tags, similar tracks) from Last.fm for each track.
3. **Recommendation Generation** (`recommendations_creator.py`): Analyzes your listening patterns and Last.fm metadata to generate personalized recommendations.
4. **Playlist Management** (`playlist_creator.py`): Creates and updates a Spotify playlist with your recommendations.

## Database Structure

The system uses a Supabase database with the following tables:

- **users**: Stores user information
  - `id`: Primary key
  - `spotify_id`: Spotify user ID
  - `display_name`: User's display name

- **tracks**: Stores track information
  - `id`: Primary key
  - `spotify_id`: Spotify track ID
  - `name`: Track name
  - `artist`: Artist name
  - `duration_ms`: Track duration in milliseconds

- **listening_history**: Records user listening history
  - `id`: Primary key
  - `user_id`: Reference to users table
  - `track_id`: Reference to tracks table
  - `play_count`: Number of times the track was played
  - `first_played_at`: First time the track was played
  - `last_played_at`: Last time the track was played

- **track_metadata**: Stores Last.fm metadata for tracks
  - `id`: Primary key
  - `track_id`: Reference to tracks table
  - `listeners`: Number of Last.fm listeners
  - `playcount`: Number of Last.fm plays
  - `tags`: Array of genre/style tags
  - `similar_tracks`: Array of similar track names
  - `wiki_summary`: Track description from Last.fm
  - `updated_at`: Last metadata update timestamp

- **recommendations**: Stores generated recommendations
  - `id`: Primary key
  - `user_id`: Reference to users table
  - `track_id`: Reference to tracks table
  - `added_at`: When the recommendation was generated
  - `rating`: Confidence score for the recommendation
  - `source`: Source of the recommendation
  - `is_played`: Whether the user has played the recommendation
  - `user_feedback`: User feedback on the recommendation

## Setup

### Prerequisites

- Python 3.6+
- Spotify Developer Account
- Last.fm API Key
- Supabase Account

### Environment Variables

Create a `.env` file with the following variables:

```
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
LASTFM_API_KEY=your_lastfm_api_key
```

### Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install spotipy python-dotenv supabase requests
   ```
3. Set up your Supabase database with the required tables

## Usage

### Running the Full Process

To run the entire recommendation process, use:

```
python run_recommendation_process.py
```

This will:
1. Collect your Spotify listening history
2. Fetch Last.fm metadata for your tracks
3. Generate personalized recommendations
4. Update your "Randy's AI Recommendations" playlist

### Running Individual Components

You can also run each component separately:

```
# Collect Spotify listening history
python spotify_collector.py

# Collect Last.fm metadata
python lastfm_collector.py

# Generate recommendations
python recommendations_creator.py

# Update playlist
python -c "from playlist_creator import PlaylistCreator; creator = PlaylistCreator(); creator.update_recommendation_playlist_with_lastfm()"
```

## How It Works

### Data Collection

The system collects your recently played tracks from Spotify and stores them in the database, tracking play counts and timestamps.

### Metadata Enrichment

For each track in your listening history, the system fetches additional metadata from Last.fm:
- Genre and style tags
- Similar tracks
- Listener counts and popularity
- Track descriptions

### Recommendation Generation

The recommendation engine uses several strategies:
1. **Tag-Based Recommendations**: Identifies your favorite music tags and finds tracks with similar tags
2. **Similar Track Recommendations**: Uses Last.fm's "similar tracks" data to find new music
3. **Top Tracks**: Falls back to your top tracks if other methods don't yield enough recommendations

### Playlist Management

The system creates and maintains a Spotify playlist called "Randy's AI Recommendations" with your personalized track selections.

## Future Enhancements

- Implement more sophisticated machine learning models
- Add user feedback mechanisms to improve recommendations
- Develop a web interface for configuration and analytics
- Support for multiple user accounts