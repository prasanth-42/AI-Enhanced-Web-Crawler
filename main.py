from flask import Flask, render_template, request, jsonify
from backend.scrape import scrape_website, extract_body_content, clean_body_content, split_dom_content
from backend.parse import parse_with_groq
import os

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        description = request.form["description"]
        model = request.form["model"]

        # Scraping
        dom = scrape_website(url)
        body = extract_body_content(dom)
        cleaned = clean_body_content(body)
        chunks = split_dom_content(cleaned)

        # Parsing
        result = parse_with_groq(chunks, description, model)

        return render_template("index.html", result=result, url=url, model=model, description=description)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
