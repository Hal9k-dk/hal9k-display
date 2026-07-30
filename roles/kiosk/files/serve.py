from bottle import run, route, response
import os
import glob
from subprocess import check_output as callx
import json
import requests
import xml.etree.ElementTree as ET

REQUEST_TIMEOUT = 10  # seconds

def _ensure_sway_env():
    """Auto-detect SWAYSOCK and WAYLAND_DISPLAY if not already set."""
    if 'SWAYSOCK' not in os.environ:
        runtime = os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')
        sockets = glob.glob(f'{runtime}/sway-ipc.*.sock')
        if sockets:
            os.environ['SWAYSOCK'] = sorted(sockets)[-1]
    if 'WAYLAND_DISPLAY' not in os.environ:
        os.environ['WAYLAND_DISPLAY'] = 'wayland-1'

_ensure_sway_env()

def call(args):
    print(" ".join(args))
    return callx(args, env=os.environ)

def get_outputs():
    """Return list of active sway outputs."""
    outputs = json.loads(call(("/usr/bin/swaymsg", "-t", "get_outputs")))
    return [o for o in outputs if o["active"]]

def _error_page(title, msg):
    return f"""
    <!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><title>{title}</title>
    <style>body{{background:#111;color:#eef;font-family:sans-serif;
    display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
    </style></head><body><h1>{title}</h1><p>{msg}</p></body></html>
    """

@route('/vejr')
def vejr():
    try:
        svg = requests.get(
            "https://www.yr.no/nb/innhold/2-2624886/meteogram.svg",
            timeout=REQUEST_TIMEOUT)
        svg.raise_for_status()
    except Exception as e:
        response.status = 502
        return _error_page("Weather unavailable", str(e))

    tree = ET.fromstring(svg.content.decode())
    width = tree.attrib["width"]
    height = tree.attrib["height"]
    for attr in ["width", "height"]:
        if attr in tree.attrib:
            del tree.attrib[attr]
    tree.attrib["viewBox"] = f"0 0 {width} {height}"
    ET.register_namespace("", "http://www.w3.org/2000/svg")

    return f"""
    <!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="Refresh" content="1200" />
<style>
  html, body {{
      margin: 0;
      height: 100%;
      width: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      }}
</style>
    </head>
    <body>
    { ET.tostring(tree, encoding="unicode") }
    </body>
</html>
    """

@route('/status')
def status():
    try:
        r = requests.get(
            "https://wiki.hal9k.dk/infrastruktur/status?do=export_xhtmlbody",
            timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        body = r.content.decode()
    except Exception as e:
        response.status = 502
        return _error_page("Status unavailable", str(e))

    return f"""
    <!DOCTYPE HTML>
    <head>
    <style>body {{ background: black; color: #eef; font-family: sans-serif; font-size: larger; }}
    a {{ color: #eef }}
    </style>
    </head>
    <body>
    {body}
    </body>
    </html>
    """

@route('/')
def index():
    try:
        screens = len(get_outputs())
    except Exception:
        screens = 4

    imgs = "\n".join(
        f'    <div><a class="zoom" href="#"><img src="/{i}.png"></a></div>'
        for i in range(1, screens + 1))

    return f'''
    <!DOCTYPE HTML>
    <head>
    <link href=" https://cdn.jsdelivr.net/npm/@picocss/pico@1.5.7/css/pico.min.css " rel="stylesheet">
<style>img {{ max-width: 200px; height: auto; }}</style>
</head>
<body>
  <main class="container">
  <div class="grid">
{imgs}
    </div>
    <dialog id="dialog">
  <article>
 <header>
      <a id="close" href="#close" aria-label="Close" class="close"></a>
    </header>
    <p>
      <img id="dialog-image" src="/1.png">
    </p>
  </article>
</dialog>

<script>
for (let el of document.querySelectorAll("a.zoom")) {{
    el.addEventListener('click', function(ev) {{
        ev.preventDefault();
        let el = ev.target.closest("A");
        let url = el.querySelector("img").src;
        document.getElementById("dialog-image").src = url;
        document.getElementById("dialog").setAttribute("open", "");
    }});
}}
document.getElementById("close").addEventListener("click", function() {{
    document.getElementById("dialog").removeAttribute("open");
}});
    </script>

    </main>
    </body>
    </html>
'''

@route('/all.png')
def all():
    response.content_type = 'image/png'
    return call(('grim', '-'))

@route('/<screen:int>.png')
def screen(screen):
    outputs = get_outputs()
    index = screen - 1
    if index < 0 or index >= len(outputs):
        response.status = 404
        return "screen not found"

    rect = outputs[index]["rect"]
    geometry = f"{rect['x']},{rect['y']} {rect['width']}x{rect['height']}"
    response.content_type = 'image/png'
    return call(('grim', '-s', '1.4', '-g', geometry, '-'))

run(host='localhost', port=8080, quiet=True)
