"""Start locally from Windows Explorer and open the browser after HTTP readiness."""
import socket
import threading
import time
import urllib.request
import webbrowser
from app import create_app

def available_port():
    for port in (5000, 5001, 5050, 8080):
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError('Ports 5000, 5001, 5050 and 8080 are busy. Close an old ParcelTrack server and try again.')

def open_when_ready(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(40):
        try:
            with opener.open(url, timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            time.sleep(0.25)
    print('Automatic browser opening failed. Open the local URL printed above manually.')

if __name__ == '__main__':
    app = create_app()
    port = available_port()
    url = f'http://127.0.0.1:{port}/track'
    print(f'ParcelTrack: {url}\nKeep this window open while using the website. Press Ctrl+C to stop.', flush=True)
    threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
