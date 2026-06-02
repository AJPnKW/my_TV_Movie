# WD TV Live Media Library Design

Session: CODEX-FOREST  
Date: 2026-06-02

## User Narrative

The Media Library must work for local network and WD TV Live-style workflows across home and trailer environments. The app needs to discover local devices and paths, compare expected filenames to actual filenames, run ffprobe/remux checks, and report VLC/X-plore compatibility without storing image or media binaries in PostgreSQL.

## Interpretation

Media Library is a server-side inventory and QA workflow. The browser/static app can display results, but discovery, ffprobe, ffmpeg remux, filesystem scans, and local network access belong to the server/API. PostgreSQL stores inventory metadata and QA status; files remain on shares/devices/disks.

## Architecture Decision

Use `media_files` as the inventory table and the `/api/v1/media-library/*` API routes as the scan/QA/remux boundary. Home and trailer profiles remain separate because network CIDRs, devices, paths, performance, and image-loading expectations differ.

## Network Profiles

| Profile | Network | Purpose | Behavior |
|---|---|---|---|
| `home` | `192.168.1.x` | Main home LAN and primary local media workflow. | Full scan/QA behavior when shares are reachable. |
| `trailer` | `192.168.2.x` | Trailer/light environment. | Prefer text-first/light behavior, avoid unnecessary image loading, preserve local path discovery metadata. |
| `portable` | removable/local direct paths | USB drives, portable disks, copied media sets. | Scan mounted roots and keep device/path identity. |
| `unknown` | unavailable or privacy-limited network | Browser/server cannot classify network. | Allow manual profile selection and do not infer destructive actions. |

## Discovery Model

Discovery records:

- location profile
- network CIDR or observed local subnet
- device name
- device address when available
- share name
- root path
- full file path
- expected filename
- actual filename
- first seen and last seen timestamps
- file size
- matched media item when identified

Discovery must not rename, delete, move, remux, or quarantine files by default. Those actions are separate explicit QA/remux/cleanup steps.

## Path Handling

Path examples:

- Windows UNC: `\\DEVICE\Videos\TV\Show Name\Season 01\Show Name - S01E01 - Episode.mkv`
- Linux mount: `/mnt/media/TV/Show Name/Season 01/Show Name - S01E01 - Episode.mkv`
- Portable drive: `E:\TV\Show Name\Season 01\Show Name - S01E01 - Episode.mkv`

Rules:

- Store paths as text metadata.
- Preserve original observed path strings.
- Do not normalize home/trailer/portable paths into one fake canonical path.
- Do not store media binaries in PostgreSQL.
- Store artwork/logo/image paths only; images remain files/assets.

## Filename Contract

Expected filename inputs:

- show/movie title
- season number
- episode number
- episode/movie title
- release or air date when needed
- TMDB ID when needed

Expected episode example:

```text
Show Name - S01E01 - Episode Title [01-01-26] [123456].mkv
```

Expected movie example:

```text
Movie Title [2026] [123456].mkv
```

Actual filename rules:

- Preserve the actual filename exactly as observed.
- Compare expected vs actual separately from QA playback status.
- A filename mismatch does not automatically mean the file is unplayable.
- A playable file with wrong filename should be `needs_review`, not quarantined.
- Duplicate actual filenames or duplicate media matches go to the `duplicate` bucket.

## QA Pipeline

The Media Library QA pipeline is:

```text
scan -> identify -> filename match -> ffprobe QA -> classify -> safe remux if needed -> final validation -> report
```

### ffprobe Checks

Record:

- container readability
- duration
- video stream presence
- audio stream presence
- video codec
- audio codec
- container format
- file size
- truncation/error status
- extension/container mismatch where detectable

### Remux Rules

- Use safe stream-copy remux only by default.
- Intended command shape: `ffmpeg -i input -map 0 -c copy output`.
- Do not transcode unless a future explicit contract allows it.
- Do not overwrite the source file without an explicit safe replacement workflow.
- Mark unsafe candidates as `unsafe` or `needs_review`.
- Bad/unrepairable files are quarantined and reported, never silently skipped.

## Status Buckets

### Inventory Buckets

- `matched`: expected media identity found.
- `missing`: expected file not found.
- `extra`: file exists but no media identity matched.
- `duplicate`: multiple files or matches conflict.
- `needs_review`: human review required.
- `unsupported`: file type/container not supported by configured workflow.
- `quarantined`: file isolated because it is bad/unrepairable or unsafe.

### QA Buckets

- `not_checked`: discovered but not probed.
- `ok`: ffprobe and compatibility checks passed.
- `repaired`: safe remux succeeded and final validation passed.
- `needs_review`: mismatch, warning, or ambiguous playback state.
- `quarantined`: bad/unrepairable/unsafe.
- `duplicate`: duplicate file/match.
- `unsupported`: unsupported format or workflow limitation.

### ffprobe Buckets

- `not_checked`
- `ok`
- `error`
- `duration_mismatch`
- `stream_missing`
- `container_mismatch`

### Playback Buckets

VLC status:

- `unknown`
- `playable`
- `not_playable`
- `not_tested`

X-plore status:

- `unknown`
- `playable`
- `not_playable`
- `not_tested`

VLC and X-plore status are separate because a file can behave differently by device/app even when ffprobe succeeds.

## API and Database Integration

Database table:

- `media_files`

API routes:

- `GET /api/v1/media-library/inventory`
- `POST /api/v1/media-library/scan`
- `POST /api/v1/media-library/qa`
- `POST /api/v1/media-library/remux`

Audit:

- Every scan batch creates audit evidence.
- Every remux attempt creates sync/history-style job evidence.
- Quarantine and repair decisions must include before/after paths and status changes.

## Validation

- Design states home network `192.168.1.x`.
- Design states trailer network `192.168.2.x`.
- Design includes local device/path discovery.
- Design includes expected filename and actual filename.
- Design includes ffprobe, safe remux, VLC, and X-plore status buckets.
- Design states image/media binaries remain files/assets by default.
- Design does not include destructive migration or file operation commands.

## Risks

- WD TV Live and local share discovery can be blocked by SMB version, permissions, DNS/NetBIOS, firewall, or disconnected trailer devices.
- Browser IP detection can be blocked by privacy features; manual profile override must remain available.
- ffprobe success does not prove every playback target is happy; VLC and X-plore buckets remain separate from ffprobe status.
- Remux can fix container issues but cannot repair every corrupt/truncated media file.
