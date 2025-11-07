# app.py (place at repo root)
from flask import Flask, send_from_directory, jsonify
import subprocess, sys, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parent
APP = Flask(__name__, static_folder=str(ROOT / 'web'), static_url_path='')

@APP.get('/')
def root():
    return send_from_directory(APP.static_folder, 'index.html')

@APP.get('/config')
def config_page():
    return send_from_directory(APP.static_folder, 'config.html')

@APP.get('/data/<path:filename>')
def data_files(filename):
    return send_from_directory(str(ROOT / 'data'), filename)

@APP.post('/api/refresh')
def refresh():
    start = time.time()
    try:
        cmd = [sys.executable, str(ROOT / 'scripts' / 'fetch_tmdb.py')]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        took = round(time.time() - start, 2)
        return jsonify({'ok': True, 'seconds': took, 'stdout': res.stdout[-2000:]})
    except subprocess.CalledProcessError as e:
        return jsonify({'ok': False, 'stdout': e.stdout[-2000:] if e.stdout else '', 'stderr': e.stderr[-2000:] if e.stderr else ''}), 500

if __name__ == '__main__':
    APP.run(host='0.0.0.0', port=8811, debug=False)
