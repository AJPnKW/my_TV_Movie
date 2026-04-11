# Hungary TV

Hungary TV is a static browser app for curated Hungary IPTV streams and XMLTV program data.

## Curated Sources

- M3U playlist: `https://iptv-org.github.io/iptv/countries/hu.m3u`
- XMLTV EPG: `https://iptv-epg.org/files/epg-hu.xml`
- Channel metadata: `https://iptv-org.github.io/api/channels.json`
- Stream metadata: `https://iptv-org.github.io/api/streams.json`
- Guide metadata: `https://iptv-org.github.io/api/guides.json`

The checked-in curated index is `data/channels.json`. It was generated from public IPTV-org API records for non-NSFW Hungary channels with active stream records.

The checked-in guide snapshot is `data/guide.json`. It is generated from the XMLTV EPG link because that remote XML file is reachable server-side but can be blocked by browser CORS when loaded directly from a static page.

## Playback Design

- Safari can play many HLS streams natively.
- Chrome, Edge, and Firefox use `hls.js` when MediaSource Extensions are available.
- Insecure `http://` streams can be blocked when the app is served over HTTPS.
- Some streams are geo-blocked or intermittent; the app exposes alternate streams and logs playback errors.
- Closed captions depend on subtitles advertised by the active HLS stream. The app detects browser text tracks and toggles them when present.
- Pause works when the browser and stream permit it. Rewind depends on DVR windows in the stream manifest and is not assumed.
- Browser-side recording is intentionally not included because live stream rights, CORS, encrypted media, and MediaRecorder support vary by source.

## User Settings

Display names and favorites are stored in local browser storage. Export settings from the channel pane to move preferences to another browser.
