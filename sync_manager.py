from datetime import datetime
import sqlite3
import json
import threading
import time
import requests
from queue import Queue
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncManager:
    def __init__(self, local_db_path, server_url):
        self.local_db_path = local_db_path
        self.server_url = server_url
        self.sync_queue = Queue()
        self.is_online = False
        self.sync_lock = threading.Lock()
        self._setup_local_db()
        
    def _setup_local_db(self):
        """Initialise la base de données locale pour le stockage hors ligne"""
        conn = sqlite3.connect(self.local_db_path)
        cursor = conn.cursor()
        
        # Table pour stocker les modifications en attente
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                operation TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Table pour stocker la dernière synchronisation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_metadata (
                table_name TEXT PRIMARY KEY,
                last_sync_timestamp DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_local_change(self, table_name, record_id, operation, data):
        """Stocke une modification locale en attente de synchronisation"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Add timestamp if not present
            if 'last_modified' not in data:
                data['last_modified'] = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO pending_changes (table_name, record_id, operation, data)
                VALUES (?, ?, ?, ?)
            ''', (table_name, record_id, operation, json.dumps(data)))
            
            conn.commit()
            self.sync_queue.put({
                'table': table_name,
                'record_id': record_id,
                'operation': operation,
                'data': data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage local: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def check_connection(self):
        """Vérifie la connexion au serveur"""
        try:
            response = requests.get(f"{self.server_url}/ping", timeout=2)  # Reduced timeout
            self.is_online = response.status_code == 200
            return self.is_online
        except:
            self.is_online = False
            return False
    
    def sync_changes(self):
        """Synchronise les modifications en attente avec le serveur"""
        if not self.check_connection():
            logger.info("Pas de connexion au serveur, synchronisation reportée")
            return False
            
        with self.sync_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.local_db_path)
                cursor = conn.cursor()
                
                # Récupère les modifications en attente
                cursor.execute('''
                    SELECT id, table_name, record_id, operation, data
                    FROM pending_changes
                    WHERE sync_status = 'pending'
                    ORDER BY timestamp ASC
                ''')
                
                pending_changes = cursor.fetchall()
                
                if not pending_changes:
                    logger.info("Aucune modification en attente")
                    return True
                
                logger.info(f"Tentative de synchronisation de {len(pending_changes)} modifications")
                
                for change_id, table, record_id, operation, data in pending_changes:
                    try:
                        # Envoie la modification au serveur
                        response = requests.post(
                            f"{self.server_url}/sync",
                            json={
                                'table': table,
                                'record_id': record_id,
                                'operation': operation,
                                'data': json.loads(data)
                            },
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            logger.info(f"Modification {change_id} synchronisée avec succès")
                            # Met à jour le statut de synchronisation
                            cursor.execute('''
                                UPDATE pending_changes
                                SET sync_status = 'completed'
                                WHERE id = ?
                            ''', (change_id,))
                            
                            # Met à jour le timestamp de dernière synchronisation
                            cursor.execute('''
                                INSERT OR REPLACE INTO sync_metadata (table_name, last_sync_timestamp)
                                VALUES (?, datetime('now'))
                            ''', (table,))
                            
                        elif response.status_code == 409:  # Conflit
                            logger.warning(f"Conflit détecté pour la modification {change_id}")
                            self._handle_conflict(response.json(), change_id, cursor)
                        else:
                            logger.error(f"Erreur lors de la synchronisation {change_id}: {response.status_code}")
                            
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Erreur réseau lors de la synchronisation: {str(e)}")
                        return False
                    except Exception as e:
                        logger.error(f"Erreur lors de la synchronisation: {str(e)}")
                        continue
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Erreur lors de la synchronisation: {str(e)}")
                return False
                
            finally:
                if conn:
                    conn.close()
    
    def _handle_conflict(self, server_data, change_id, cursor):
        """Gère les conflits de synchronisation"""
        # Récupère les données locales
        cursor.execute('''
            SELECT data, timestamp
            FROM pending_changes
            WHERE id = ?
        ''', (change_id,))
        
        local_data, local_timestamp = cursor.fetchone()
        local_data = json.loads(local_data)
        
        # Compare les timestamps
        if server_data['timestamp'] > local_timestamp:
            # Le serveur a la version la plus récente
            cursor.execute('''
                UPDATE pending_changes
                SET sync_status = 'conflict_resolved_server'
                WHERE id = ?
            ''', (change_id,))
        else:
            # La version locale est plus récente
            cursor.execute('''
                UPDATE pending_changes
                SET sync_status = 'conflict_resolved_local'
                WHERE id = ?
            ''', (change_id,))
    
    def start_sync_worker(self):
        """Démarre le worker de synchronisation en arrière-plan"""
        def sync_worker():
            while True:
                if not self.sync_queue.empty() and self.check_connection():
                    self.sync_changes()
                time.sleep(30)  # Vérifie toutes les 30 secondes
        
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()
