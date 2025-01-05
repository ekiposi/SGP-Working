from flask import Flask, jsonify, request
import sqlite3
from datetime import datetime
import json

app = Flask(__name__)

# Initialize server database
def init_db():
    conn = sqlite3.connect('server.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            check_in TEXT,
            check_out TEXT,
            last_modified TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'online'}), 200

@app.route('/api/sync', methods=['POST'])
def sync():
    try:
        data = request.get_json()
        
        conn = sqlite3.connect('server.db')
        cursor = conn.cursor()
        
        table = data.get('table')
        record_id = data.get('record_id')
        operation = data.get('operation')
        record_data = data.get('data')
        
        if table != 'attendance':
            return jsonify({'error': 'Table non supportée'}), 400
            
        if operation == 'create':
            cursor.execute('''
                INSERT INTO attendance_records 
                (employee_id, date, check_in, check_out, last_modified)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                record_data['employee_id'],
                record_data['date'],
                record_data['check_in'],
                record_data.get('check_out'),
                datetime.now().isoformat()
            ))
            
        elif operation == 'update':
            # Check for conflicts
            cursor.execute('''
                SELECT last_modified FROM attendance_records
                WHERE id = ?
            ''', (record_id,))
            
            existing = cursor.fetchone()
            if existing:
                server_timestamp = datetime.fromisoformat(existing[0])
                local_timestamp = datetime.fromisoformat(record_data.get('last_modified', '2000-01-01'))
                
                if server_timestamp > local_timestamp:
                    return jsonify({
                        'status': 'conflict',
                        'timestamp': server_timestamp.isoformat(),
                        'server_data': existing
                    }), 409
            
            cursor.execute('''
                UPDATE attendance_records
                SET check_in = ?, check_out = ?, last_modified = ?
                WHERE id = ?
            ''', (
                record_data['check_in'],
                record_data['check_out'],
                datetime.now().isoformat(),
                record_id
            ))
            
        conn.commit()
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    app.run(port=5001)
