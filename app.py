from flask import Flask, render_template_string, request, redirect
import os
import json
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

app = Flask(__name__)

# Load the EPUB file
book = epub.read_epub('shadow_slave.epub')

# Extract valid chapter documents (those that start with Chapter NNNN)
chapter_items = []
for item in book.items:
    if item.get_type() == ITEM_DOCUMENT:
        content = item.get_content().decode(errors='ignore')
        if 'Chapter ' in content:
            chapter_items.append(item)

# Cache setup
CACHE_DIR = 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)
RANGE_FILE = os.path.join(CACHE_DIR, 'range.json')
DEFAULT_RANGE = {'from': 1001, 'to': 1002}

# Map visible chapter numbers to actual index
chapter_map = {}
for idx, item in enumerate(chapter_items):
    content = item.get_content().decode(errors='ignore')
    soup = BeautifulSoup(content, 'html.parser')
    headings = soup.find_all(['h1', 'h2'])
    for tag in headings:
        text = tag.get_text()
        if text.strip().lower().startswith("chapter"):
            try:
                number = int(''.join(filter(str.isdigit, text.split()[1])))
                chapter_map[number] = idx
            except:
                continue

sorted_chapters = sorted(chapter_map.items())


def get_chapter_html(chapter_item):
    soup = BeautifulSoup(chapter_item.get_content(), 'html.parser')
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
        if chap_num in chapter_map:
            chapter_html = get_chapter_html(chapter_items[chapter_map[chap_num]])
            content += f"<div>{chapter_html}</div><hr>"

    # Cache the rendered HTML
    with open(os.path.join(CACHE_DIR, 'multi_chap.html'), 'w') as f:
        f.write(content)

    return redirect("/")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
