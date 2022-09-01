from flask import *
import requests as rq
from bs4 import BeautifulSoup
from urllib.parse import quote as urlencode, urlparse
import time
import flask_cors as cors
import json
import logging
import wikipedia as wp
from autocorrect import Speller
from simpleeval import simple_eval

log = logging.getLogger('werkzeug')
log.disabled = True


def spell_check(query):
    spell = Speller(lang="en")
    return " ".join(map(spell, query.split(" ")))


headers = {
    "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36"}

app = Flask(__name__)


def favicon(url):
    return f"si?w=" + urlencode(f"https://www.google.com/s2/favicons?domain={urlparse(url).netloc}")


def get_ip(): return json.loads(
    rq.get("https://api.ipify.org/?format=json").text)["ip"]


def get_breadcrumbs(url):
    seperator = " \u203A "
    protocol = url.split("//")[0]
    path_seperator = "/"
    breadcrumbs = (path_seperator.join(
        url.split(path_seperator)[2:]))
    if breadcrumbs[-1] == path_seperator:
        breadcrumbs = breadcrumbs[:-1]
    breadcrumbs = breadcrumbs.replace(path_seperator, seperator)
    return f"{protocol}//{breadcrumbs}"


def get_wikipedia(page):
    try:
        summary = wp.summary(page)
        return {
            "success": True,
            "summary": summary
        }
    except:
        return {
            "success": False
        }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/hq")
def hide_query():
    return redirect(request.args.get("w"))


@app.route("/si")
def secure_image():
    try:
        resp = rq.get(request.args.get("w"))
        return Response(resp.content, content_type=resp.headers["content-type"])
    except:
        logging.error("Image proxy failed")


@app.route("/search_engine.xml")
def search_engine():
    return Response(
        render_template("search_engine.xml", host=request.host),
        mimetype="application/opensearchdescription+xml")


@app.route("/api")
@cors.cross_origin()
def api():
    now = time.time()
    q = request.args.get("q")
    page = 0
    if "p" in request.args:
        page = int(request.args.get("p"))
    page_as_first = page * 10 + 1
    url = f"https://www.bing.com/search?q=%2B{urlencode(q)}&first={page_as_first}"
    res = rq.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    results2 = []
    corrected = spell_check(q)
    misspelled = corrected != q
    for link in soup.find_all("li", class_="b_algo"):
        url = link.find("h2").find("a")
        url = url.get("href")
        title = link.find("h2").text
        try:
            snippet = link.find(
                "div", class_="b_caption").find("p").text
        except (TypeError, AttributeError):
            snippet = "No snippet available."
        results2.append({"url": url, "title": title, "snippet": snippet,
                        "favicon": f"https://www.google.com/s2/favicons?domain={urlparse(url).netloc}"})
    results = [x for x in results2 if not x["url"].startswith(
        "/") ^ x["url"].startswith("//")]
    api_output = {
        "query": q,
        "results": results,
        "time_took": time.time() - now,
        "amount": len(results),
        "sent_via": {
            "ip": get_ip(),
            "location": f"https://codetabs.com/ip-geolocation/ip-geolocation.html?q={get_ip()}"
        },
        "typo": {
            "has_typo": misspelled,
            "corrected": corrected
        },
        "page": {
            "as_bing_first": page_as_first,
            "as_page": page
        }
    }
    wikipedia = get_wikipedia(q)
    if wikipedia["success"]:
        api_output["wikipedia"] = wikipedia["summary"]
    try:
      api_output["calculated"] = simple_eval(q)
    except:
      pass
    return jsonify(api_output)


@app.route("/imageapi")
@cors.cross_origin()
def imageapi():
    now = time.time()
    q = request.args.get("q")
    url = f"https://www.bing.com/images/search?q=%2B{urlencode(q)}&first=1&tsc=ImageHoverTitle"
    res = rq.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    results = []
    for result in soup.find_all("a", class_="iusc"):
        m = json.loads(result["m"])
        murl, turl = m["murl"], m["turl"]
        results.append({"url": murl})
    api_output = {
        "query": q,
        "results": results,
        "time_took": time.time() - now,
        "amount": len(results),
        "sent_via": {
            "ip": get_ip(),
            "location": f"https://codetabs.com/ip-geolocation/ip-geolocation.html?q={get_ip()}"
        }
    }
    return jsonify(api_output)


@app.route("/s")
def search():
    now = time.time()
    q = request.args.get("q")
    calculated = False
    try:
      calculated = simple_eval(q)
    except:
      pass
    page = 0
    if "p" in request.args:
        page = int(request.args.get("p"))
    page_as_first = page * 10 + 1
    url = f"https://www.bing.com/search?q=%2B{urlencode(q)}&first={page_as_first}"
    corrected = spell_check(q)
    misspelled = corrected != q
    res = rq.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    results2 = []
    for link in soup.find_all("li", class_="b_algo"):
        url = link.find("h2").find("a")
        url = url.get("href")
        title = link.find("h2").text
        _favicon = favicon(url)
        breadcrumbs = get_breadcrumbs(url)
        try:
            snippet = link.find(
                "div", class_="b_caption").find("p").text
        except (TypeError, AttributeError):
            snippet = "No snippet available."
        results2.append({"url": f"hq?w={urlencode(url)}", "unsafe_url": url, "favicon_url": _favicon, "title": title,
                         "snippet": snippet, "breadcrumbs": breadcrumbs})
    results = [x for x in results2 if not x["unsafe_url"].startswith(
        "/") ^ x["unsafe_url"].startswith("//")]
    wikipedia = get_wikipedia(q)
    return render_template("search.html", results=results, query=q, results_amount='{:,}'.format(len(results)), time_took=round(time.time() - now, 2), ip=get_ip(), query_encoded=urlencode(q), wikipedia=wikipedia, typo={"has_typo": misspelled, "corrected": corrected, "corrected_encoded": urlencode(corrected)}, page=page, calculated=calculated)


@app.route("/i")
def image_search():
    now = time.time()
    q = request.args.get("q")
    url = f"https://www.bing.com/images/search?q=%2B{urlencode(q)}&first=1&tsc=ImageHoverTitle"
    res = rq.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    results = []
    for result in soup.find_all("a", class_="iusc"):
        m = json.loads(result["m"])
        murl, turl = m["murl"], m["turl"]
        results.append({"url": f"si?w={urlencode(murl)}"})
    truelen = len(results)
    results = [results[i:i+4] for i in range(0, len(results), 4)]
    return render_template("image.html", results=results, query=q, results_amount='{:,}'.format(truelen), time_took=round(time.time() - now, 2), ip=get_ip(), query_encoded=urlencode(q))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/favicon.ico")
def __favicon():
    return send_from_directory(".", "favicon.ico", mimetype="image/vnd.microsoft.icon")


app.run(host="0.0.0.0", port=5000)
