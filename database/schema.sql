-- Users table to track individual users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    spotify_id TEXT UNIQUE NOT NULL,
    display_name TEXT
);

-- Tracks table to store song information
CREATE TABLE tracks (
    id SERIAL PRIMARY KEY,
    spotify_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    artist TEXT NOT NULL,
    duration_ms INTEGER
);

-- User listening history with play counts
CREATE TABLE listening_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    track_id INTEGER REFERENCES tracks(id),
    play_count INTEGER DEFAULT 1,
    first_played_at TIMESTAMP WITH TIME ZONE,
    last_played_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT listening_history_user_id_track_id_key UNIQUE (user_id, track_id)
);

-- Last.fm metadata for tracks
CREATE TABLE track_metadata (
    id SERIAL PRIMARY KEY,
    track_id INTEGER REFERENCES tracks(id),
    listeners INTEGER,
    playcount INTEGER,
    tags TEXT[],
    similar_tracks TEXT[],
    wiki_summary TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(track_id)
);

-- User feedback on recommendations
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    track_id INTEGER REFERENCES tracks(id),
    feedback_type TEXT CHECK (feedback_type IN ('skip', 'complete', 'like')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Recommendations table to store recommended tracks
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    track_id INT NOT NULL REFERENCES tracks(id),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rating FLOAT,  -- Optional: store the ML model's confidence score here
    source TEXT,   -- Optional: track where this recommendation came from
    is_played BOOLEAN DEFAULT FALSE,  -- Track if the user has played this recommendation
    user_feedback TEXT,  -- Optional: store user feedback (liked, skipped, etc.)
    UNIQUE(user_id, track_id)
);