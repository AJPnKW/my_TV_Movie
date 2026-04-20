Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"

if (!(Test-Path ".git")) { throw "NOT A GIT REPOSITORY: C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie" }

New-Item -ItemType Directory -Path "scripts" -Force | Out-Null
New-Item -ItemType Directory -Path "web" -Force | Out-Null
New-Item -ItemType Directory -Path "web\js" -Force | Out-Null
New-Item -ItemType Directory -Path "web\css" -Force | Out-Null
New-Item -ItemType Directory -Path "logs" -Force | Out-Null

$log_file = "logs\apply_ui_fix_local_only.log.txt"
"START $(Get-Date -Format s)" | Set-Content $log_file

$runtime = "web\js\app_runtime.js"
if (Test-Path $runtime) {
    $r = Get-Content $runtime -Raw
    $r = $r -replace '\.slice\(0,\s*3\)', ''
    $r = $r -replace 'Last Week', ''
    $r = $r -replace 'v\d+\.\d+\.\d+', 'v1.4.5'
    Set-Content $runtime $r
    "UPDATED: $runtime" | Add-Content $log_file
} else {
    "MISSING: $runtime" | Add-Content $log_file
}

$css_patch = @"
.panel{border:none!important;box-shadow:none!important;padding:8px!important}
.media-card{min-width:180px!important}
.media-card img{object-fit:cover!important;object-position:center}
.media-card__overlay{background:linear-gradient(transparent,rgba(0,0,0,.85))!important}
.media-card__overlay-title{font-size:14px!important;line-height:1.2!important}
.actionbar{display:flex!important;justify-content:space-between!important}
.carousel{display:flex!important;overflow-x:auto!important}
.carousel .media-card{min-width:200px!important}
.calendar-day{padding:6px!important}
.dashcol{flex:1 1 auto!important}
"@

$css_file = "web\css\ui_fix_patch.css"
Set-Content $css_file $css_patch
"CREATED: $css_file" | Add-Content $log_file

$js_fix = @"
(function(){
  window.addEventListener('load', function(){
    document.querySelectorAll('[data-kind="episode"] img').forEach(function(img){
      var still = img.getAttribute('data-still');
      if (still) { img.src = still; }
    });
  });
})();
"@

$js_file = "web\js\fix_images.js"
Set-Content $js_file $js_fix
"CREATED: $js_file" | Add-Content $log_file

$index = "web\index.html"
if (Test-Path $index) {
    $html = Get-Content $index -Raw

    if ($html -notmatch 'ui_fix_patch\.css') {
        $html = $html -replace '<link rel="stylesheet" href="\./css/main_app\.css"\s*/?>', '$0`r`n  <link rel="stylesheet" href="./css/ui_fix_patch.css" />'
    }

    if ($html -notmatch 'fix_images\.js') {
        $html = $html -replace '</body>', '  <script src="./js/fix_images.js"></script>`r`n</body>'
    }

    Set-Content $index $html
    "UPDATED: $index" | Add-Content $log_file
} else {
    "MISSING: $index" | Add-Content $log_file
}

git status --short | Add-Content $log_file

"DONE $(Get-Date -Format s)" | Add-Content $log_file
Write-Host "LOCAL PATCH COMPLETE"
Write-Host "LOG: logs\apply_ui_fix_local_only.log.txt"
