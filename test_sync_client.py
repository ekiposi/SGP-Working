from flask import Flask, jsonify, render_template_string
from sync_manager import SyncManager
import threading
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Sync Manager
sync_manager = SyncManager(
    local_db_path='test_local_sync.db',
    server_url='http://localhost:5001/api'
)

# HTML template for the test interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Test de Synchronisation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .button { padding: 10px; margin: 5px; cursor: pointer; }
        .status { margin: 20px 0; padding: 10px; border: 1px solid #ccc; }
        .offline { background-color: #ffebee; }
        .online { background-color: #e8f5e9; }
    </style>
    <script>
        function makeRequest(endpoint) {
            fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    employee_id: 1,
                    timestamp: new Date().toISOString()
                })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('result').textContent = JSON.stringify(data, null, 2);
                setTimeout(updateStatus, 1000);
            });
        }

        function updateStatus() {
            fetch('/status')
            .then(response => response.json())
            .then(data => {
                const statusDiv = document.getElementById('status');
                statusDiv.textContent = data.is_online ? 'En ligne' : 'Hors ligne';
                statusDiv.className = 'status ' + (data.is_online ? 'online' : 'offline');
            });
        }

        // Update status every 5 seconds
        setInterval(updateStatus, 5000);
        // Initial status check
        updateStatus();
    </script>
</head>
<body>
    <h1>Test de Synchronisation Hors Ligne/En Ligne</h1>
    
    <div id="status" class="status">Vérification du statut...</div>
    
    <button class="button" onclick="makeRequest('/record_checkin')">
        Enregistrer Entrée
    </button>
    
    <button class="button" onclick="makeRequest('/record_checkout')">
        Enregistrer Sortie
    </button>
    
    <h3>Résultat:</h3>
    <pre id="result"></pre>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def check_status():
    is_online = sync_manager.check_connection()
    return jsonify({'is_online': is_online})

@app.route('/record_checkin', methods=['POST'])
def record_checkin():
    try:
        current_time = datetime.now().isoformat()
        
        # Store the check-in locally
        sync_manager.store_local_change(
            'attendance',
            1,  # Using a fixed record ID for testing
            'create',
            {
                'employee_id': 1,
                'date': current_time[:10],
                'check_in': current_time,
                'check_out': None,
                'last_modified': current_time
            }
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Entrée enregistrée localement',
            'timestamp': current_time
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/record_checkout', methods=['POST'])
def record_checkout():
    try:
        current_time = datetime.now().isoformat()
        
        # Store the check-out locally
        sync_manager.store_local_change(
            'attendance',
            1,  # Using a fixed record ID for testing
            'update',
            {
                'employee_id': 1,
                'date': current_time[:10],
                'check_in': (datetime.now().replace(hour=9, minute=0)).isoformat(),  # Simulated check-in time
                'check_out': current_time,
                'last_modified': current_time
            }
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Sortie enregistrée localement',
            'timestamp': current_time
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    # Start the sync worker in a separate thread
    sync_manager.start_sync_worker()
    app.run(port=5002)
