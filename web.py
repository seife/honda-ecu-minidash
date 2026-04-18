import os
import time
import json
import g_vars as G

# from ahttpserver import HTTPResponse, HTTPServer, sendfile
# app = HTTPServer()

from phew import server

server.logging.log_file = "/ramdisk/log.txt"
server.logging.set_truncate_thresholds(2048, 1024)

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
        except Exception as e:
            if name == "ramdisk" and path == "/":
                is_dir = True
            else:
                is_dir = False
            size = 0
        out.append((name, is_dir, size))
    out.sort(key=lambda x: (not x[1], x[0].lower()))
    return out


@server.route("/", methods=["GET"])
def root(request):
    state = G.state
    resp = HEAD_TMPL
    resp += """
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
        lines.push(k + ':')
        for (const l in json[k]){
          lines.push('=> ' + l + ': ' + json[k][l]);
        }
      }
      document.getElementById('status').textContent = lines.join('\\n');
    }catch(e){
      console.error('update failed', e);
      document.getElementById('status').textContent = 'Error';
    }
  }

  updateStatus();
  setInterval(updateStatus, 5000);
</script>
<p>Links:<br><a href="/settings">Settings</a><br><a href="/browse"</a>File Browser</a>
</body></html>
    """
    return resp, 200, "text/html"


@server.route("/api/status", methods=["GET"])
def get_data(request):
    # xxx = {"conn": True, "rpm": 2345, "ect": 53, "iat": 18, "bat": 13.9, "kmh": 66, "inj": 1234, "fuel": 1234213421}
    # resp = {"state": xxx, "stats": G.stats, "time": {"now": time.time()}}
    resp = {"state": G.state, "stats": G.stats, "time": {"now": time.time()}}
    return json.dumps(resp), 200, "application/json"


@server.route("/settings", methods=["GET", "POST"])
def settings(request):
    fuel = 0
    if "fuel" in G.stats:
        fuel = G.stats["fuel"]
    if request.method == "POST":
        resp = ""
        form = request.form
        if "_reset" in form and form["_reset"] == "1":
            G.stats["update"] = True
            G.stats["fuel"] = 0
        if "_liter" in form and form["_liter"]:
            G.stats["liter"] = form["_liter"]
            G.state["oldfuel"] = fuel
        resp += "form: " + json.dumps(request.form) + "\n"
        return resp, 200, "text/plain"
    # rquests.method == GET
    resp = HEAD_TMPL
    resp += """
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
    <button type="submit">Save</button>
  </form>
</body>
</html>
"""
    return resp, 200, "text/html"


@server.route("/browse", methods=["GET"])
def browse(request):
    try:
        path = request.query["path"]
    except:
        path = ""
    if "file" in request.query:
        file = request.query["file"]
        if "/secrets.py" in file:
            return "Forbidden\n", 403
        try:
            with open(file) as f:
                resp = f.read()
            return resp, 200, "text/plain"
        except Exception as e:
            return f"{e}\n", 500, "text/plain"
    # print("path", path)
    ls = list_dir(path)
    # print("ls", json.dumps(ls))
    resp = HEAD_TMPL
    resp += """
<body>
  <h1>File Browser</h1>
  <h2><a href="/">Home</a><br></h2>
  <table>
    <tr><td><b>Name</b></td><td><b>Size</b></td></tr>
"""
    if path:
        np = path.rsplit("/", 1)[0]
        resp += f'    <tr><td><a href="/browse?path={np}">..</a></td><td>[Up]</td></tr>\n'
    for i in ls:
        resp += "    <tr><td>"
        if i[1]:
            resp += f'<a href="/browse?path={path}/{i[0]}">{i[0]}/</a></td><td>[DIR]</td></tr>\n'
        else:
            resp += f'<a href="/browse?file={path}/{i[0]}">{i[0]}</a></td><td>{i[2]}</td></tr>\n'
    resp += "  </table>\n</body>\n</html>\n"
    # print(resp)
    return resp, 200, "text/html"


@server.route("/generate_204", methods=["GET"])
def gen_204(request):
    return "", 204


# catchall example
@server.catchall()
def catchall(request):
    return "Not found", 404
