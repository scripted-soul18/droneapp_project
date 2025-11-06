require('dotenv').config();
const express = require('express');
const http = require('http');
const mongoose = require('mongoose');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const { Server } = require('socket.io');

const app = express();
app.use(express.json());
app.use(cors());

// Models (simple, extend as needed)
const userSchema = new mongoose.Schema({
  username: { type: String, unique: true },
  passwordHash: String,
  role: { type: String, default: 'operator' }
});
const telemetrySchema = new mongoose.Schema({
  droneId: String,
  timestamp: { type: Date, default: Date.now },
  location: { lat: Number, lon: Number, alt: Number },
  battery: Number,
  meta: mongoose.Schema.Types.Mixed
});
const missionSchema = new mongoose.Schema({
  name: String,
  droneId: String,
  waypoints: [mongoose.Schema.Types.Mixed],
  status: String,
  createdAt: { type: Date, default: Date.now }
});

const User = mongoose.model('User', userSchema);
const Telemetry = mongoose.model('Telemetry', telemetrySchema);
const Mission = mongoose.model('Mission', missionSchema);

// Connect to MongoDB
const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/drone-backend';
mongoose.connect(MONGO_URI).then(() => {
  console.log('Connected to MongoDB');
}).catch(err => {
  console.error('MongoDB connection error:', err);
});

// JWT helpers
const jwtSecret = process.env.JWT_SECRET || 'dev_secret';
function authMiddleware(req, res, next) {
  const auth = req.headers.authorization;
  if (!auth) return res.status(401).json({ error: 'Missing auth' });
  const token = auth.split(' ')[1];
  try {
    const payload = jwt.verify(token, jwtSecret);
    req.user = payload;
    next();
  } catch (e) {
    return res.status(401).json({ error: 'Invalid token' });
  }
}

// REST endpoints
app.post('/api/register', async (req, res) => {
  const { username, password } = req.body;
  const passwordHash = await bcrypt.hash(password, 10);
  try {
    const user = new User({ username, passwordHash });
    await user.save();
    res.json({ ok: true });
  } catch (e) {
    res.status(400).json({ error: 'Registration failed', details: e.message });
  }
});

app.post('/api/login', async (req, res) => {
  const { username, password } = req.body;
  const user = await User.findOne({ username });
  if (!user) return res.status(400).json({ error: 'Invalid credentials' });
  const ok = await bcrypt.compare(password, user.passwordHash);
  if (!ok) return res.status(400).json({ error: 'Invalid credentials' });
  const token = jwt.sign({ id: user._id, username: user.username, role: user.role }, jwtSecret, { expiresIn: '12h' });
  res.json({ token });
});

// Store telemetry by REST (optional)
app.post('/api/telemetry', authMiddleware, async (req, res) => {
  const data = req.body;
  const t = new Telemetry(data);
  await t.save();
  res.json({ ok: true, id: t._id });
});

// Query stored telemetry
app.get('/api/telemetry/:droneId', authMiddleware, async (req, res) => {
  const { droneId } = req.params;
  const items = await Telemetry.find({ droneId }).sort({ timestamp: -1 }).limit(200);
  res.json(items);
});

// Missions
app.post('/api/missions', authMiddleware, async (req, res) => {
  const m = new Mission(req.body);
  await m.save();
  res.json(m);
});
app.get('/api/missions', authMiddleware, async (req, res) => {
  const items = await Mission.find().sort({ createdAt: -1 }).limit(100);
  res.json(items);
});

// HTTP server + Socket.IO
const httpServer = http.createServer(app);
const io = new Server(httpServer, {
  cors: { origin: '*' }
});

// Simple auth for sockets using JWT
io.use((socket, next) => {
  const token = socket.handshake.auth?.token;
  if (!token) return next(new Error('Auth error'));
  try {
    const payload = jwt.verify(token, jwtSecret);
    socket.user = payload;
    next();
  } catch (e) {
    next(new Error('Auth error'));
  }
});

io.on('connection', (socket) => {
  console.log('Socket connected', socket.id, 'user', socket.user?.username);

  // Drones should join room named by their droneId, e.g., 'drone:DRONE123'
  socket.on('join:drone', (droneId) => {
    socket.join(`drone:${droneId}`);
    console.log(`${socket.id} joined drone:${droneId}`);
  });

  // Drone sends telemetry via socket event
  socket.on('telemetry', async (payload) => {
    // payload should include droneId, location, battery, etc.
    // Broadcast to clients listening to this drone
    if (!payload?.droneId) return;
    io.to(`drone:${payload.droneId}`).emit('telemetry:update', payload);

    // Optionally persist telemetry
    const t = new Telemetry(payload);
    t.save().catch(err => console.error('Save telemetry error', err));
  });

  // Operator sends control commands to drone
  socket.on('control', (cmd) => {
    // cmd: { droneId, action, params }
    if (!cmd?.droneId) return;
    // Forward to drone room; drones listening can handle control messages
    io.to(`drone:${cmd.droneId}`).emit('control:cmd', cmd);
  });

  socket.on('disconnect', () => {
    console.log('Socket disconnected', socket.id);
  });
});

const PORT = process.env.PORT || 3000;
httpServer.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});