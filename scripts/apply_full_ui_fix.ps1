# SAFE FULL UI FIX

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

cd C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie

git checkout main
git pull

# --- FIX runtime ---
if (Test-Path "web\js\app_runtime.js") {
    $r = Get-Content "web\js\app_runtime.js" -Raw
    $r = $r -replace '\.slice\(0,\s*3\)', ''
    $r = $r -replace 'Last Week', ''
    $r = $r -replace 'v\d+\.\d+\.\d+', 'v1.4.5'
    Set-Content "web\js\app_runtime.js" $r
}

# --- FIX CSS ---
$css = @"
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

Add-Content "web\css\main_app.css" $css

# --- FIX images ---
$fix = @"
(function(){
  window.addEventListener('load',function(){
    document.querySelectorAll('[data-kind=""episode""] img').forEach(function(img){
      let still = img.getAttribute('data-still');
      if(still){ img.src = still; }
    });
  });
})();
"@

Set-Content "web\js\fix_images.js" $fix

# attach script
$index = "web\index.html"
if (Test-Path $index) {
    $html = Get-Content $index -Raw
    if ($html -notmatch "fix_images.js") {
        $html = $html -replace "</body>", "  <script src=`"./js/fix_images.js`"></script>`n</body>"
        Set-Content $index $html
    }
}

git add -A
git commit -m "UI FIX FINAL: dashboard, layout, carousel, images, version"
git push

Write-Host "DONE"
