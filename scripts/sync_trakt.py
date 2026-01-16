#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/sync_trakt.py
# [PROJECT] my_TV_Movie
# [ROLE]    Compatibility shim: outbound Trakt sync entrypoint.
# [VERSION] v0.1.0
# [UPDATED] 2026-01-15
# [BUILD]   14.01.15
# ==============================================================================
from __future__ import annotations
def main() -> int:
    print("sync_trakt.py is deprecated in this pipeline.")
    print("Use: scripts/fetch_trakt.py and scripts/trakt_sync_watch_state.py")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
