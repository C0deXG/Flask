from flask import Flask, render_template_string, request, redirect
import os
import json
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

app = Flask(__name__)

book = epub.read_epub('shadow_slave.epub')

# Extract only valid XHTML chapters
chapter_items = [item for item in book.items if item.get_type() == ITEM_DOCUMENT]
chapter_items.sort(key=lambda x: x.get_id())

# Adjust this based on where "Chapter 1001" actually starts
REAL_CHAPTER_START_INDEX = 8  # ✅ Adjust this based on your book
REAL_CHAPTER_START_NUMBER = 1001
CHAPTER_OFFSET = REAL_CHAPTER_START_NUMBER - REAL_CHAPTER_START_INDEX

CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)

RANGE_FILE = os.path.join(CACHE_DIR, 'range.json')
DEFAULT_RANGE = {'from': 1001, 'to': 1002}

def get_chapter_html(chapter_item):
    soup = BeautifulSoup(chapter_item.get_content(), 'html.parser')

    # Optional: Remove existing <h2> or <h1> titles inside EPUB content
    for tag in soup.find_all(['h1', 'h2']):
        tag.decompose()

    return soup.prettify()

@app.route("/")
def index():
    if os.path.exists(RANGE_FILE):
        with open(RANGE_FILE, 'r') as f:
            last_range = json.load(f)
    else:
        last_range = DEFAULT_RANGE

    cached_path = os.path.join(CACHE_DIR, 'multi_chap.html')
    cached_content = ""
    if os.path.exists(cached_path):
        with open(cached_path, 'r') as f:
            cached_content = f.read()

    return render_template_string("""
        <form action="/load-range" method="get">
            From: <input type="number" name="from_chap" value="{{ from_chap }}">
            To: <input type="number" name="to_chap" value="{{ to_chap }}">
            <button type="submit">Load Chapters</button>
        </form>
        <hr>
        {{ content | safe }}
    """, from_chap=last_range['from'], to_chap=last_range['to'], content=cached_content)


@app.route("/chapter/<int:chapter_id>")
def chapter(chapter_id):
    if chapter_id >= len(chapter_items):
        return "Chapter not found", 404

    chap_num = chapter_id + CHAPTER_OFFSET
    chap_html = get_chapter_html(chapter_items[chapter_id])

    prev_link = f"/chapter/{chapter_id - 1}" if chapter_id > REAL_CHAPTER_START_INDEX else None
    next_link = f"/chapter/{chapter_id + 1}" if chapter_id + 1 < len(chapter_items) else None

    return render_template_string("""
        <p>
            {% if prev_link %}<a href="{{ prev_link }}">&laquo; Previous</a>{% endif %}
            {% if next_link %}<a href="{{ next_link }}" style="float:right">Next &raquo;</a>{% endif %}
        </p>
        <h2>Chapter {{ chap_num }}</h2>
        <div>{{ chap_html|safe }}</div>
    """, prev_link=prev_link, next_link=next_link, chap_num=chap_num, chap_html=chap_html)


@app.route("/load-range")
def load_range():
    try:
        from_chap = int(request.args.get("from_chap", 1001))
        to_chap = int(request.args.get("to_chap", 1002))
    except ValueError:
        return "Invalid chapter numbers."

    # Save range
    with open(RANGE_FILE, 'w') as f:
        json.dump({'from': from_chap, 'to': to_chap}, f)

    content = ""
    for chap_num in range(from_chap, to_chap + 1):
        chap_id = chap_num - CHAPTER_OFFSET
        if 0 <= chap_id < len(chapter_items):
            chapter_html = get_chapter_html(chapter_items[chap_id])
            content += f"<h2>Chapter {chap_num}</h2>\n<div>{chapter_html}</div><hr>"

    # Cache the range
    with open(os.path.join(CACHE_DIR, 'multi_chap.html'), 'w') as f:
        f.write(content)

    return redirect("/")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)