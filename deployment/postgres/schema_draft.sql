-- deployment/postgres/schema_draft.sql
CREATE TABLE IF NOT EXISTS media_items (
    media_item_id BIGSERIAL PRIMARY KEY,
    media_type TEXT NOT NULL CHECK (media_type IN ('show','season','episode','movie')),
    tmdb_id BIGINT,
    parent_tmdb_id BIGINT,
    season_number INTEGER,
    episode_number INTEGER,
    title TEXT NOT NULL,
    subtitle TEXT,
    release_date DATE,
    runtime_minutes INTEGER,
    source_json_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watch_state (
    watch_state_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT NOT NULL REFERENCES media_items(media_item_id) ON DELETE CASCADE,
    watch_status TEXT NOT NULL CHECK (watch_status IN ('unwatched','partial','watched')),
    in_watchlist BOOLEAN NOT NULL DEFAULT FALSE,
    is_favourite BOOLEAN NOT NULL DEFAULT FALSE,
    last_watched_at TIMESTAMPTZ,
    source TEXT NOT NULL DEFAULT 'local',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(media_item_id)
);

CREATE TABLE IF NOT EXISTS sync_queue (
    sync_queue_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT REFERENCES media_items(media_item_id) ON DELETE SET NULL,
    sync_target TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS media_files (
    media_file_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT REFERENCES media_items(media_item_id) ON DELETE SET NULL,
    location_profile TEXT NOT NULL,
    device_name TEXT,
    file_path TEXT NOT NULL,
    expected_filename TEXT,
    actual_filename TEXT,
    file_status TEXT NOT NULL DEFAULT 'unknown',
    ffprobe_status TEXT,
    duration_seconds NUMERIC,
    video_codec TEXT,
    audio_codec TEXT,
    container_format TEXT,
    repair_status TEXT,
    qa_json JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
