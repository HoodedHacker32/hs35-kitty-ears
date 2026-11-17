"""Render the assembly film to assembly.mp4: frame-exact capture of assembly.html?capture + its synthesised soundtrack.

python render_video.py [--url http://127.0.0.1:8766/assembly.html] [--fps 60] [--size 1920x1080] [--out assembly.mp4]
Needs: playwright (chromium), ffmpeg, and a local web server serving this folder.
"""
import argparse, base64, os, subprocess, sys, tempfile, time
from playwright.sync_api import sync_playwright
ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://127.0.0.1:8766/assembly.html")
ap.add_argument("--fps", type=int, default=60)
ap.add_argument("--size", default="1920x1080")
ap.add_argument("--out", default="assembly.mp4")
ap.add_argument("--audio", default=None, help="use this soundtrack instead of rendering it in the page")
A = ap.parse_args()
W, H = (int(v) for v in A.size.split("x"))
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.on("pageerror", lambda e: print("pageerror:", e))
    pg.goto(A.url + "?capture"); pg.wait_for_function("window.__ready && window.__ready()", timeout=300000)
    time.sleep(2)
    dur = pg.evaluate("window.__film.DUR")
    wav = A.audio
    if not wav:
        wav = os.path.join(tempfile.gettempdir(), "kitty_score.wav")
        open(wav, "wb").write(base64.b64decode(pg.evaluate("window.__film.wav()")))
    n = int(round(dur * A.fps))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(A.fps), "-i", "-", "-i", wav,
                           "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", A.out], stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(n):
        pg.evaluate(f"window.__film.seek({i / A.fps})")
        ff.stdin.write(pg.screenshot(type="png"))
        if i % 120 == 0:
            el = time.time() - t0; print(f"frame {i}/{n}  {el:.0f}s elapsed, ~{el / max(i, 1) * (n - i):.0f}s left", flush=True)
    ff.stdin.close(); ff.wait(); b.close()
print("wrote", A.out, round(os.path.getsize(A.out) / 1e6, 1), "MB")
