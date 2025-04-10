from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import json
import random
import asyncio

app = FastAPI()

with open("commands.json", "r") as f:
    commands = json.load(f)

class Room:
    def init(self, mode, creator_role, difficulty, room_name, password):
        self.mode = mode
        self.players = [(None, creator_role)]  # (websocket, role)
        self.password = password
        self.room_name = room_name
        self.difficulty = difficulty
        self.access_level = 0
        self.data_extracted = 0
        self.system_integrity = 100
        self.lockout_progress = 0
        self.trace_progress = 0
        self.stealth = 100
        self.alert_level = 0
        self.network_status = {"Router": "Secure", "Server": "Secure", "DB": "Secure"}
        self.game_time = 600
        self.timer_task = None
        self.event_task = None
        self.bot_task = None

    async def start_game(self):
        if self.mode == "PvP":
            await self.broadcast(f"Game Started! | PvP: Hacker vs Defender")
        else:
            await self.broadcast(f"Game Started! | Co-op: Team vs Bot ({self.difficulty})")
            self.bot_task = asyncio.create_task(self.bot_action())
        self.timer_task = asyncio.create_task(self.start_timer())
        self.event_task = asyncio.create_task(self.random_events())

    async def start_timer(self):
        while self.game_time > 0 and len([ws for ws, _ in self.players if ws]) >= 2:
            await asyncio.sleep(1)
            self.game_time -= 1
            await self.broadcast(f"Time Left: {self.game_time // 60:02d}:{self.game_time % 60:02d}")
        if self.game_time <= 0 and self.system_integrity > 0:
            await self.broadcast("Defeat: Time's up! Defender/Bot wins!")
            await self.end_game()

    async def random_events(self):
        while len([ws for ws, _ in self.players if ws]) >= 2:
            await asyncio.sleep(random.randint(20, 40))
            event = random.choice([
                "Event: Firewall Alert! Alert +20",
                "Event: Suspicious Activity! Stealth -15",
                "Event: Vulnerability Found! Integrity -20",
                "Chat: [System] Security breach detected!"
            ])
            if "Alert +20" in event: self.alert_level = min(100, self.alert_level + 20)
            elif "Stealth -15" in event: self.stealth = max(0, self.stealth - 15)
            elif "Integrity -20" in event: self.system_integrity = max(0, self.system_integrity - 20)
            await self.broadcast(event)

    async def bot_action(self):
        difficulty_mod = {"Easy": 0.5, "Medium": 1, "Hard": 1.5}.get(self.difficulty, 1)
        bot_role = "defender" if self.players[0][1] == "hacker" else "hacker"
        while len([ws for ws, _ in self.players if ws]) >= 2:
            await asyncio.sleep(random.uniform(5, 10) / difficulty_mod)
            bot_commands = list(commands[bot_role].keys())
            cmd = random.choice(bot_commands)
            if bot_role == "defender":
                if "block" in cmd and self.access_level > 0: self.lockout_progress += int(20 * difficulty_mod)
                elif "firewall" in cmd: self.lockout_progress += int(30 * difficulty_mod); self.network_status["Router"] = "Secure"; self.alert_level += int(10 * difficulty_mod)
                elif "trace" in cmd: self.trace_progress += int(20 * difficulty_mod)
                elif "backdoor" in cmd: self.system_integrity = min(100, self.system_integrity + int(30 * difficulty_mod)); self.network_status["Server"] = "Secure"
                elif "monitor" in cmd: self.alert_level += int(15 * difficulty_mod); self.stealth -= int(10 * difficulty_mod)
            else:
                if "scan" in cmd and self.access_level < 50: self.access_level = 50; self.network_status["Router"] = "Compromised"; self.stealth -= int(10 * difficulty_mod)
                elif "force" in cmd and self.access_level < 100: self.access_level = 100; self.network_status["Server"] = "Compromised"; self.stealth -= int(20 * difficulty_mod)
                elif "data" in cmd and self.access_level > 0: self.data_extracted += int(30 * difficulty_mod); self.network_status["DB"] = "Compromised"; self.stealth -= int(10 * difficulty_mod)
                elif "ransom" in cmd and self.access_level == 100: self.system_integrity = 0
                elif "spoof" in cmd or "cloak" in cmd: self.stealth = min(100, self.stealth + int(20 * difficulty_mod))
            self.alert_level += int(5 * difficulty_mod)
            await self.broadcast(f"Bot {bot_role.capitalize()}: {commands[bot_role][cmd]['description']}")
            if self.check_win_conditions():
                await self.end_game()

    async def broadcast(self, message):
        status = f"| Access: {self.access_level} | Data: {self.data_extracted} | Integrity: {self.system_integrity} | Stealth: {self.stealth} | Lockout: {self.lockout_progress} | Trace: {self.trace_progress} | Alert: {self.alert_level} | Router: {self.network_status['Router']} | Server: {self.network_status['Server']} | DB: {self.network_status['DB']}"
        for ws, _ in self.players:
            if ws and ws.open:
                await ws.send_text(message + status)

    def check_win_conditions(self):
        if self.mode == "PvP":
            if self.system_integrity == 0 or (self.data_extracted >= 100 and self.access_level == 100):
                asyncio.create_task(self.broadcast("Victory: System compromised! Hacker wins!"))
                return True
            elif self.lockout_progress >= 100 and self.trace_progress >= 100:
                asyncio.create_task(self.broadcast("Victory: Hacker locked out and traced! Defender wins!"))
                return True
        elif self.mode == "Co-op":
            if self.players[0][1] == "hacker":
                if self.system_integrity == 0 or (self.data_extracted >= 100 and self.access_level == 100):
                    asyncio.create_task(self.broadcast("Victory: System compromised! Hackers win!"))
                    return True
                elif self.lockout_progress >= 100 and self.trace_progress >= 100:
                    asyncio.create_task(self.broadcast("Defeat: Bot locked you out and traced you!"))
                    return True
            else:
                if self.system_integrity == 0 or (self.data_extracted >= 100 and self.access_level == 100):
                    asyncio.create_task(self.broadcast("Defeat: Bot compromised the system!"))
                    return True
                elif self.lockout_progress >= 100 and self.trace_progress >= 100:
                    asyncio.create_task(self.broadcast("Victory: Bot locked out and traced!"))
                    return True
        return False

    async def end_game(self):
        for ws, _ in self.players:
            if ws:
                await ws.close()
        if self.timer_task:
            self.timer_task.cancel()
        if self.event_task:
            self.event_task.cancel()
        if self.bot_task:
            self.bot_task.cancel()
        rooms[self.room_name] = None

rooms = {}

@app.get("/")
async def get():
    return HTMLResponse("<h1>Hacker vs Defender Server</h1>")

@app.websocket("/game")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        parts = data.split(":")
        if parts[0] == "create":
            _, mode, role, difficulty, room_name, password = parts
            if room_name in rooms and rooms[room_name]:
                await websocket.send_text("Error: Room already exists")
                await websocket.close()
                return
            rooms[room_name] = Room(mode, role, difficulty, room_name, password)
            rooms[room_name].players[0] = (websocket, role)
            await websocket.send_text(f"Room created: {room_name} | Waiting for second player...")
        elif parts[0] == "join":
            _, room_name, password = parts
            if room_name not in rooms or not rooms[room_name] or rooms[room_name].password != password:
                await websocket.send_text("Error: Invalid room name or password")
                await websocket.close()
                return
            room = rooms[room_name]
            if len([ws for ws, _ in room.players if ws]) >= 2:
                await websocket.send_text("Error: Room is full")
                await websocket.close()
                return
            creator_role = room.players[0][1]
            joiner_role = "defender" if creator_role == "hacker" else "hacker"
            room.players.append((websocket, joiner_role))
            await websocket.send_text(f"Role assigned: {joiner_role}")
            await room.players[0][0].send_text(f"Game Started | {room.mode}")
            await room.start_game()
        else:
            await websocket.send_text("Error: Invalid request")
            await websocket.close()
            return

        room = rooms[room_name]
        role = next(r for ws, r in room.players if ws == websocket)
        while True:
            data = await websocket.receive_text()
            if room.mode == "Co-op" and data.startswith("chat:"):
                _, sender_role, message = data.split(":", 2)
                if sender_role == role:
                    await room.broadcast(f"Chat: [{role.capitalize()}] {message}")
            elif data in commands[role]:
                response = f"Response: {commands[role][data]['description']}"
                if role == "hacker":
                    if "scan" in data and room.access_level < 50: room.access_level = 50; room.stealth -= 10; room.network_status["Router"] = "Compromised"
                    elif "force" in data and room.access_level < 100: room.access_level = 100; room.stealth -= 20; room.network_status["Server"] = "Compromised"
                    elif "data" in data and room.access_level > 0: room.data_extracted += 30; room.stealth -= 10; room.network_status["DB"] = "Compromised"
                    elif "ransom" in data and room.access_level == 100: room.system_integrity = 0
                    elif "spoof" in data or "cloak" in data: room.stealth = min(100, room.stealth + 20)
                    room.alert_level = min(100, room.alert_level + 5)
                else:
                    if "block" in data and room.access_level > 0: room.lockout_progress += 20
                    elif "firewall" in data: room.lockout_progress += 30; room.alert_level += 10; room.network_status["Router"] = "Secure"
                    elif "trace" in data and room.alert_level > 50: room.trace_progress += 20
                    elif "backdoor" in data and room.system_integrity < 100: room.system_integrity = min(100, room.system_integrity + 30); room.network_status["Server"] = "Secure"
                    elif "monitor" in data: room.alert_level += 15; room.stealth -= 10
                await room.broadcast(response)
                if room.check_win_conditions():
                    await room.end_game()
            elif data == "map":
                await websocket.send_text(f"[NETWORK]\n[Router: {room.network_status['Router']}] --> [Server: {room.network_status['Server']}] --> [DB: {room.network_status['DB']}]")
            elif data == "clear":
                await websocket.send_text("clear")
            elif data == "whoami":
                await websocket.send_text(f"You are the {role.capitalize()}")
            elif data == "status":
                await websocket.send_text(f"Status: | Access: {room.access_level} | Data: {room.data_extracted} | Integrity: {room.system_integrity} | Stealth: {room.stealth} | Lockout: {room.lockout_progress} | Trace: {room.trace_progress} | Alert: {room.alert_level}")
            else:
                await websocket.send_text(f"Error: Unknown command '{data}'")

    except WebSocketDisconnect:
        if room_name in rooms and rooms[room_name]:
            room = rooms[room_name]
            room.players = [(ws, r) for ws, r in room.players if ws != websocket]
            if len([ws for ws, _ in room.players if ws]) < 2:
                await room.broadcast("Player disconnected! Game aborted.")
                await room.end_game()
                rooms[room_name] = None
        print(f"Player disconnected from {room_name}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)