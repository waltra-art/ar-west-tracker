# AR West Tracker - Shared Server

🔒 **SECURED** - API Key Required

A Flask server deployed on **Render.com** that enables multiple users to share AR West Tracker data in real-time.

## Security

Access requires a valid API key in the `X-API-Key` header.

| Method | Description |
|--------|-------------|
| **API Key** | Must provide `X-API-Key` header with every request |

**Default API Key:** `arwest-cf-2026-internal`  
**To customize:** Set `AR_TRACKER_API_KEY` environment variable on Render.com

## Render.com Setup

1. **Create a new Web Service** on Render.com
2. **Connect your GitHub repo** (ar-west-tracker-server)
3. **Configure:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python server.py`
4. **Add Environment Variable:**
   - `AR_TRACKER_API_KEY` = `your-secret-key-here` (or use default)
5. **Deploy!**

Your server will be at: `https://your-app-name.onrender.com`

## Connecting from AR West Tracker

Your userscript/HTML needs to include the API key in requests:

```javascript
// Add this header to all fetch requests
headers: {
  'Content-Type': 'application/json',
  'X-API-Key': 'arwest-cf-2026-internal'
}
```

## How It Works

- All tracker data is stored in a SQLite database
- Multiple users can connect and see each other's changes
- Shift log entries are automatically merged
- Archives are shared across all users
- **All data endpoints require API key**

## Network Access

To allow other computers on your network to connect:

1. Find your computer's IP address:
   - Open Command Prompt
   - Type `ipconfig`
   - Look for "IPv4 Address" (e.g., `192.168.1.100`)

2. Share this address with your team:
   - They should use `http://192.168.1.100:5000` as the server URL

3. Make sure Windows Firewall allows connections on port 5000

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Check if server is online |
| `/api/data` | GET | Get all tracker data |
| `/api/data` | POST | Save tracker data |
| `/api/sync` | POST | Smart sync (merge local + server) |
| `/api/shift-logs` | GET | Get all shift logs |
| `/api/shift-logs` | POST | Add shift log entry |
| `/api/archives` | GET | List all archives |
| `/api/archives` | POST | Create archive |

## Troubleshooting

**Server won't start:**
- Make sure Python is installed
- Run `pip install flask flask-cors` manually

**Can't connect from other computers:**
- Check firewall settings
- Make sure you're using the correct IP address
- Verify all computers are on the same network

**Data not syncing:**
- Check browser console for errors
- Verify server URL is correct in tracker settings
