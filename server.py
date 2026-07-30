"""
AR West Tracker - Shared Server (Amazon Internal Only)
A Flask server with SQLite database for multi-user collaboration.
SECURED: API key required for all data endpoints.
Deployed on: Render.com
Run with: python server.py
"""

from flask import Flask, request, jsonify, abort
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
# Render Dashboard -> Environment -> Add AR_TRACKER_API_KEY
API_KEY = os.environ.get('AR_TRACKER_API_KEY', 'arwest-cf-2026-internal')

# Allowed origins - Amazon domains only (for CORS)
ALLOWED_ORIGINS = [
    r'https?://.*\.amazon\.com',
    r'https?://.*\.amazon\.dev',
    r'https?://.*\.a2z\.com',
    r'https?://.*\.corp\.amazon\.com',
    r'https?://localhost(:\d+)?',
    r'https?://127\.0\.0\.1(:\d+)?',
    r'^null$',  # Allow local file://
]

def is_allowed_origin(origin):
    """Check if origin matches allowed Amazon domains."""
    if not origin:
        return True  # Allow requests without origin (direct API calls)
    for pattern in ALLOWED_ORIGINS:
        if re.match(pattern, origin, re.IGNORECASE):
            return True
    return False

def require_api_key(f):
    """Decorator to require valid API key for access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check API key from header or query param
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            app.logger.warning(f"Access denied - No API key provided")
            return jsonify({
                'success': False,
                'error': 'API key required. Add X-API-Key header.',
                'hint': 'Get the API key from your team lead.'
            }), 401
        
        if api_key != API_KEY:
            app.logger.warning(f"Access denied - Invalid API key")
            return jsonify({
                'success': False,
                'error': 'Invalid API key.',
                'hint': 'Check your API key in Server Settings.'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Configure CORS - allow Amazon domains
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # We validate via API key instead
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key"]
    }
})

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
