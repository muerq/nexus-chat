# ============================================================
# NEXUS SOCIAL NETWORK -> CHAT VERSION (PYTHON SINGLE FILE)
# ============================================================
# FEATURES:
# - FastAPI backend
# - WebSocket realtime chats
# - Chat rooms
# - Private messaging (simple)
# - Users + login
# - Simple frontend
# - In-memory DB
# ============================================================

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# DATABASE
# ============================================================

db = {
    "users": [],
    "sessions": {},
    "rooms": [
        {"id": "general", "name": "General"},
        {"id": "gaming", "name": "Gaming"},
        {"id": "random", "name": "Random"}
    ],
    "messages": []
}

# ============================================================
# HELPERS
# ============================================================

def token():
    return str(uuid.uuid4())

def get_user(t):
    uid = db["sessions"].get(t)
    for u in db["users"]:
        if u["id"] == uid:
            return u
    return None

# ============================================================
# AUTH
# ============================================================

@app.post("/register")
def register(data: dict):
    user = {
        "id": str(uuid.uuid4()),
        "username": data["username"],
        "created": time.time()
    }
    db["users"].append(user)
    return user

@app.post("/login")
def login(data: dict):
    for u in db["users"]:
        if u["username"] == data["username"]:
            t = token()
            db["sessions"][t] = u["id"]
            return {"token": t, "user": u}
    return {"error": "no user"}

# ============================================================
# ROOMS
# ============================================================

@app.get("/rooms")
def rooms():
    return db["rooms"]

# ============================================================
# MESSAGES
# ============================================================

@app.get("/messages/{room_id}")
def get_messages(room_id: str):
    return [m for m in db["messages"] if m["room"] == room_id]

# ============================================================
# WEBSOCKET MANAGER
# ============================================================

class Manager:
    def __init__(self):
        self.connections = []

    async def connect(self, ws):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, msg):
        dead = []
        for c in self.connections:
            try:
                await c.send_text(json.dumps(msg))
            except:
                dead.append(c)
        for d in dead:
            self.disconnect(d)

manager = Manager()

# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await manager.connect(ws)

    try:
        while True:
            data = json.loads(await ws.receive_text())

            if data["type"] == "message":
                msg = {
                    "id": str(uuid.uuid4()),
                    "room": data["room"],
                    "user": data["user"],
                    "text": data["text"],
                    "time": time.time()
                }

                db["messages"].append(msg)

                await manager.broadcast({
                    "type": "message",
                    "data": msg
                })

            if data["type"] == "join":
                await manager.broadcast({
                    "type": "system",
                    "text": f"{data['user']} joined {data['room']}"
                })

    except WebSocketDisconnect:
        manager.disconnect(ws)

# ============================================================
# FRONTEND
# ============================================================

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Nexus Chat</title>
<style>
body{margin:0;font-family:Arial;background:#111;color:white;display:flex;height:100vh}
#sidebar{width:200px;background:#222;padding:10px}
#chat{flex:1;display:flex;flex-direction:column}
#messages{flex:1;overflow:auto;padding:10px}
.msg{background:#333;margin:5px;padding:5px;border-radius:5px}
.room{padding:5px;cursor:pointer}
.room:hover{background:#444}
input{width:100%;padding:10px}
button{padding:10px}
#bottom{display:flex}
</style>
</head>
<body>

<div id="sidebar"></div>

<div id="chat">
<div id="messages"></div>
<div id="bottom">
<input id="text" placeholder="message" />
<button onclick="send()">send</button>
</div>
</div>

<script>
let ws=new WebSocket("ws://"+location.host+"/ws")
let user="user"+Math.random()
let room="general"

ws.onmessage=e=>{
let d=JSON.parse(e.data)
if(d.type=="message"){
let m=document.createElement("div")
m.className="msg"
m.innerText=d.data.user+": "+d.data.text
messages.appendChild(m)
}
}

async function loadRooms(){
let r=await fetch("/rooms")
let rooms=await r.json()

let s=document.getElementById("sidebar")
rooms.forEach(rm=>{
let div=document.createElement("div")
div.className="room"
div.innerText=rm.name

div.onclick=()=>{
room=rm.id
messages.innerHTML=""
ws.send(JSON.stringify({type:"join",user,room}))
}

s.appendChild(div)
})
}

function send(){
ws.send(JSON.stringify({type:"message",user,room,text:text.value}))
text.value=""
}

loadRooms()
</script>

</body>
</html>
"""

@app.get("/")
def home():
    return HTMLResponse(HTML)

# ============================================================
# RUN
# uvicorn main:app --ho
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)