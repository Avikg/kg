"""
serve_kg.py
Starts a local HTTP server so vis-network and other CDN libraries load correctly.

Run: python serve_kg.py
Then open: http://localhost:8000/kg_output/cancer_subgraph_explained.html
"""
import http.server, socketserver, os, webbrowser, threading, time

PORT = 8000
BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

print("=" * 55)
print("  Cancer KG - Local HTTP Server")
print("=" * 55)
print(f"  Serving: {BASE}")
print()
print("  Open in Chrome:")
print(f"  http://localhost:{PORT}/kg_output/cancer_subgraph_explained.html")
print(f"  http://localhost:{PORT}/kg_output/cancer_kg_enhanced.html")
print(f"  http://localhost:{PORT}/db_profiles/00_overview_dashboard.html")
print()
print("  Press Ctrl+C to stop.")
print("=" * 55)

def open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}/kg_output/cancer_subgraph_explained.html")

threading.Thread(target=open_browser, daemon=True).start()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")