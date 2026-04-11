#!/usr/bin/env node
"use strict";

const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const PORT = Number(process.env.WATCH_PARTY_PORT || process.env.PORT || 8789);
const VIDEO_DIRS = [path.join(ROOT, ".videos_local"), path.join(ROOT, "videos_local")];
const VIDEO_EXTENSIONS = new Set([".mp4", ".m4v", ".webm", ".ogv", ".mov"]);
const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".avif": "image/avif",
  ".svg": "image/svg+xml",
  ".mp4": "video/mp4",
  ".m4v": "video/mp4",
  ".webm": "video/webm",
  ".ogv": "video/ogg",
  ".mov": "video/quicktime",
};

const rooms = new Map();

function safeJoin(root, requestPath) {
  const decoded = decodeURIComponent(requestPath);
  const joined = path.normalize(path.join(root, decoded));
  return joined.startsWith(root) ? joined : null;
}

function listVideos() {
  const items = [];
  for (const dir of VIDEO_DIRS) {
    if (!fs.existsSync(dir)) continue;
    for (const name of fs.readdirSync(dir)) {
      const full = path.join(dir, name);
      const stat = fs.statSync(full);
      if (!stat.isFile() || !VIDEO_EXTENSIONS.has(path.extname(name).toLowerCase())) continue;
      items.push({
        id: name,
        name,
        url: `/watch-party-video/${encodeURIComponent(name)}`,
        size: stat.size,
      });
    }
  }
  return items.sort((a, b) => a.name.localeCompare(b.name));
}

function findVideo(name) {
  const safeName = path.basename(String(name || ""));
  if (!safeName || safeName !== name) return null;
  for (const dir of VIDEO_DIRS) {
    const full = path.join(dir, safeName);
    if (fs.existsSync(full) && fs.statSync(full).isFile()) return full;
  }
  return null;
}

function sendJson(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(data),
    "Cache-Control": "no-store",
  });
  res.end(data);
}

function serveVideo(req, res, name) {
  const file = findVideo(name);
  if (!file) {
    sendJson(res, 404, { error: "Video not found" });
    return;
  }
  const stat = fs.statSync(file);
  const ext = path.extname(file).toLowerCase();
  const range = req.headers.range;
  if (!range) {
    res.writeHead(200, {
      "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
      "Content-Length": stat.size,
      "Accept-Ranges": "bytes",
      "Cache-Control": "no-store",
    });
    fs.createReadStream(file).pipe(res);
    return;
  }

  const match = range.match(/bytes=(\d*)-(\d*)/);
  const start = match && match[1] ? Number(match[1]) : 0;
  const end = match && match[2] ? Number(match[2]) : stat.size - 1;
  if (start >= stat.size || end >= stat.size || start > end) {
    res.writeHead(416, { "Content-Range": `bytes */${stat.size}` });
    res.end();
    return;
  }
  res.writeHead(206, {
    "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
    "Content-Length": end - start + 1,
    "Content-Range": `bytes ${start}-${end}/${stat.size}`,
    "Accept-Ranges": "bytes",
    "Cache-Control": "no-store",
  });
  fs.createReadStream(file, { start, end }).pipe(res);
}

function serveStatic(req, res, pathname) {
  const filePath = safeJoin(ROOT, pathname === "/" ? "/web/heated-rivalry.html" : pathname);
  if (!filePath || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    sendJson(res, 404, { error: "Not found" });
    return;
  }
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, {
    "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
    "Cache-Control": ext === ".html" ? "no-store" : "public, max-age=60",
  });
  fs.createReadStream(filePath).pipe(res);
}

function encodeFrame(payload) {
  const data = Buffer.from(JSON.stringify(payload));
  if (data.length < 126) return Buffer.concat([Buffer.from([0x81, data.length]), data]);
  if (data.length < 65536) {
    const header = Buffer.alloc(4);
    header[0] = 0x81;
    header[1] = 126;
    header.writeUInt16BE(data.length, 2);
    return Buffer.concat([header, data]);
  }
  const header = Buffer.alloc(10);
  header[0] = 0x81;
  header[1] = 127;
  header.writeBigUInt64BE(BigInt(data.length), 2);
  return Buffer.concat([header, data]);
}

function decodeFrame(buffer) {
  if (buffer.length < 2) return null;
  const opcode = buffer[0] & 0x0f;
  if (opcode === 0x8) return { close: true };
  if (opcode !== 0x1) return null;
  let offset = 2;
  let length = buffer[1] & 0x7f;
  if (length === 126) {
    length = buffer.readUInt16BE(offset);
    offset += 2;
  } else if (length === 127) {
    length = Number(buffer.readBigUInt64BE(offset));
    offset += 8;
  }
  const masked = Boolean(buffer[1] & 0x80);
  const mask = masked ? buffer.subarray(offset, offset + 4) : null;
  if (masked) offset += 4;
  const data = buffer.subarray(offset, offset + length);
  const out = Buffer.alloc(data.length);
  for (let i = 0; i < data.length; i++) out[i] = masked ? data[i] ^ mask[i % 4] : data[i];
  try {
    return JSON.parse(out.toString("utf8"));
  } catch (_) {
    return null;
  }
}

function roomFor(name) {
  const roomName = String(name || "default").trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "-") || "default";
  if (!rooms.has(roomName)) {
    rooms.set(roomName, { name: roomName, clients: new Set(), hostId: "", state: null });
  }
  return rooms.get(roomName);
}

function send(socket, payload) {
  if (socket.destroyed) return;
  socket.write(encodeFrame(payload));
}

function broadcast(room, payload, exceptId = "") {
  for (const client of room.clients) {
    if (client.id !== exceptId) send(client.socket, payload);
  }
}

function handleMessage(client, message) {
  if (!message || typeof message !== "object") return;
  if (message.type === "hello") {
    const room = roomFor(message.room);
    client.room = room;
    client.name = String(message.name || "Guest").slice(0, 80);
    client.role = message.role === "host" ? "host" : "guest";
    room.clients.add(client);
    if (client.role === "host" && !room.hostId) room.hostId = client.id;
    send(client.socket, { type: "joined", clientId: client.id, hostId: room.hostId, room: room.name, state: room.state });
    broadcast(room, { type: "presence", count: room.clients.size, hostId: room.hostId });
    return;
  }
  if (!client.room) return;
  const isHost = client.room.hostId === client.id;
  if (message.type === "state" && isHost) {
    client.room.state = {
      sourceId: message.sourceId || message.videoId || "",
      paused: Boolean(message.paused),
      currentTime: Number(message.currentTime) || 0,
      updatedAt: Date.now(),
    };
    broadcast(client.room, { type: "state", state: client.room.state }, client.id);
  }
}

const server = http.createServer((req, res) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host || "127.0.0.1"}`);
  if (requestUrl.pathname === "/api/watch-party/health") {
    sendJson(res, 200, { ok: true, websocket: "/watch-party-ws" });
    return;
  }
  if (requestUrl.pathname === "/api/watch-party/videos") {
    sendJson(res, 200, { videos: listVideos() });
    return;
  }
  if (requestUrl.pathname.startsWith("/watch-party-video/")) {
    serveVideo(req, res, decodeURIComponent(requestUrl.pathname.replace("/watch-party-video/", "")));
    return;
  }
  serveStatic(req, res, requestUrl.pathname);
});

server.on("upgrade", (req, socket) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host || "127.0.0.1"}`);
  if (requestUrl.pathname !== "/watch-party-ws") {
    socket.destroy();
    return;
  }
  const key = req.headers["sec-websocket-key"];
  if (!key) {
    socket.destroy();
    return;
  }
  const accept = crypto.createHash("sha1").update(`${key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11`).digest("base64");
  socket.write([
    "HTTP/1.1 101 Switching Protocols",
    "Upgrade: websocket",
    "Connection: Upgrade",
    `Sec-WebSocket-Accept: ${accept}`,
    "",
    "",
  ].join("\r\n"));

  const client = { id: crypto.randomUUID(), socket, room: null, role: "guest", name: "Guest" };
  socket.on("data", (buffer) => {
    const message = decodeFrame(buffer);
    if (message?.close) socket.end();
    else handleMessage(client, message);
  });
  socket.on("error", () => {
    socket.destroy();
  });
  socket.on("close", () => {
    if (!client.room) return;
    client.room.clients.delete(client);
    if (client.room.hostId === client.id) client.room.hostId = "";
    broadcast(client.room, { type: "presence", count: client.room.clients.size, hostId: client.room.hostId });
  });
});

server.listen(PORT, () => {
  console.log(`Watch party player server: http://127.0.0.1:${PORT}/web/heated-rivalry.html`);
  console.log(`Local videos: ${VIDEO_DIRS.join(" | ")}`);
});
