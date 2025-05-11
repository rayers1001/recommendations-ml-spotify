# Randy's AI Music Recommendations

AI-powered music recommendation system for Spotify that creates personalized playlists based on listening history.

## Overview

This project creates a personalized Spotify playlist that updates with new music recommendations that match your listening habits. It collects your listening history, uses it to generate recommendations, and automatically creates a playlist in your Spotify account.

## Features

- Collects your Spotify listening history
- Generates recommendations using Spotify's API (will be replaced with ML model)
- Creates and maintains a "Randy's AI Recommendations" playlist in your Spotify account
- Updates recommendations periodically
- Custom playlist cover image

## System Components

1. **Data Collection** (`spotify_collector.py`)
   - Authenticates with Spotify API
   - Retrieves user's recently played tracks
   - Stores track info and listening history in database
   - Updates play counts for repeat listens

2. **Recommendation Engine** (`sample_recommendations.py`)
   - Generates track recommendations based on listening data
   - Uses Spotify's recommendation algorithm (temporary)
   - Will be replaced with custom ML model in the future

3. **Playlist Manager** (`playlist_creator.py`)
   - Creates/updates "Randy's AI Recommendations" playlist
   - Pulls recommended tracks from database
   - Sets custom playlist cover image

## Setup

### Prerequisites

- Python 3.7+
- Spotify account
- Spotify Developer account (for API access)
- Supabase account (for database)

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/rayers1001/recommendations-ml-spotify.git
   cd recommendations-ml-spotify
   ```

2. Install dependencies
   ```bash
   pip install spotipy python-dotenv supabase pillow
   ```

3. Set up Spotify API credentials
   - Create an app at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Set redirect URI to `http://127.0.0.1:8888/callback`
   - Note your Client ID and Client Secret

4. Set up Supabase
   - Create a new project at [Supabase](https://supabase.com/)
   - Run the database schema in `database/schema.sql`
   - Note your Supabase URL and API key

5. Create a `.env` file with your credentials
   ```
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_api_key
   ```

6. Add a custom image for the playlist
   - Place your image in the `images/` directory
   - Name it `cover.jpg`

### Usage

1. Collect listening data
   ```bash
   python spotify_collector.py
   ```

2. Generate recommendations
   ```bash
   python sample_recommendations.py
   ```

3. Create/update your playlist
   ```bash
   python playlist_creator.py
   ```

You can also add a track directly to recommendations:
```bash
python playlist_creator.py --add SPOTIFY_TRACK_ID
```

## Future Enhancements

- Custom machine learning model for recommendations
- User feedback collection (likes, skips)
- Automated scheduled updates
- Web interface for managing recommendations
- Mobile app integration

## Database Schema

The system uses the following database tables:

- `users`: Stores user information
- `tracks`: Stores track metadata
- `listening_history`: Records user listening activity with play counts
- `recommendations`: Stores recommended tracks for each user
- `user_feedback`: Stores user interaction with recommendations

## Contributing

Feel free to submit issues or pull requests to improve the project.

## License

[MIT License](LICENSE) 