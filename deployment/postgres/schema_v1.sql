-- deployment/postgres/schema_v1.sql
-- Server-mode PostgreSQL schema for my_TV_Movie.
-- PostgreSQL is the primary writable store. JSON remains import/export/static fallback.
-- Image and media binaries remain files under assets/media paths by default; this schema stores metadata and paths only.

BEGIN;

CREATE TABLE IF NOT EXISTS media_items (
    media_item_id BIGSERIAL PRIMARY KEY,
    media_type TEXT NOT NULL CHECK (media_type IN ('show', 'season', 'episode', 'movie')),
    canonical_title TEXT NOT NULL,
    sort_title TEXT,
    parent_media_item_id BIGINT REFERENCES media_items(media_item_id) ON DELETE SET NULL,
    tmdb_id BIGINT,
    imdb_id TEXT,
    tvdb_id BIGINT,
    trakt_id BIGINT,
    trakt_slug TEXT,
    original_language TEXT,
    release_date DATE,
    runtime_minutes INTEGER CHECK (runtime_minutes IS NULL OR runtime_minutes >= 0),
    overview TEXT,
    poster_path TEXT,
    backdrop_path TEXT,
    still_path TEXT,
    asset_root TEXT NOT NULL DEFAULT 'assets',
    source_json_path TEXT,
    source_json_key TEXT,
    source_hash TEXT,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_media_items_type_tmdb
    ON media_items(media_type, tmdb_id)
    WHERE tmdb_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_media_items_parent
    ON media_items(parent_media_item_id);

CREATE INDEX IF NOT EXISTS ix_media_items_title
    ON media_items USING gin(to_tsvector('simple', canonical_title));

CREATE TABLE IF NOT EXISTS shows (
    show_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT NOT NULL UNIQUE REFERENCES media_items(media_item_id) ON DELETE CASCADE,
    tmdb_show_id BIGINT,
    first_air_date DATE,
    last_air_date DATE,
    status TEXT,
    network_name TEXT,
    origin_country TEXT,
    season_count INTEGER CHECK (season_count IS NULL OR season_count >= 0),
    episode_count INTEGER CHECK (episode_count IS NULL OR episode_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seasons (
    season_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT NOT NULL UNIQUE REFERENCES media_items(media_item_id) ON DELETE CASCADE,
    show_id BIGINT NOT NULL REFERENCES shows(show_id) ON DELETE CASCADE,
    season_number INTEGER NOT NULL CHECK (season_number >= 0),
    tmdb_season_id BIGINT,
    title TEXT,
    air_date DATE,
    episode_count INTEGER CHECK (episode_count IS NULL OR episode_count >= 0),
    poster_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(show_id, season_number)
);

CREATE TABLE IF NOT EXISTS episodes (
    episode_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT NOT NULL UNIQUE REFERENCES media_items(media_item_id) ON DELETE CASCADE,
    show_id BIGINT NOT NULL REFERENCES shows(show_id) ON DELETE CASCADE,
    season_id BIGINT NOT NULL REFERENCES seasons(season_id) ON DELETE CASCADE,
    season_number INTEGER NOT NULL CHECK (season_number >= 0),
    episode_number INTEGER NOT NULL CHECK (episode_number >= 0),
    tmdb_episode_id BIGINT,
    title TEXT NOT NULL,
    air_date DATE,
    runtime_minutes INTEGER CHECK (runtime_minutes IS NULL OR runtime_minutes >= 0),
    still_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(show_id, season_number, episode_number)
);

CREATE TABLE IF NOT EXISTS movies (
    movie_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT NOT NULL UNIQUE REFERENCES media_items(media_item_id) ON DELETE CASCADE,
    tmdb_movie_id BIGINT,
    title TEXT NOT NULL,
    release_date DATE,
    runtime_minutes INTEGER CHECK (runtime_minutes IS NULL OR runtime_minutes >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watch_state (
    watch_state_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT NOT NULL UNIQUE REFERENCES media_items(media_item_id) ON DELETE CASCADE,
    watched_status TEXT NOT NULL DEFAULT 'unwatched'
        CHECK (watched_status IN ('unwatched', 'partial', 'watched')),
    progress_percent NUMERIC(5,2) NOT NULL DEFAULT 0
        CHECK (progress_percent >= 0 AND progress_percent <= 100),
    progress_seconds INTEGER CHECK (progress_seconds IS NULL OR progress_seconds >= 0),
    last_watched_at TIMESTAMPTZ,
    play_count INTEGER NOT NULL DEFAULT 0 CHECK (play_count >= 0),
    state_source TEXT NOT NULL DEFAULT 'local'
        CHECK (state_source IN ('local', 'json_import', 'trakt', 'api_import', 'manual_reconcile')),
    state_version BIGINT NOT NULL DEFAULT 1 CHECK (state_version >= 1),
    pending_sync BOOLEAN NOT NULL DEFAULT FALSE,
    last_synced_at TIMESTAMPTZ,
    conflict_status TEXT NOT NULL DEFAULT 'none'
        CHECK (conflict_status IN ('none', 'local_newer', 'remote_newer', 'conflict', 'resolved')),
    conflict_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watchlist (
    watchlist_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT NOT NULL UNIQUE REFERENCES media_items(media_item_id) ON DELETE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    list_source TEXT NOT NULL DEFAULT 'local'
        CHECK (list_source IN ('local', 'json_import', 'trakt', 'api_import', 'manual_reconcile')),
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    removed_at TIMESTAMPTZ,
    pending_sync BOOLEAN NOT NULL DEFAULT FALSE,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS favourites (
    favourite_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT NOT NULL UNIQUE REFERENCES media_items(media_item_id) ON DELETE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    favourite_source TEXT NOT NULL DEFAULT 'local'
        CHECK (favourite_source IN ('local', 'json_import', 'api_import', 'manual_reconcile')),
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    removed_at TIMESTAMPTZ,
    pending_sync BOOLEAN NOT NULL DEFAULT FALSE,
    local_only_reason TEXT NOT NULL DEFAULT 'favourite has no default Trakt mapping',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sync_queue (
    sync_queue_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT REFERENCES media_items(media_item_id) ON DELETE SET NULL,
    provider_key TEXT NOT NULL DEFAULT 'trakt',
    operation_type TEXT NOT NULL CHECK (
        operation_type IN (
            'watch_state_set',
            'watchlist_add',
            'watchlist_remove',
            'favourite_set',
            'trakt_pull',
            'trakt_push',
            'trakt_reconcile',
            'providers_refresh',
            'media_inventory_scan',
            'media_file_qa',
            'media_file_remux'
        )
    ),
    operation_key TEXT,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'blocked', 'cancelled')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 5 CHECK (max_attempts >= 1),
    priority INTEGER NOT NULL DEFAULT 100,
    not_before TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_sync_queue_status_priority
    ON sync_queue(status, priority, created_at);

CREATE TABLE IF NOT EXISTS sync_history (
    sync_history_id BIGSERIAL PRIMARY KEY,
    sync_queue_id BIGINT REFERENCES sync_queue(sync_queue_id) ON DELETE SET NULL,
    provider_key TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('pull', 'push', 'reconcile', 'local_only')),
    operation_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed', 'partial', 'blocked')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    records_read INTEGER NOT NULL DEFAULT 0 CHECK (records_read >= 0),
    records_written INTEGER NOT NULL DEFAULT 0 CHECK (records_written >= 0),
    conflicts_found INTEGER NOT NULL DEFAULT 0 CHECK (conflicts_found >= 0),
    conflicts_resolved INTEGER NOT NULL DEFAULT 0 CHECK (conflicts_resolved >= 0),
    request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS media_files (
    media_file_id BIGSERIAL PRIMARY KEY,
    media_item_id BIGINT REFERENCES media_items(media_item_id) ON DELETE SET NULL,
    location_profile TEXT NOT NULL CHECK (location_profile IN ('home', 'trailer', 'portable', 'unknown')),
    network_cidr TEXT,
    device_name TEXT,
    device_address INET,
    share_name TEXT,
    file_path TEXT NOT NULL,
    expected_filename TEXT,
    actual_filename TEXT,
    file_size_bytes BIGINT CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),
    file_status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (file_status IN ('unknown', 'matched', 'missing', 'extra', 'duplicate', 'quarantined', 'unsupported', 'needs_review')),
    qa_status TEXT NOT NULL DEFAULT 'not_checked'
        CHECK (qa_status IN ('not_checked', 'ok', 'repaired', 'needs_review', 'quarantined', 'duplicate', 'unsupported')),
    ffprobe_status TEXT NOT NULL DEFAULT 'not_checked'
        CHECK (ffprobe_status IN ('not_checked', 'ok', 'error', 'duration_mismatch', 'stream_missing', 'container_mismatch')),
    remux_status TEXT NOT NULL DEFAULT 'not_attempted'
        CHECK (remux_status IN ('not_attempted', 'not_needed', 'queued', 'succeeded', 'failed', 'unsafe')),
    vlc_status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (vlc_status IN ('unknown', 'playable', 'not_playable', 'not_tested')),
    xplore_status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (xplore_status IN ('unknown', 'playable', 'not_playable', 'not_tested')),
    duration_seconds NUMERIC(12,3) CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    video_codec TEXT,
    audio_codec TEXT,
    container_format TEXT,
    artwork_path TEXT,
    qa_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(location_profile, file_path)
);

CREATE INDEX IF NOT EXISTS ix_media_files_item
    ON media_files(media_item_id);

CREATE INDEX IF NOT EXISTS ix_media_files_qa
    ON media_files(qa_status, ffprobe_status, remux_status);

CREATE TABLE IF NOT EXISTS provider_registry (
    provider_registry_id BIGSERIAL PRIMARY KEY,
    provider_key TEXT NOT NULL UNIQUE,
    provider_name TEXT NOT NULL,
    provider_type TEXT NOT NULL
        CHECK (provider_type IN ('streaming_embed', 'commercial_watch', 'metadata', 'trakt', 'local_device', 'media_tool')),
    provider_status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (provider_status IN ('active', 'degraded', 'candidate', 'blocked', 'retired')),
    country_code TEXT,
    template_url TEXT,
    base_url TEXT,
    logo_path TEXT,
    public_label TEXT,
    private_notes TEXT,
    health_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runtime_config (
    runtime_config_id BIGSERIAL PRIMARY KEY,
    config_scope TEXT NOT NULL DEFAULT 'global'
        CHECK (config_scope IN ('global', 'home', 'trailer', 'api', 'media_library', 'sync')),
    config_key TEXT NOT NULL,
    config_value JSONB NOT NULL,
    secret_ref TEXT,
    is_secret BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(config_scope, config_key),
    CHECK ((is_secret = FALSE AND secret_ref IS NULL) OR (is_secret = TRUE AND secret_ref IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_log_id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_type TEXT NOT NULL DEFAULT 'system'
        CHECK (actor_type IN ('user', 'system', 'sync_job', 'migration', 'api')),
    actor_id TEXT,
    request_id TEXT,
    event_type TEXT NOT NULL,
    entity_table TEXT NOT NULL,
    entity_id BIGINT,
    media_item_id BIGINT REFERENCES media_items(media_item_id) ON DELETE SET NULL,
    before_json JSONB,
    after_json JSONB,
    outcome TEXT NOT NULL DEFAULT 'succeeded'
        CHECK (outcome IN ('succeeded', 'failed', 'blocked')),
    error_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_log_event_time
    ON audit_log(event_time DESC);

CREATE INDEX IF NOT EXISTS ix_audit_log_entity
    ON audit_log(entity_table, entity_id);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    target_table TEXT;
BEGIN
    FOREACH target_table IN ARRAY ARRAY[
        'media_items',
        'shows',
        'seasons',
        'episodes',
        'movies',
        'watch_state',
        'watchlist',
        'favourites',
        'sync_queue',
        'media_files',
        'provider_registry',
        'runtime_config'
    ]
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            WHERE t.tgname = format('trg_%s_updated_at', target_table)
              AND c.relname = target_table
              AND NOT t.tgisinternal
        ) THEN
            EXECUTE format(
                'CREATE TRIGGER trg_%I_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
                target_table,
                target_table
            );
        END IF;
    END LOOP;
END;
$$;

COMMENT ON TABLE media_items IS 'Canonical media identity table. PostgreSQL is writable source in server mode; JSON remains import/export/static fallback.';
COMMENT ON TABLE watch_state IS 'Tri-state local-first watch status. Watchlist and favourites are separate independent tables.';
COMMENT ON TABLE media_files IS 'Media inventory stores paths, filenames, QA metadata, and playback/remux status. It does not store media or image binaries by default.';
COMMENT ON TABLE provider_registry IS 'Provider metadata and health state. Logo/image data remains path-based, not binary.';
COMMENT ON TABLE runtime_config IS 'Runtime settings. Secret values are not stored here; secret_ref points to external environment/secret storage.';
COMMENT ON TABLE audit_log IS 'Append-only accountability for writes, sync, migration, and no-silent-loss validation.';

COMMIT;
