import json
import logging as _logging
import random
import socket
import struct
import time
from urllib.parse import quote as urlencode
from urllib.parse import urlparse

import flask_cors as cors
import requests as rq
import wikipedia as wp
from autocorrect import Speller
from bs4 import BeautifulSoup
from flask import *
from simpleeval import simple_eval

log = _logging.getLogger('werkzeug')
log.disabled = True

headers = {
    "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36"}


def generate_ip():
    return socket.inet_ntoa(
        struct.pack('>I', random.randint(0x1c000000, 0x1effffff)))


def ip_headers(generated_ip):
    return {
        "X-Originating-IP": generated_ip,
        "X-Forwarded-For": generated_ip,
        "X-Remote-IP": generated_ip,
        "X-Remote-Addr": generated_ip,
        "X-Client-IP": generated_ip,
        "X-Host": generated_ip,
        "X-Forwarded-Host": generated_ip
    }


def tineye(imageFile):
    generated_ip = generate_ip()
    _headers = {**headers, **ip_headers(generated_ip)}
    r = rq.post(
        "https://tineye.com/result_json/?sort=score&order=desc", headers=_headers, files={"image": imageFile})
    return (r.json(), generated_ip)


def spell_check(query):
    spell = Speller(lang="en")
    return " ".join(map(spell, query.split(" ")))


app = Flask(__name__)


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


@app.route("/hide_referrer")
def hide_referrer():
    return redirect(request.args["goto"])


@app.route("/secure_image")
def secure_image():
    try:
        resp = rq.get(request.args["source"])
        return Response(resp.content, content_type=resp.headers["content-type"])
    except:
        return Response(open("static/assets/no_image.png", "rb").read(), content_type="image/png")


@app.route("/web")
@cors.cross_origin()
def api():
    _headers = {**headers, **ip_headers(generate_ip())}
    now = time.time()
    q = request.args["query"]
    page = 0
    if "page" in request.args:
        page = int(request.args["page"])
    page_as_first = page * 10 + 1
    url = f"https://www.bing.com/search?q=%2B{urlencode(q)}&first={page_as_first}"
    res = rq.get(url, headers=_headers)
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
        "time_took": round(time.time() - now, 3),
        "amount": len(results),
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


@app.route("/images")
@cors.cross_origin()
def imageapi():
    _headers = {**headers, **ip_headers(generate_ip())}
    now = time.time()
    q = request.args.get("query")
    url = f"https://www.bing.com/images/search?q=%2B{urlencode(q)}&qft="
    filters = ["imagesize", "color2", "photo", "aspect", "face", "license"]
    for filter in filters:
        fv = request.args.get(filter)
        if fv:
            url += f"+filterui:{filter}-{fv}"
    res = rq.get(url, headers=_headers)
    soup = BeautifulSoup(res.text, "html.parser")
    results = []
    for result in soup.find_all("a", class_="iusc"):
        m = json.loads(result["m"])
        murl, turl = m["murl"], m["turl"]
        results.append({"url": murl})
    api_output = {
        "query": q,
        "results": results,
        "time_took": round(time.time() - now, 3),
        "amount": len(results),
    }
    return jsonify(api_output)


@app.route("/reverse_image", methods=["POST"])
@cors.cross_origin()
def reverse_image_search_api():
    now = time.time()
    f = request.files["image"]
    api, ip_address = tineye(f)
    if not api.get("matches"):
        return jsonify({
            "results": [],
            "time_took": time.time() - now,
            "amount": 0,
            "sent_via": {
                "ip": ip_address,
                "location": f"https://codetabs.com/ip-geolocation/ip-geolocation.html?q={ip_address}"
            }
        })
    results2 = [{"url": i['domains'][0]['backlinks'][0]['url']}
                for i in api["matches"]]
    results = []
    for result in results2:
        if result["url"]:
            results.append(result)
    api_output = {
        "results": results,
        "time_took": round(time.time() - now, 3),
        "amount": len(results),
    }
    return jsonify(api_output)


app.run(host="0.0.0.0", port=5000)
