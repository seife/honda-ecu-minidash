import os
from time import ticks_ms, ticks_diff
import json
import g_vars as G

# from ahttpserver import HTTPResponse, HTTPServer, sendfile
# app = HTTPServer()

from phew import server

server.logging.set_truncate_thresholds(2048, 1024)
root = ""  # will be set via web.root=... from outside

HEAD_TMPL = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    body { font-family: Arial, sans-serif; padding:20px; }
    form { max-width:420px; }
    label { display:block; margin:12px 0 6px; font-weight:600; }
    input, select { width:100%; padding:8px; box-sizing:border-box; }
    button { margin-top:12px; padding:8px 12px; }
  </style>
  <title>Honda minidash</title>
</head>
"""


# Helpers
def list_dir(path):
    if path == "":
        path = "/"
    try:
        entries = os.listdir(path)
        print("listdir:", entries)
    except Exception as e:
        print(e)
        return []
    out = []
    for name in entries:
        try:
            st = os.stat(f"{path}/{name}")
            is_dir = (st[0] & 0x4000) != 0
            size = st[6]
        except Exception:  # ramdisk mount point does not want to stat?
            if name == "ramdisk" and path == "/":
                is_dir = True
            else:
                is_dir = False
            size = 0
        out.append((name, is_dir, size))
    out.sort(key=lambda x: (not x[1], x[0].lower()))
    return out


def num_from_string(value):
    if isinstance(value, float):
        return value
    if "," in value:
        return float(value.replace(",", ".", 1))  # more than one comma or decimal point is bad anyway...
    return float(value)


@server.route("/", methods=["GET"])
def index(request):
    resp = "".join(
        [
            HEAD_TMPL,
            """
<body>
<h1>Honda ECU minidash</h1>
<pre>
/api/status:
<div id="status">Loading...</div>
</pre>
<script>
  async function updateStatus(){
    try{
      const res = await fetch('/api/status');
      if(!res.ok) throw new Error('HTTP '+res.status);
      //const text = await res.text();
      //document.getElementById('status').textContent = text;
      const json = await res.json();
      const lines = [];
      for (const k in json) {
        lines.push(k + ':');
        // nested keys sorted (if it's an object)
        const v = json[k];
        if (v && typeof v === 'object' && !Array.isArray(v)){
          for (const l of Object.keys(v).sort()){
            lines.push('=> ' + l + ': ' + v[l]);
          }
        } else {
          lines.push('=> ' + String(v));
        }
      }
      document.getElementById('status').textContent = lines.join('\\n');
    }catch(e){
      console.error('update failed', e);
      document.getElementById('status').textContent = 'Error';
    }
  }

  updateStatus();
  setInterval(updateStatus, 2500);
</script>
<p>Links:<br><a href="/settings">Settings</a><br><a href="/browse">File Browser</a>
</body></html>""",
        ]
    )
    return resp, 200, "text/html"


@server.route("/api/status", methods=["GET"])
def get_data(request):
    # xxx = {"conn": True, "rpm": 2345, "ect": 53, "iat": 18, "bat": 13.9, "kmh": 66, "inj": 1234, "fuel": 1234213421}
    # resp = {"state": xxx, "stats": G.stats, "time": {"now": time.time()}}
    state = dict(G.state)  # shallow copy to avoid feeding back changes
    try:
        div = G.stats.get("div", 0)
        if div:  # avoid division by zero, even though this is hardly possible as div is pre-set
            state["liter"] = round(state["fuel"] / div, 3)
        kmh = state.get("kmh", 0)
        if kmh > 0:
            per_h = state.get("per_h", 0)
            state["per_100"] = round(per_h * 100 / kmh, 2)
    except Exception as e:
        print(f"get_data exc {e}")
    now = ticks_ms()
    resp = {
        "state": state,
        "stats": G.stats,
        "time": {"uptime": round(now / 1000, 1), "lastsave": round(ticks_diff(now, G.lastsave) / 1000, 1)},
    }
    return json.dumps(resp), 200, "application/json"


@server.route("/settings", methods=["GET", "POST"])
def settings(request):
    fuel = int(G.stats.get("fuel", 0))
    if request.method == "POST":
        resp = ""
        form = request.form

        fuel_tot = int(G.stats.get("fuel_total", 0))
        if "_reset" in form and form["_reset"] == "1":
            fuel_tot += fuel
            G.stats["fuel_total"] = fuel_tot
            G.stats["fuel"] = 0
            G.stats["km"] = 0
            G.stats["update"] = True
        if "_liter" in form and form["_liter"]:
            try:
                liter = num_from_string(form["_liter"])
                liter_tot = num_from_string(G.stats.get("liter_total", 0))
                liter_tot += liter
                G.stats["liter_total"] = liter_tot
                G.stats["div"] = int(fuel_tot / liter_tot)  # if liter_tot == 0 this will raise an Exception
            except Exception as e:
                resp = f"{e} \n\n"
                if "update" in G.stats:
                    del G.stats["update"]
        if form.get("_reset_all", "") == "YES":
            G.stats["liter_total"] = 0.0
            G.stats["fuel"] = 0
            G.stats["update"] = True

        resp += "form: " + json.dumps(request.form) + "\n"
        return resp, 200, "text/plain"
    # requests.method == GET
    resp = "".join(
        [
            HEAD_TMPL,
            """
<body>
  <h1>Settings</h1>
  <h2><a href="/">Home</a><br></h2>
  <form method="post" action="">
    <label for="_liter">Liter added</label>
    <input id="_liter" name="_liter" type="number" min="0" step="any">
    <label class="checkbox">
      <span>Reset fuel counter</span>
      <input id="_reset" name="_reset" type="checkbox" value="1">
    </label>
    <label for="_reset_all">RESET all fuel statistics (only first run, enter "YES")</label>
    <input id="_reset_all" name="_reset_all" type="text">
    <button type="submit">Save</button>
  </form>
</body>
</html>
""",
        ]
    )
    return resp, 200, "text/html"


@server.route("/browse", methods=["GET"])
def browse(request):
    path = request.query.get("path", "")
    if "file" in request.query:
        file = request.query["file"]
        if "/secrets.py" in file:
            return "Forbidden\n", 403
        try:
            with open(root + file) as f:
                resp = f.read()
            return resp, 200, "text/plain"
        except Exception as e:
            return f"{e}\n", 500, "text/plain"
    # print("path", path)
    # ls = list_dir(root + path)
    # print("ls", json.dumps(ls))

    def generate():
        yield HEAD_TMPL
        yield '<body>\n  <h1>File Browser</h1>\n  <h2><a href="/">Home</a><br></h2>\n'
        yield "  <table>\n    <tr><td><b>Name</b></td><td><b>Size</b></td></tr>\n"
        if path:
            np = path.rsplit("/", 1)[0]
            yield f'    <tr><td><a href="/browse?path={np}">..</a></td><td>[Up]</td></tr>\n'
        for name, is_dir, size in list_dir(root + path):
            if is_dir:
                yield f'    <tr><td><a href="/browse?path={path}/{name}">{name}/</a></td><td>[DIR]</td></tr>\n'
            else:
                yield f'    <tr><td><a href="/browse?file={path}/{name}">{name}</a></td><td>{size}</td></tr>\n'
        yield "  </table>\n</body>\n</html>\n"

    return generate(), 200, "text/html"


@server.route("/generate_204", methods=["GET"])
def gen_204(request):
    return "", 204


# catchall example
@server.catchall()
def catchall(request):
    return "Not found", 404
