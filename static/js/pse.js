function _pse(id) {
    let elem = document.getElementById(id);
    let searchBox = document.createElement('input');
    searchBox.setAttribute('type', 'text');
    searchBox.setAttribute('placeholder', 'Search this site...');
    let searchButton = document.createElement('button');
    searchButton.setAttribute('type', 'button');
    searchButton.addEventListener("click", async function () {
        let box = open("about:blank", "results", "width=800,height=600");
        let search = searchBox.value;
        let url = "https://w.xrch.rf.gd/api?q=" + encodeURIComponent(`site:${location.hostname} `) + encodeURIComponent(search);
        let resp = await fetch(url);
        let data = await resp.json();
        box.document.body.appendChild((() => { x = document.createElement("title"); x.textContent = "Search Results"; return x })());
        box.document.body.appendChild((() => { x = document.createElement("style"); x.textContent = "body{font-family:sans-serif;}"; return x })());
        box.document.body.appendChild((() => { x = document.createElement("h1"); x.textContent = "Search Results"; return x })());
        for (const result of data.results) {
            let a = document.createElement('a');
            a.setAttribute('href', result.url);
            a.setAttribute('target', '_blank')
            a.innerText = result.title;
            box.document.body.appendChild(a);
            box.document.body.appendChild(document.createElement("br"));
        }
    });
    searchButton.innerHTML = 'Search';
    elem.appendChild(searchBox);
    elem.appendChild(searchButton);
}