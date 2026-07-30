from bottle import run, route, response
import os
from subprocess import check_output as callx
import json
import requests
import xml.etree.ElementTree as ET

def call(args):
    print(" ".join(args))
    return callx(args)

@route('/vejr')
def vejr():
    svg = requests.get("https://www.yr.no/nb/innhold/2-2624886/meteogram.svg")
    tree = ET.fromstring(svg.content.decode())
    width = tree.attrib["width"]
    height = tree.attrib["height"]
    for attr in ["width", "height"]:
        if attr in tree.attrib:
            del tree.attrib[attr]
    new_width = 1024
    new_height = int(height) / int(width) * new_width
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
    status = requests.get("https://wiki.hal9k.dk/infrastruktur/status?do=export_xhtmlbody")
    return f"""
    <!DOCTYPE HTML>
    <head>
    <style>body {{ background: black; color: #eef; font-family: sans-serif; font-size: larger; }}
    a {{ color: #eef }}
    </style>
    </head>
    <body>
    {status.content.decode()}
    </body>
    </html>
    """

@route('/')
def index():
    return '''
    <!DOCTYPE HTML>
    <head>
    <script src=" https://cdn.jsdelivr.net/npm/@picocss/pico@1.5.7/css/postcss.config.min.js "></script>
<link href=" https://cdn.jsdelivr.net/npm/@picocss/pico@1.5.7/css/pico.min.css " rel="stylesheet">
<style>mg { width: 120px; }</style>
</head>
<body>
  <main class="container">
  <div class="grid">
    <div><a class="zoom" href="#"><img src="/1.png"></a></div>
    <div><a class="zoom" href="#"><img src="/2.png"></a></div>
    <div><a class="zoom" href="#"><img src="/3.png"></a></div>
    <div><a class="zoom" href="#"><img src="/4.png"></a></div>
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
for (let el of document.querySelectorAll("a.zoom")) {
    console.log(el);
    el.addEventListener('click', function(ev) {
        ev.preventDefault();
        let el = ev.target.closest("A");
        url = el.querySelector("img").src;
        document.getElementById("dialog-image").src = url;
        document.getElementById("dialog").setAttribute("open", "");
    });
    }

    document.getElementById("close").addEventListener("click", function() {
        document.getElementById("dialog").removeAttribute("open");
    });
    </script>

    </main>
    </body>
    </html>
'''

@route('/all.png')
def all():
    response.content_type = 'image/png'
    return call(('grim', '-'))

@route('/<screen>.png')
def screen(screen):
    print(os.getenv("SWAYSOCK"))
    print(os.getenv("WAYLAND_DISPLAY"))
    outputs = json.loads(call(("/usr/bin/swaymsg", "-t", "get_outputs")))
    outputs = list(filter(lambda output: output["active"], outputs))
    number = int(screen)
    x_offset = 1280 * number
    width = 1280
    height = 1024
    index = number - 1
    rect = outputs[index]["rect"]
    x = rect["x"]
    y = rect["y"]
    width = rect["width"]
    height = rect["height"]
    geometry = f"{x},{y} {width}x{height}"
    response.content_type = 'image/png'
    return call(('grim', '-s', '1.4', '-g', geometry, '-'))

run(host='localhost', port=8080)
