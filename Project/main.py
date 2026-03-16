from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except: pass

manager = ConnectionManager()

html_content = """
<!DOCTYPE html>
<html>
    <head>
        <title>VIRUS CQC Log Monitor</title>
        <style>
            body { background-color: #1a1a1a; color: #eee; font-family: 'Consolas', monospace; margin: 0; padding: 20px; }
            header { border-bottom: 2px solid #333; margin-bottom: 20px; padding-bottom: 10px; display: flex; justify-content: space-between; }
            .log-section { background-color: #252525; border: 1px solid #444; border-radius: 8px; padding: 20px; height: 80vh; display: flex; flex-direction: column; }
            #log-container { flex-grow: 1; overflow-y: auto; line-height: 1.8; font-size: 16px; }
            .log-entry { border-bottom: 1px solid #333; padding: 8px 0; animation: fadeIn 0.3s; }
            .timestamp { color: #888; margin-right: 15px; font-size: 14px; }
            .status-robot { color: #3498db; }
            .status-door { color: #2ecc71; }
            .status-warn { color: #e74c3c; font-weight: bold; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(-5px); } to { opacity: 1; transform: translateY(0); } }
        </style>
    </head>
    <body>
        <header>
            <h1>System Patrol Monitor</h1>
            <div id="status-dot" style="color: #e74c3c;">● Offline</div>
        </header>
        <div class="log-section">
            <div id="log-container"></div>
        </div>
        <script>
            const ws = new WebSocket("ws://" + window.location.host + "/ws");
            const logBox = document.getElementById('log-container');
            const statusDot = document.getElementById('status-dot');

            ws.onopen = () => {
                statusDot.style.color = "#2ecc71";
                statusDot.innerText = "● Live Connected";
            };

            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    if (data.log) {
                        const entry = document.createElement("div");
                        entry.className = "log-entry";
                        
                        let typeClass = "";
                        if(data.log.includes("🤖")) typeClass = "status-robot";
                        if(data.log.includes("Door")) typeClass = "status-door";
                        if(data.log.includes("⚠️")) typeClass = "status-warn";
                        
                        entry.innerHTML = `<span class="timestamp">[${new Date().toLocaleTimeString()}]</span><span class="${typeClass}">${data.log}</span>`;
                        logBox.prepend(entry);
                        
                        if (logBox.childNodes.length > 100) logBox.removeChild(logBox.lastChild);
                    }
                } catch (e) {}
            };

            ws.onclose = () => {
                statusDot.style.color = "#e74c3c";
                statusDot.innerText = "● Disconnected";
            };
        </script>
    </body>
</html>
"""

@app.get("/")
async def get(): return HTMLResponse(html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=None, ws_ping_timeout=None)