# Watch Source Chooser Contract

Timestamp: `20260314T172445Z`

## Allowed Source Types

| source_type | allowed_now | notes |
|---|---|---|
| `local` | yes | local or owned media URLs already present in `links.local_media|local|localMedia` |
| `embed` | yes, existing-only | existing repo data may expose embed links such as `vidsrc` and `videasy`; this pass does not expand provider integration |
| `network` | yes | direct official/homepage/owned destinations |
| `provider_deep_link` | yes | legal provider links from `watch_providers` |
| `future_configured` | yes | `watch_sources` or `source_options` arrays when present in data |

## Required `data.json` Inputs

| field | required_for | meaning |
|---|---|---|
| `links.local_media|local|localMedia` | direct local source | owned/local playback destination |
| `links.vidsrc` | existing embed compatibility | existing embed source |
| `links.videasy` | existing embed compatibility | existing alternate embed source |
| `links.homepage|official|network|owned_url|owned` | network/owned link | official destination |
| `watch_providers` | provider section | legal provider catalog with deep link |
| `watch_sources[]` or `source_options[]` | future extension | explicit configured chooser entries |

## Chooser Behavior

| behavior | contract |
|---|---|
| open trigger | popcorn button opens chooser in modal shell |
| modal shell | reuse existing provider modal shell for compatibility |
| option ordering | local/owned first, existing embed links next, official/network links next, future configured links next, provider section last |
| fallback | if no direct sources exist, chooser still renders provider links if available |
| empty state | if neither direct sources nor providers exist, chooser shows explicit unavailable text |

## Entity Support

| entity | support |
|---|---|
| show | chooser allowed, mainly for future/owned/provider paths |
| season | chooser allowed through unified show detail context |
| episode | required |
| movie | required |
