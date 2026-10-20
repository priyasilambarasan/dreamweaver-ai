import os
import time
from pathlib import Path
from urllib.parse import quote
import hmac

import requests
from flask import Flask, request, jsonify, render_template_string, send_file

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
GALLERY_DIR = BASE_DIR / "dream_gallery"
GALLERY_DIR.mkdir(exist_ok=True)

# Optional Hugging Face token
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
DELETE_TOKEN = os.environ.get("DELETE_TOKEN", "").strip()

HF_URL = (
    "https://router.huggingface.co/hf-inference/"
    "models/black-forest-labs/FLUX.1-schnell"
)

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DreamWeaver AI</title>
<style>
*{box-sizing:border-box}
body{
 margin:0;padding:15px;background:#17112d;color:#fff0ff;
 font-family:Georgia,serif
}
main{max-width:720px;margin:auto}
h1{text-align:center;font-size:32px}
.sub{text-align:center;color:#c8b6ec;margin-bottom:25px}
.panel{
 background:linear-gradient(145deg,#302344,#241b39);
 border:1px solid #49375e;border-radius:28px;
 padding:20px;margin-bottom:24px
}
label{display:block;margin:16px 0 9px;font-size:18px}
textarea,select{
 width:100%;background:#171128;color:white;
 border:1px solid #49375e;border-radius:17px;
 padding:14px;font:16px Georgia,serif
}
textarea{min-height:120px;resize:vertical}
button{
 border:1px solid #554269;border-radius:17px;
 padding:14px;background:#3a2c4d;color:white;
 font:bold 16px Georgia,serif;cursor:pointer
}
button:disabled{opacity:.5}
.full{width:100%;margin-top:15px}
.primary{
 background:linear-gradient(100deg,#c9a0ff,#9567f2);
 color:#241339;border:0;padding:19px
}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.shapes{display:flex;gap:8px;margin-top:10px}
.shapes button{flex:1;padding:12px 5px;font-size:14px}
.selected{background:#694b91!important;border-color:#d2a7ff!important}
#status{
 display:none;margin-top:18px;padding:15px;
 border-radius:15px;background:#3a2a40;color:#ffe0a8;
 overflow-wrap:anywhere;line-height:1.5
}
#canvas{text-align:center;min-height:250px}
#canvas img{width:100%;border-radius:18px;margin-top:15px}
#empty{padding:45px 5px;color:#c7b6df}
#gallery{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.tile img{width:100%;border-radius:12px}
.tile button{width:100%;margin-top:5px;padding:9px;font-size:13px}
.small{font-size:13px;color:#c8b6df;line-height:1.5}
a{color:#dfc5ff}
</style>
</head>
<body>
<main>
<h1>✧ DreamWeaver AI</h1>
<div class="sub">Turn your imagination into a dream</div>

<section class="panel">
<label for="prompt">Describe your dream</label>
<textarea id="prompt" maxlength="1200" placeholder="A magical floating island above the clouds..."></textarea>

<button class="full" onclick="surprise()">✧ Surprise Me</button>

<div class="row">
<div>
<label for="style">Art Style</label>
<select id="style">
<option>Fantasy</option>
<option>Anime</option>
<option>Watercolor</option>
<option>Realistic</option>
<option>Digital Art</option>
<option>Pixel Art</option>
<option>Oil Painting</option>
</select>
</div>
<div>
<label for="mood">Dream Mood</label>
<select id="mood">
<option>Magical</option>
<option>Nostalgic</option>
<option>Peaceful</option>
<option>Mysterious</option>
<option>Dreamy</option>
<option>Adventurous</option>
</select>
</div>
</div>

<label>Canvas Shape</label>
<div class="shapes">
<button data-shape="square" onclick="setShape('square',this)">Square</button>
<button data-shape="portrait" onclick="setShape('portrait',this)">Portrait</button>
<button data-shape="landscape" class="selected"
onclick="setShape('landscape',this)">Landscape</button>
</div>

<button id="generate" class="full primary" onclick="generate()">
✨ Weave into Image
</button>
<div id="status"></div>
</section>

<section class="panel" id="canvas">
<div id="empty">
<div style="font-size:70px">✧</div>
<h2>Your Dream Canvas</h2>
<p>Your imagined world will appear here.</p>
<p>Choose your settings and create something wonderful.</p>
</div>
<div id="result"></div>
</section>

<section class="panel">
<h2>✦ Dream Gallery</h2>
<div id="gallery">Loading gallery...</div>
<button class="full" onclick="loadGallery()">↻ Refresh Gallery</button>
</section>

<p class="small">
Image generation requires an available image service.
Free services may have limits or refuse requests.
</p>
</main>

<script>
let currentShape="landscape";
let deleteToken="";

function getDeleteToken(){
 if(deleteToken)return deleteToken;
 const value=window.prompt("Enter DELETE_TOKEN to remove this image:");
 if(value)deleteToken=value.trim();
 return deleteToken;
}

async function readJSON(response){
 const text=await response.text();
 try{return JSON.parse(text);}
 catch{return {error:"Server returned an invalid response."};}
}

const ideas=[
"A magical crystal palace above fluffy clouds, glowing waterfalls, purple moon and sparkling stars",
"A tiny cottage inside a giant glowing flower, fireflies and enchanted forest",
"A dreamy island floating in a lavender sky, rainbow waterfall and magical butterflies",
"A secret library among the stars, floating books and golden lights",
"A peaceful underwater kingdom with glowing coral and crystal towers"
];

function surprise(){
 document.getElementById("prompt").value=
 ideas[Math.floor(Math.random()*ideas.length)];
 document.getElementById("style").value="Fantasy";
 document.getElementById("mood").value="Magical";
}

function setShape(value,button){
 currentShape=value;
 document.querySelectorAll("[data-shape]").forEach(
  b=>b.classList.remove("selected")
 );
 button.classList.add("selected");
}

function showStatus(message){
 const el=document.getElementById("status");
 el.style.display="block";
 el.textContent=message;
}

function escapeHTML(value){
 return String(value).replace(/[&<>"']/g,c=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
 }[c]));
}

async function generate(){
 const prompt=document.getElementById("prompt").value.trim();

 if(!prompt){
  showStatus("Please describe your dream first.");
  return;
 }

 const button=document.getElementById("generate");
 button.disabled=true;
 button.textContent="✨ Weaving your dream...";
 showStatus("Connecting to image service. Please wait...");

 try{
  const response=await fetch("/generate",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({
    prompt:prompt,
    style:document.getElementById("style").value,
    mood:document.getElementById("mood").value,
    shape:currentShape
   })
  });

  const data=await readJSON(response);

  if(!response.ok){
   throw new Error(data.error||"Image generation failed.");
  }

  document.getElementById("empty").style.display="none";
  document.getElementById("result").innerHTML=
   '<img src="'+data.image+'" alt="Generated dream image">'+
   '<p>'+escapeHTML(data.prompt)+'</p>'+
   '<a href="'+data.url+'" download="'+
   escapeHTML(data.filename)+'">Download image</a>';

  showStatus("Your dream image is ready! ✨");
  loadGallery();

 }catch(error){
  showStatus(error.message);
 }finally{
  button.disabled=false;
  button.textContent="✨ Weave into Image";
 }
}

async function loadGallery(){
 try{
  const response=await fetch("/gallery");
  const data=await readJSON(response);
  const el=document.getElementById("gallery");

  if(!data.images.length){
   el.textContent="No saved dreams yet.";
   return;
  }

  el.innerHTML=data.images.map(item=>
   '<div class="tile">'+
   '<img src="'+item.url+'" alt="Saved dream">'+
   '<a href="'+item.url+'" download="'+escapeHTML(item.name)+'">Download</a>'+
   '<button onclick="deleteImage(\''+
   encodeURIComponent(item.name)+'\')">Delete</button>'+
   '</div>'
  ).join("");

 }catch(error){
  document.getElementById("gallery").textContent=
   "Could not load gallery.";
 }
}

async function deleteImage(encodedName){
 if(!confirm("Delete this saved dream?"))return;

 const response=await fetch("/delete/"+encodedName,{
  method:"DELETE"
 });
 const data=await response.json();

 if(!response.ok){
  showStatus(data.error||"Delete failed.");
  return;
 }

 loadGallery();
}

loadGallery();
</script>
</body>
</html>
"""


def make_image(prompt, width, height):
    # Use Hugging Face if a token is configured.
    if HF_TOKEN:
        response = requests.post(
            HF_URL,
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": prompt,
                "parameters": {
                    "width": width,
                    "height": height
                }
            },
            timeout=180
        )

        if (
            response.ok
            and response.headers.get("Content-Type", "").startswith("image/")
        ):
            return response.content, response.headers.get(
                "Content-Type", "image/png"
            )

        raise RuntimeError(
            f"Hugging Face error {response.status_code}: "
            f"{response.text[:250]}"
        )

    # Public no-token fallback. Availability is not guaranteed.
    url = (
        "https://image.pollinations.ai/prompt/"
        + quote(prompt, safe="")
        + f"?width={width}&height={height}&nologo=true"
    )

    response = requests.get(
        url,
        headers={"User-Agent": "DreamWeaverAI/1.0"},
        timeout=180
    )

    if (
        response.ok
        and response.headers.get("Content-Type", "").startswith("image/")
    ):
        return response.content, response.headers.get(
            "Content-Type", "image/jpeg"
        )

    raise RuntimeError(
        f"Free image service returned HTTP {response.status_code}. "
        "The service may be unavailable or may require access. "
        "Try again later or configure HF_TOKEN."
    )


ALLOWED_STYLES = {
    "Fantasy", "Anime", "Watercolor", "Realistic",
    "Digital Art", "Pixel Art", "Oil Painting"
}

ALLOWED_MOODS = {
    "Magical", "Nostalgic", "Peaceful",
    "Mysterious", "Dreamy", "Adventurous"
}

ALLOWED_SHAPES = {"square", "portrait", "landscape"}


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/generate", methods=["POST"])
def generate_image():
    data = request.get_json(silent=True) or {}

    prompt = str(data.get("prompt", "")).strip()[:1200]
    style = str(data.get("style", "Fantasy")).strip()[:50]
    mood = str(data.get("mood", "Magical")).strip()[:50]
    shape = str(data.get("shape", "landscape")).strip()

    if not prompt:
        return jsonify(error="Please enter a dream description."), 400

    if style not in ALLOWED_STYLES:
        style = "Fantasy"
    if mood not in ALLOWED_MOODS:
        mood = "Magical"
    if shape not in ALLOWED_SHAPES:
        shape = "landscape"

    sizes = {
        "square": (768, 768),
        "portrait": (576, 1024),
        "landscape": (1024, 576)
    }

    width, height = sizes[shape]
    full_prompt = (
        f"{prompt}. Art style: {style}. Mood: {mood}. "
        "Detailed, beautiful composition, high quality artwork."
    )

    try:
        content, mime = make_image(full_prompt, width, height)

        extension = {
            "image/jpeg": ".jpg",
            "image/webp": ".webp"
        }.get(mime.split(";")[0], ".png")

        filename = f"dream_{time.time_ns()}{extension}"
        (GALLERY_DIR / filename).write_bytes(content)

        image_url = "/image/" + quote(filename)

        return jsonify(
            image=image_url,
            url=image_url,
            filename=filename,
            prompt=prompt
        )

    except requests.Timeout:
        return jsonify(
            error="Image request timed out. Please try again."
        ), 504

    except requests.RequestException as exc:
        return jsonify(
            error=f"Network error: {str(exc)[:180]}"
        ), 502

    except RuntimeError as exc:
        return jsonify(error=str(exc)), 502

    except Exception as exc:
        return jsonify(
            error=f"Unexpected error: {str(exc)[:180]}"
        ), 500


@app.route("/gallery")
def gallery():
    images = []

    for path in sorted(
        GALLERY_DIR.iterdir(),
        key=lambda item: item.stat().st_mtime,
        reverse=True
    ):
        if path.is_file() and path.suffix.lower() in {
            ".png", ".jpg", ".jpeg", ".webp"
        }:
            images.append({
                "name": path.name,
                "url": "/image/" + quote(path.name)
            })

    return jsonify(images=images)


@app.route("/image/<path:filename>")
def image_file(filename):
    path = (GALLERY_DIR / filename).resolve()

    if (
        path.parent != GALLERY_DIR.resolve()
        or not path.is_file()
        or path.is_symlink()
    ):
        return jsonify(error="Image not found."), 404

    return send_file(path)


@app.route("/delete/<path:filename>", methods=["DELETE"])
def delete_image(filename):
    path = (GALLERY_DIR / filename).resolve()

    if not DELETE_TOKEN:
        return jsonify(
            error="Delete is disabled. Configure DELETE_TOKEN first."
        ), 403

    supplied_token = request.headers.get("X-Delete-Token", "")
    if not hmac.compare_digest(supplied_token, DELETE_TOKEN):
        return jsonify(error="Invalid delete token."), 403

    if (
        path.parent != GALLERY_DIR.resolve()
        or not path.is_file()
        or path.is_symlink()
    ):
        return jsonify(error="Image not found."), 404

    path.unlink()
    return jsonify(success=True)


if __name__ == "__main__":
    print("DreamWeaver AI starting...")
    print("Open http://<YOUR-COMPUTER-IP>:5000 in your phone browser.")
    print("Set HF_TOKEN for Hugging Face or use the public fallback service.")
    print("Set DELETE_TOKEN to enable gallery deletion.")
    app.run(host="0.0.0.0", port=5000, debug=False)
