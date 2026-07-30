"""
AR West Tracker - Shared Server (Amazon Internal Only)
A Flask server with SQLite database for multi-user collaboration.
SECURED: API key required for all data endpoints.
Deployed on: Render.com
"""

from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from functools import wraps
import sqlite3
import json
import os
import re
from datetime import datetime

app = Flask(__name__)

# ============ SECURITY CONFIGURATION ============

# API Key - Set this as environment variable on Render.com
API_KEY = os.environ.get('AR_TRACKER_API_KEY', 'arwest-cf-2026-internal')

def require_api_key(f):
    """Decorator to require valid API key for access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check API key from header or query param
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key required. Add X-API-Key header.',
                'hint': 'Get the API key from your team lead.'
            }), 401
        
        if api_key != API_KEY:
            return jsonify({
                'success': False,
                'error': 'Invalid API key.',
                'hint': 'Check your API key.'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key"]
    }
})

# ============ LOGIN PAGE ============
LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AR West Tracker - Login</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Segoe UI', sans-serif; 
            background: linear-gradient(135deg, #1b2a4a 0%, #0f172a 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-box {
            background: #fff;
            border-radius: 16px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
        }
        .logo { font-size: 48px; margin-bottom: 16px; }
        h1 { color: #1b2a4a; font-size: 24px; margin-bottom: 8px; }
        .subtitle { color: #64748b; font-size: 14px; margin-bottom: 32px; }
        .input-group { margin-bottom: 20px; text-align: left; }
        label { display: block; font-weight: 600; color: #334155; margin-bottom: 8px; font-size: 14px; }
        input {
            width: 100%;
            padding: 14px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }
        input:focus { outline: none; border-color: #3b82f6; }
        .btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(59,130,246,0.4); }
        .error { 
            background: #fef2f2; 
            color: #dc2626; 
            padding: 12px; 
            border-radius: 8px; 
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }
        .error.show { display: block; }
        .hint { color: #94a3b8; font-size: 12px; margin-top: 24px; }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo">🔐</div>
        <h1>AR West Tracker</h1>
        <p class="subtitle">Amazon Internal Only</p>
        
        <div id="error" class="error"></div>
        
        <form onsubmit="return handleLogin(event)">
            <div class="input-group">
                <label>API Key</label>
                <input type="password" id="apiKey" placeholder="Enter your API key" required>
            </div>
            <div class="input-group">
                <label>Your Name</label>
                <input type="text" id="userName" placeholder="Enter your name" required>
            </div>
            <button type="submit" class="btn">🚀 Access Tracker</button>
        </form>
        
        <p class="hint">Get the API key from your team lead</p>
    </div>
    
    <script>
        // Check if already logged in
        var savedKey = localStorage.getItem('ar-west-api-key');
        var savedName = localStorage.getItem('ar-west-user-name');
        if (savedKey && savedName) {
            verifyAndRedirect(savedKey, savedName);
        }
        
        function handleLogin(e) {
            e.preventDefault();
            var apiKey = document.getElementById('apiKey').value.trim();
            var userName = document.getElementById('userName').value.trim();
            verifyAndRedirect(apiKey, userName);
            return false;
        }
        
        async function verifyAndRedirect(apiKey, userName) {
            var errorEl = document.getElementById('error');
            errorEl.classList.remove('show');
            
            try {
                var response = await fetch('/api/status', {
                    headers: { 'X-API-Key': apiKey }
                });
                var result = await response.json();
                
                if (result.api_key_valid) {
                    localStorage.setItem('ar-west-api-key', apiKey);
                    localStorage.setItem('ar-west-user-name', userName);
                    window.location.href = '/app';
                } else {
                    throw new Error('Invalid API key');
                }
            } catch (err) {
                localStorage.removeItem('ar-west-api-key');
                errorEl.textContent = '❌ Invalid API key. Please try again.';
                errorEl.classList.add('show');
            }
        }
    </script>
</body>
</html>
'''

# ============ ROUTES ============

@app.route('/')
def index():
    """Show login page."""
    return render_template_string(LOGIN_PAGE)

@app.route('/app')
def app_page():
    """Serve the main app (requires valid API key in localStorage - checked client-side)."""
    # Read and serve the app HTML
    try:
        with open('app.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "App not found. Please deploy app.html", 404

DATABASE = 'ar_west_tracker.db'

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Main data store - stores the complete tracker state
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracker_data (
            id INTEGER PRIMARY KEY,
            data_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT
        )
    ''')
    
    # Shift log entries - separate table for easier querying
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shift_logs (
            id TEXT PRIMARY KEY,
            shift TEXT NOT NULL,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    
    # Action plans - separate table for tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_plans (
            id TEXT PRIMARY KEY,
            site TEXT NOT NULL,
            metric TEXT NOT NULL,
            goal TEXT,
            action_plan TEXT,
            owner TEXT,
            progress TEXT DEFAULT 'not_started',
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    
    # Archives - for weekly snapshots
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS archives (
            id TEXT PRIMARY KEY,
            week_label TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT
        )
    ''')
    
    # Site classifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classifications (
            site TEXT PRIMARY KEY,
            classification TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# Initialize database when module is loaded (for gunicorn)
init_db()

# ============ FULL DATA ENDPOINTS ============

@app.route('/api/data', methods=['GET'])
@require_api_key
def get_data():
    """Get the complete tracker data."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT data_json, updated_at, updated_by FROM tracker_data WHERE id = 1')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'success': True,
            'data': json.loads(row['data_json']),
            'updated_at': row['updated_at'],
            'updated_by': row['updated_by']
        })
    else:
        return jsonify({
            'success': True,
            'data': None,
            'message': 'No data found'
        })

@app.route('/api/data', methods=['POST'])
@require_api_key
def save_data():
    """Save the complete tracker data."""
    try:
        payload = request.get_json()
        data = payload.get('data')
        updated_by = payload.get('user', 'Unknown')
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tracker_data (id, data_json, updated_at, updated_by)
            VALUES (1, ?, ?, ?)
        ''', (json.dumps(data), now, updated_by))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Data saved successfully',
            'updated_at': now
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ SHIFT LOG ENDPOINTS ============

@app.route('/api/shift-logs', methods=['GET'])
@require_api_key
def get_shift_logs():
    """Get all shift log entries."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM shift_logs ORDER BY date DESC, created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    logs = [dict(row) for row in rows]
    return jsonify({'success': True, 'logs': logs})

@app.route('/api/shift-logs', methods=['POST'])
@require_api_key
def add_shift_log():
    """Add a new shift log entry."""
    try:
        entry = request.get_json()
        
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO shift_logs (id, shift, date, name, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.get('id', now),
            entry.get('shift'),
            entry.get('date'),
            entry.get('name'),
            entry.get('notes'),
            entry.get('timestamp', now),
            now
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Shift log saved'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/shift-logs/<log_id>', methods=['DELETE'])
@require_api_key
def delete_shift_log(log_id):
    """Delete a shift log entry."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM shift_logs WHERE id = ?', (log_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Shift log deleted'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ ARCHIVE ENDPOINTS ============

@app.route('/api/archives', methods=['GET'])
@require_api_key
def get_archives():
    """Get all archives."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, week_label, created_at, created_by FROM archives ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    archives = [dict(row) for row in rows]
    return jsonify({'success': True, 'archives': archives})

@app.route('/api/archives/<archive_id>', methods=['GET'])
@require_api_key
def get_archive(archive_id):
    """Get a specific archive."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM archives WHERE id = ?', (archive_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        archive = dict(row)
        archive['data'] = json.loads(archive['data_json'])
        del archive['data_json']
        return jsonify({'success': True, 'archive': archive})
    else:
        return jsonify({'success': False, 'error': 'Archive not found'}), 404

@app.route('/api/archives', methods=['POST'])
@require_api_key
def create_archive():
    """Create a new archive."""
    try:
        payload = request.get_json()
        
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO archives (id, week_label, data_json, created_at, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            payload.get('id', now),
            payload.get('week_label'),
            json.dumps(payload.get('data', {})),
            now,
            payload.get('user', 'Unknown')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Archive created'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/archives/<archive_id>', methods=['DELETE'])
@require_api_key
def delete_archive(archive_id):
    """Delete an archive."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM archives WHERE id = ?', (archive_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Archive deleted'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ SYNC ENDPOINT ============

@app.route('/api/sync', methods=['POST'])
@require_api_key
def sync_data():
    """
    Smart sync - merges local data with server data.
    Returns the merged result.
    """
    try:
        payload = request.get_json()
        local_data = payload.get('data', {})
        user = payload.get('user', 'Unknown')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get current server data
        cursor.execute('SELECT data_json FROM tracker_data WHERE id = 1')
        row = cursor.fetchone()
        
        if row:
            server_data = json.loads(row['data_json'])
            # Merge shift logs (combine unique entries)
            merged_logs = merge_shift_logs(
                server_data.get('shiftLog', []),
                local_data.get('shiftLog', [])
            )
            local_data['shiftLog'] = merged_logs
        
        # Save merged data
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO tracker_data (id, data_json, updated_at, updated_by)
            VALUES (1, ?, ?, ?)
        ''', (json.dumps(local_data), now, user))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': local_data,
            'updated_at': now,
            'message': 'Data synced successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def merge_shift_logs(server_logs, local_logs):
    """Merge shift logs from server and local, keeping unique entries."""
    merged = {log['id']: log for log in server_logs}
    for log in local_logs:
        log_id = log.get('id')
        if log_id:
            # Local entry wins if newer or doesn't exist on server
            if log_id not in merged:
                merged[log_id] = log
            else:
                # Compare timestamps, keep newer
                local_time = log.get('timestamp', '')
                server_time = merged[log_id].get('timestamp', '')
                if local_time > server_time:
                    merged[log_id] = log
    
    return list(merged.values())

# ============ STATUS ENDPOINT ============

@app.route('/api/status', methods=['GET'])
def status():
    """Check server status (public - for health checks)."""
    # Check if API key was provided (for testing)
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    key_valid = api_key == API_KEY if api_key else None
    
    return jsonify({
        'success': True,
        'status': 'online',
        'server': 'AR West Tracker Server',
        'version': '2.0.0',
        'security': 'API Key Required',
        'platform': 'Render.com',
        'api_key_provided': api_key is not None,
        'api_key_valid': key_valid,
        'timestamp': datetime.now().isoformat()
    })

# ============ MAIN ============

if __name__ == '__main__':
    print("=" * 60)
    print("AR West Tracker - Shared Server")
    print("🔒 SECURED: API Key Required")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    # Get port from environment (Render sets this automatically)
    port = int(os.environ.get('PORT', 5000))
    
    print(f"\n✅ Server starting on port {port}")
    
    # Check if API key is set
    if API_KEY == 'arwest-cf-2026-internal':
        print("\n⚠️  Using default API key!")
        print("   Set AR_TRACKER_API_KEY environment variable for production.")
    else:
        print(f"\n🔑 Custom API key configured")
    
    print("\n🛡️  Security: All data endpoints require X-API-Key header")
    print("\nPress Ctrl+C to stop\n")
    
    # Run server (Render will set debug=False in production)
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
