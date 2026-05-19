# FILE: scripts/apply_contract_recovery_v3_overlay.ps1
# VERSION: v1.0.0
# UPDATED: 2026-05-18
# CHANGE NOTES:
# - Fixes prior overlay root bug caused by resolving paths from user profile/SHELL instead of repo location.
# - Detects repo root by walking upward from the script path until .git and docs/00_master_contract.html are found.
# - Archives the current contract before editing.
# - Injects a detailed recovery section additively; does not regenerate the whole contract.
# - Writes a Codex implementation prompt into codex_prompts/.

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$timestamp] $Message"
    Write-Host $line
    if ($script:LogFile) { Add-Content -LiteralPath $script:LogFile -Value $line -Encoding UTF8 }
}

function Find-RepoRoot {
    param([string]$StartPath)
    $current = Resolve-Path -LiteralPath $StartPath
    $dir = Get-Item -LiteralPath $current
    if (-not $dir.PSIsContainer) { $dir = $dir.Directory }
    while ($null -ne $dir) {
        $git = Join-Path $dir.FullName '.git'
        $contract = Join-Path $dir.FullName 'docs\00_master_contract.html'
        if ((Test-Path -LiteralPath $git) -and (Test-Path -LiteralPath $contract)) {
            return $dir.FullName
        }
        $dir = $dir.Parent
    }
    throw "Could not locate repo root from $StartPath"
}

$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot = Find-RepoRoot -StartPath $ScriptDir
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$LogDir = Join-Path $RepoRoot 'logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$script:LogFile = Join-Path $LogDir "apply_contract_recovery_v3_$Stamp.log.txt"

Write-Log "START contract recovery v3 overlay"
Write-Log "REPO_ROOT $RepoRoot"
Write-Log "SCRIPT_DIR $ScriptDir"

$ContractPath = Join-Path $RepoRoot 'docs\00_master_contract.html'
$ArchiveDir = Join-Path $RepoRoot 'docs\_archive\contracts'
New-Item -ItemType Directory -Path $ArchiveDir -Force | Out-Null
$ArchivePath = Join-Path $ArchiveDir "00_master_contract_pre_recovery_v3_$Stamp.html"
Copy-Item -LiteralPath $ContractPath -Destination $ArchivePath -Force
Write-Log "ARCHIVED $ArchivePath"

$PromptDir = Join-Path $RepoRoot 'codex_prompts'
New-Item -ItemType Directory -Path $PromptDir -Force | Out-Null
$PromptPath = Join-Path $PromptDir 'contract_recovery_v3_implementation_prompt.txt'
$Prompt = @'
You are working in:
C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie

SOURCE OF TRUTH:
docs/00_master_contract.html

TASK:
Fix the popup, navigation, Media Library, trailer/light mode, TMDB ID display, and media-file QA drift documented in the MC-2026-05-18.1 recovery section.

NON-NEGOTIABLE RULES:
- Do not regenerate the contract from scratch.
- Do not replace the watch popup with a minimal provider list.
- Do not remove legacy streaming providers; classify them as active, degraded, legacy, blocked, or archived.
- Do not simplify user examples into generic wording.
- Screenshot-visible failures override previous QA claims.

IMPLEMENTATION REQUIREMENTS:
1. Restore Watch Source popup to full two-panel design:
   - left media detail panel
   - right provider panel
   - sticky Exit button
   - title, episode/movie title, metadata row, TMDB ID, description, generated filename copy line
   - streamers/watch-now section on left side
   - providers/where-to-watch section aligned by country/provider row
   - no raw admin notes/status text
   - provider lifecycle indicators: eye + check/warning

2. Add popup/form reference labels:
   - bottom-right visible label on every page/form/popup panel
   - not on media cards

3. Add TMDB ID to episode card metadata:
   - Show title
   - Episode title
   - SxxExx • runtime • TMDB: id

4. Fix Media Library navigation:
   - add Media_Library.html
   - add library icon to standard nav header
   - icon must not render under logo or left filter rail
   - opens Media_Library.html in a separate tab

5. Add Trailer/Light mode:
   - if detectable local network is 192.168.2.x, default browser session to light mode where possible
   - otherwise provide session slider under Ready/version area
   - modes: Full / Light
   - Light mode does not create img src for posters/stills/backdrops but renders all text/actions
   - user override persists for current browser session

6. Media QA pipeline:
   - every file in media cleanup pipeline gets ffprobe validation
   - safe remux uses ffmpeg stream copy
   - report media_file_qa.csv, media_file_qa.json, repair_actions.log.txt, unrepaired_files.csv, final_summary.html
   - validation must fail if ffprobe/ffmpeg paths are absent from the pipeline

7. Contract/inventory:
   - preserve and extend docs/00_master_contract.html
   - add/update file inventory, folder inventory, runtime ownership map, popup schema, provider lifecycle, validation matrix
   - every major section needs Added / Updated / Origin metadata

VALIDATION:
Run:
powershell -ExecutionPolicy Bypass -File scripts\validate_runtime.ps1
node scripts\qa_browser_layout_check.mjs
py scripts\validate_media_renamer.py

RETURN ONLY:
1. git status
2. commits
3. files changed
4. root causes fixed
5. popup rendered proof
6. nav/media library proof
7. trailer light mode proof
8. media QA proof
9. validation results
'@
Set-Content -LiteralPath $PromptPath -Value $Prompt -Encoding UTF8
Write-Log "INSTALLED $PromptPath"

$Content = Get-Content -LiteralPath $ContractPath -Raw -Encoding UTF8
$StartMarker = '<!-- MC-2026-05-18.1-RECOVERY-START -->'
$EndMarker = '<!-- MC-2026-05-18.1-RECOVERY-END -->'
$RecoverySection = @'
<!-- MC-2026-05-18.1-RECOVERY-START -->
<section id="recovery-20260518" class="card">
<h2>MC-2026-05-18.1 Recovery Contract — Popup, Media Library, Trailer Mode, and Media QA</h2>
<table><tr><th>Metadata</th><th>Value</th></tr>
<tr><td>Added</td><td>MC-2026-05-18.1</td></tr>
<tr><td>Updated</td><td>MC-2026-05-18.1</td></tr>
<tr><td>Origin</td><td>User screenshot and console evidence showed the watch popup collapsed into a provider-only list, Media Library navigation rendered in the wrong location, popup/form reference labels were missing, TMDB ID was missing from episode cards, trailer/light runtime behavior was not defined, and media file QA was not enforced as one pipeline.</td></tr>
<tr><td>Status</td><td>Authoritative until replaced by a later explicitly versioned section.</td></tr>
</table>

<h3>R1. Contract update rules</h3>
<ul>
<li>The contract must be edited additively. It must not be regenerated from scratch.</li>
<li>Before major contract edits, archive the current file under <code>docs/_archive/contracts/</code>.</li>
<li>Every major section must show Added, Updated, and Origin metadata.</li>
<li>User screenshots and concrete examples are acceptance evidence and must become QA assertions.</li>
<li>Do not remove legacy provider URLs or historical design elements unless explicitly classified and archived.</li>
</ul>

<h3>R2. Repo inventory and ownership required</h3>
<table><tr><th>Inventory area</th><th>Required documentation</th></tr>
<tr><td>Page files</td><td>Every active page under <code>web/</code>, including Dashboard, Shows, Movies, Calendar, Discover, Config, Manage Watch State, Watch Me compatibility, Inputs Editor, and Media Library.</td></tr>
<tr><td>Runtime files</td><td>Every active JS owner and its scope: app runtime, card renderer, action bar, watch state manager, focus/D-pad manager, provider popup guard or replacement.</td></tr>
<tr><td>CSS ownership</td><td>Primary layout owner, compatibility/shim status, card layout owner, popup layout owner, calendar layout owner, carousel layout owner.</td></tr>
<tr><td>Data files</td><td>Catalog data, detail data, calendar data, provider registry, watch state queue, config, generated media reference.</td></tr>
<tr><td>Scripts</td><td>Build, validation, media cleanup, media QA, Trakt sync, asset optimization, and GitHub workflow scripts.</td></tr>
<tr><td>Reports/logs</td><td>Expected report names, log names, archive policy, and which outputs are tracked versus local-only.</td></tr>
</table>

<h3>R3. Watch Source popup schema</h3>
<p>The watch popup must never be replaced by a minimal provider-only list. Any guard or compatibility file may clean unsafe/admin text only; it must preserve the full popup structure.</p>
<table><tr><th>Popup area</th><th>Required content</th></tr>
<tr><td>Left media detail panel</td><td>Still/poster in Full mode; no image in Light mode; title; episode/movie title; action row; rating; metadata; TMDB ID; date; description; generated filename copy line.</td></tr>
<tr><td>Metadata row</td><td>Episodes: <code>S11E01 • 68 min • May 8, 2026 • TMDB: 67482</code>. Movies: <code>Runtime • Release date • TMDB: id</code>.</td></tr>
<tr><td>Generated filename line</td><td>Plain selectable text after one blank line below description. Example: <code>RuPaul's Drag Race All Stars - S11E01 - Break Dancin' 2 - Electric Rugaloo [05-05-26] [67482]</code>.</td></tr>
<tr><td>Streamers / Watch Now</td><td>Rendered on the left side as compact rows. Provider name plus eye icon plus status icon. No raw admin notes.</td></tr>
<tr><td>Providers / Where to Watch</td><td>Country and provider icons aligned on the same row. Compact spacing. No outline boxes around provider icons or streaming service buttons unless required for focus state.</td></tr>
<tr><td>Exit</td><td>Sticky Exit button inside the popup shell. All popup exits must remain visible while scrolling.</td></tr>
<tr><td>Reference label</td><td>Small bottom-right label such as <code>REF: POP-WATCH-SOURCE</code>.</td></tr>
</table>

<h3>R4. Provider lifecycle and rendering</h3>
<table><tr><th>Provider state</th><th>Rendering rule</th></tr>
<tr><td>active</td><td>Visible in Watch Now with eye icon and green check when verified working.</td></tr>
<tr><td>degraded</td><td>Visible with eye icon and warning/yield icon.</td></tr>
<tr><td>legacy</td><td>Retained in registry and visible only in a separate legacy section if enabled; not deleted.</td></tr>
<tr><td>blocked</td><td>Hidden from public popup but retained in registry/reporting with reason.</td></tr>
<tr><td>archived</td><td>Retained for audit/history only.</td></tr>
</table>
<ul>
<li>Known verified working from user testing: <code>VidEasy</code> and <code>2Embed CC</code> use eye + green check.</li>
<li>VidSrc remains retained and may be active/degraded based on health result, not deleted.</li>
<li>SuperEmbed, MultiEmbed, SmashyStream, FlixHQ, and other historical entries must not be silently removed; classify them.</li>
<li>Forbidden public text: <code>ACTIVE CANDIDATE FROM USER FINDINGS</code>, raw <code>ACTIVE</code>, raw <code>DEGRADED</code>, raw <code>BLOCKED</code>, raw notes/comments.</li>
</ul>

<h3>R5. Episode card metadata</h3>
<p>Episode cards across Dashboard, Calendar, Shows, popups, and carousels must include the TMDB ID in the detail block where space allows.</p>
<pre>CIA
Broken Glass
S01E12 • 43 min • TMDB: 123456</pre>
<pre>FROM
What a Long Strange Trip It's Been
S04E05 • 52 min • TMDB: 987654</pre>

<h3>R6. Media Library page and navigation</h3>
<ul>
<li>Add <code>web/Media_Library.html</code>.</li>
<li>Add a library/books icon to the standard view icon header.</li>
<li>The icon must render within the normal nav group, not under the logo and not behind the left filter rail.</li>
<li>The icon opens <code>Media_Library.html</code> in a separate tab.</li>
<li>The page includes <code>REF: PAGE-MEDIA-LIBRARY</code>.</li>
<li>The page summarizes media QA pipeline results: OK, repaired, needs review, quarantined, duplicate, unsupported.</li>
</ul>

<h3>R7. Trailer / Light mode</h3>
<ul>
<li>Add a Full/Light slider under the Ready/version area.</li>
<li>Default is Full except when the browser/session can identify the trailer network as <code>192.168.2.x</code>; if browser privacy prevents IP detection, provide manual session override.</li>
<li>Light mode must not create <code>img src</code> for posters, stills, backdrops, or large logos.</li>
<li>Light mode still renders text, metadata, actions, ratings, provider buttons, carousels, popups, and watch-state controls.</li>
<li>User override persists for the current browser session.</li>
</ul>

<h3>R8. Media file QA pipeline</h3>
<p>Media cleanup is not only renaming. The single pipeline is:</p>
<pre>scan → identify → filename match → ffprobe QA → classify → safe remux if needed → rename/move → final validation → report</pre>
<table><tr><th>Requirement</th><th>Rule</th></tr>
<tr><td>All files</td><td>Every media file in scope must be checked, not only examples.</td></tr>
<tr><td>ffprobe</td><td>Validate container readability, duration, video stream, audio stream, codec, file size, truncation/error status, and extension/container mismatch where detectable.</td></tr>
<tr><td>ffmpeg repair</td><td>When safe, remux with stream copy: <code>ffmpeg -i input -map 0 -c copy output</code>. Do not transcode unless explicitly required.</td></tr>
<tr><td>Compatibility</td><td>Target playback compatibility is VLC and X-plore.</td></tr>
<tr><td>Failure</td><td>Bad/unrepairable files are quarantined and reported; never silently skipped.</td></tr>
<tr><td>Reports</td><td><code>media_file_qa.csv</code>, <code>media_file_qa.json</code>, <code>repair_actions.log.txt</code>, <code>unrepaired_files.csv</code>, <code>final_summary.html</code>.</td></tr>
</table>

<h3>R9. Popup/form reference labels</h3>
<ul>
<li>Every popup, form, modal, major page shell, and major panel must show a small bottom-right reference label.</li>
<li>Examples: <code>REF: POP-WATCH-SOURCE</code>, <code>REF: POP-SHOW-DETAIL</code>, <code>REF: POP-MOVIE-DETAIL</code>, <code>REF: PAGE-MEDIA-LIBRARY</code>.</li>
<li>Do not put reference labels on media cards.</li>
</ul>

<h3>R10. Validation requirements</h3>
<ul>
<li>Fail if Watch Source popup renders only provider names or loses title/metadata/description/generated filename.</li>
<li>Fail if popup guard replaces full popup markup instead of post-processing it.</li>
<li>Fail if provider admin notes/status text appears in public popup.</li>
<li>Fail if legacy providers are deleted instead of classified.</li>
<li>Fail if Media Library nav icon renders outside the nav group or overlaps the left filter rail.</li>
<li>Fail if episode cards omit TMDB ID where required.</li>
<li>Fail if Light mode still loads hidden images.</li>
<li>Fail if media validator does not call/reference ffprobe and repair logic does not call/reference ffmpeg.</li>
</ul>
</section>
<!-- MC-2026-05-18.1-RECOVERY-END -->
'@

if ($Content.Contains($StartMarker) -and $Content.Contains($EndMarker)) {
    $Pattern = [regex]::Escape($StartMarker) + '.*?' + [regex]::Escape($EndMarker)
    $Content = [regex]::Replace($Content, $Pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $RecoverySection }, [System.Text.RegularExpressions.RegexOptions]::Singleline)
    Write-Log 'UPDATED existing MC-2026-05-18.1 recovery section'
} else {
    if ($Content -notmatch '</main>') { throw 'Contract missing </main> marker; refusing unsafe edit.' }
    $Content = $Content -replace '</main>', ($RecoverySection + "`r`n</main>")
    Write-Log 'INSERTED MC-2026-05-18.1 recovery section before </main>'
}

$Content = $Content -replace 'Version MC-2026-05-07\.1\.', 'Version MC-2026-05-18.1.'
if ($Content -notmatch 'MC-2026-05-18\.1') {
    throw 'Contract version marker not updated.'
}
Set-Content -LiteralPath $ContractPath -Value $Content -Encoding UTF8
Write-Log "UPDATED $ContractPath"

$ValidationText = Get-Content -LiteralPath $ContractPath -Raw -Encoding UTF8
$RequiredMarkers = @(
    'MC-2026-05-18.1 Recovery Contract',
    'Watch Source popup schema',
    'Media Library page and navigation',
    'Trailer / Light mode',
    'Media file QA pipeline',
    'Popup/form reference labels',
    'ffprobe',
    'ffmpeg',
    'REF: POP-WATCH-SOURCE'
)
foreach ($marker in $RequiredMarkers) {
    if ($ValidationText -notmatch [regex]::Escape($marker)) {
        throw "Validation failed; missing marker: $marker"
    }
}
Write-Log 'VALIDATION PASSED'
Write-Log "LOG_FILE $script:LogFile"
Write-Log 'NEXT: git add docs codex_prompts'
Write-Log 'NEXT: git commit -m "recover contract popup media library media qa v3"'
Write-Log 'END contract recovery v3 overlay'
