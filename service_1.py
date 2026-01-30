from fastapi import FastAPI
import requests
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/api", response_class=HTMLResponse)
def api():
    r = requests.get("http://192.168.1.5:9000/process")
    return f"""
    <html>
      <body>
        <h2>Server 1 Status: <b>OK</b></h2>
        <p>Server 2 Response: <b>{r.json()['message']}</b></p>
      </body>
    </html>
    """
