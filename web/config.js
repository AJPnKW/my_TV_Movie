/* ======================================================================================
[FILE]        web/config.js
[PROJECT]     my_TV_Movie (My TV Hub)
[ROLE]        Config UI logic: load defaults, validate, apply, save (client-side)
[VERSION]     v1.2.0
[UPDATED]     2025-12-14
[OWNER]       Andrew & Brant (internal)
[DEPENDS ON]  web/config.html (form + controls)
              web/config.json (schema defaults)
[NOTES]
- Must NOT assume a server-side "saveConfig()" endpoint (GitHub Pages is static).
- Store user edits in browser localStorage; web/config.json remains the workflow baseline.
====================================================================================== */


// Save config values to config.json
document.getElementById('configForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const configData = {
        streaming_services: {
            vidsrc_tv: document.getElementById('vidsrcTvUrl').value,
            vidsrc_movie: document.getElementById('vidsrcMovieUrl').value,
            videasy_tv: document.getElementById('videasyTvUrl').value,
            videasy_movie: document.getElementById('videasyMovieUrl').value
        },
        image_sizes: {
            show_width: parseInt(document.getElementById('showImageWidth').value),
            movie_width: parseInt(document.getElementById('movieImageWidth').value)
        }
    };

    // Assuming this data is saved to the server or locally as a file
    saveConfig(configData);
});

function saveConfig(configData) {
    // Save the configuration (for now, we assume a simple local storage / file update)
    fetch('save-config-endpoint', {
        method: 'POST',
        body: JSON.stringify(configData),
        headers: { 'Content-Type': 'application/json' }
    });
}
