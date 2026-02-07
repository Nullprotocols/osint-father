import sqlite3
import json
import threading
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from contextlib import contextmanager
import hashlib
import zlib
import os

class DatabaseManager:
    """Advanced Database Manager with Connection Pooling"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.db_path = 'bot_database.db'
            self.connection_pool = {}
            self.max_pool_size = 5
            self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection from pool"""
        thread_id = threading.get_ident()
        
        if thread_id not in self.connection_pool:
            if len(self.connection_pool) >= self.max_pool_size:
                # Remove oldest connection
                oldest = list(self.connection_pool.keys())[0]
                self.connection_pool[oldest].close()
                del self.connection_pool[oldest]
            
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connection_pool[thread_id] = conn
        
        return self.connection_pool[thread_id]
    
    def init_database(self):
        """Initialize database with all tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table with enhanced fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                is_premium INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                credits INTEGER DEFAULT 100,
                total_credits_earned INTEGER DEFAULT 0,
                total_credits_spent INTEGER DEFAULT 0,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                last_lookup TIMESTAMP,
                total_lookups INTEGER DEFAULT 0,
                successful_lookups INTEGER DEFAULT 0,
                failed_lookups INTEGER DEFAULT 0,
                referred_by INTEGER,
                referral_code TEXT UNIQUE,
                total_referred INTEGER DEFAULT 0,
                settings TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}'
            )
        ''')
        
        # Lookups table with compression
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lookups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lookup_uuid TEXT UNIQUE,
                user_id INTEGER,
                command TEXT,
                query TEXT,
                query_hash TEXT,
                result BLOB,  -- Compressed JSON
                result_size INTEGER,
                status TEXT DEFAULT 'success',
                error_message TEXT,
                api_response_time REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                log_channel_id INTEGER,
                log_message_id INTEGER,
                indexed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Admin actions log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT,
                target_id INTEGER,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # API usage statistics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT,
                endpoint TEXT,
                total_calls INTEGER DEFAULT 0,
                successful_calls INTEGER DEFAULT 0,
                failed_calls INTEGER DEFAULT 0,
                total_response_time REAL DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                last_called TIMESTAMP,
                daily_calls INTEGER DEFAULT 0,
                monthly_calls INTEGER DEFAULT 0,
                last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Rate limiting
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rate_limits (
                user_id INTEGER,
                command TEXT,
                count INTEGER DEFAULT 1,
                window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, command)
            )
        ''')
        
        # Cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key_hash TEXT PRIMARY KEY,
                key_data TEXT,
                value BLOB,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP
            )
        ''')
        
        # Notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                notification_type TEXT,
                title TEXT,
                message TEXT,
                data TEXT DEFAULT '{}',
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lookups_user ON lookups(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lookups_timestamp ON lookups(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lookups_command ON lookups(command)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_join_date ON users(join_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)')
        
        conn.commit()
    
    def compress_data(self, data: Any) -> Tuple[bytes, int]:
        """Compress data for storage"""
        json_str = json.dumps(data, ensure_ascii=False)
        compressed = zlib.compress(json_str.encode('utf-8'), level=9)
        return compressed, len(compressed)
    
    def decompress_data(self, compressed: bytes) -> Any:
        """Decompress stored data"""
        json_str = zlib.decompress(compressed).decode('utf-8')
        return json.loads(json_str)
    
    def add_user(self, user_data: Dict) -> bool:
        """Add new user to database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Generate referral code
            referral_code = hashlib.md5(f"{user_data['user_id']}{datetime.now().timestamp()}".encode()).hexdigest()[:8]
            
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, language_code, referral_code, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['user_id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('language_code', 'en'),
                referral_code,
                datetime.now()
            ))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def record_lookup(self, user_id: int, command: str, query: str, result: Dict, 
                     status: str = 'success', error: str = None, response_time: float = None) -> str:
        """Record a lookup in database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Compress result
            compressed_result, result_size = self.compress_data(result)
            
            # Generate UUID
            import uuid
            lookup_uuid = str(uuid.uuid4())
            
            # Create query hash
            query_hash = hashlib.md5(f"{command}:{query}".encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO lookups 
                (lookup_uuid, user_id, command, query, query_hash, result, result_size, 
                 status, error_message, api_response_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                lookup_uuid,
                user_id,
                command,
                query,
                query_hash,
                compressed_result,
                result_size,
                status,
                error,
                response_time,
                datetime.now()
            ))
            
            # Update user stats
            cursor.execute('''
                UPDATE users SET 
                last_active = ?,
                last_lookup = ?,
                total_lookups = total_lookups + 1,
                successful_lookups = successful_lookups + ?,
                failed_lookups = failed_lookups + ?,
                credits = credits - 1
                WHERE user_id = ?
            ''', (
                datetime.now(),
                datetime.now(),
                1 if status == 'success' else 0,
                1 if status != 'success' else 0,
                user_id
            ))
            
            # Update API stats
            cursor.execute('''
                INSERT INTO api_stats (api_name, endpoint, total_calls, successful_calls, 
                                      failed_calls, total_response_time, last_called, daily_calls)
                VALUES (?, ?, 1, ?, ?, ?, ?, 1)
                ON CONFLICT(api_name) DO UPDATE SET
                total_calls = total_calls + 1,
                successful_calls = successful_calls + ?,
                failed_calls = failed_calls + ?,
                total_response_time = total_response_time + ?,
                avg_response_time = total_response_time / total_calls,
                last_called = ?,
                daily_calls = daily_calls + 1
            ''', (
                command,
                command,
                1 if status == 'success' else 0,
                1 if status != 'success' else 0,
                response_time or 0,
                datetime.now(),
                1 if status == 'success' else 0,
                1 if status != 'success' else 0,
                response_time or 0,
                datetime.now()
            ))
            
            conn.commit()
            return lookup_uuid
        except Exception as e:
            print(f"Error recording lookup: {e}")
            return None
    
    def check_rate_limit(self, user_id: int, command: str, limit: int = 10, window: int = 60) -> bool:
        """Check if user has exceeded rate limit"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            window_start = datetime.now() - timedelta(seconds=window)
            
            cursor.execute('''
                SELECT count FROM rate_limits 
                WHERE user_id = ? AND command = ? AND window_start > ?
            ''', (user_id, command, window_start))
            
            result = cursor.fetchone()
            
            if result and result[0] >= limit:
                return False
            
            # Update or insert rate limit
            cursor.execute('''
                INSERT INTO rate_limits (user_id, command, count, window_start)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(user_id, command) DO UPDATE SET
                count = count + 1,
                window_start = CASE 
                    WHEN window_start < ? THEN ?
                    ELSE window_start
                END
            ''', (user_id, command, datetime.now(), window_start, datetime.now()))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Rate limit error: {e}")
            return True
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get comprehensive user statistics"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return None
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_lookups,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    COUNT(CASE WHEN status != 'success' THEN 1 END) as failed,
                    AVG(api_response_time) as avg_response_time,
                    MAX(timestamp) as last_lookup_time
                FROM lookups 
                WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
            
            cursor.execute('''
                SELECT command, COUNT(*) as count
                FROM lookups 
                WHERE user_id = ?
                GROUP BY command
                ORDER BY count DESC
                LIMIT 5
            ''', (user_id,))
            
            top_commands = cursor.fetchall()
            
            return {
                'user': dict(user),
                'stats': dict(stats) if stats else {},
                'top_commands': [dict(cmd) for cmd in top_commands]
            }
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return None
    
    def create_backup(self, format: str = 'all') -> List[str]:
        """Create database backup in multiple formats"""
        backup_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Create backup directory
            os.makedirs('backups', exist_ok=True)
            
            # SQLite backup
            if format in ['all', 'db']:
                backup_db = f'backups/backup_{timestamp}.db'
                conn_backup = sqlite3.connect(backup_db)
                self.get_connection().backup(conn_backup)
                conn_backup.close()
                backup_files.append(backup_db)
            
            # CSV backup
            if format in ['all', 'csv']:
                conn = self.get_connection()
                
                # Export users
                users_df = pd.read_sql_query("SELECT * FROM users", conn)
                users_csv = f'backups/users_{timestamp}.csv'
                users_df.to_csv(users_csv, index=False)
                backup_files.append(users_csv)
                
                # Export lookups
                lookups_df = pd.read_sql_query("SELECT * FROM lookups", conn)
                lookups_csv = f'backups/lookups_{timestamp}.csv'
                lookups_df.to_csv(lookups_csv, index=False)
                backup_files.append(lookups_csv)
            
            # JSON backup
            if format in ['all', 'json']:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                backup_data = {}
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT * FROM {table_name}")
                    columns = [description[0] for description in cursor.description]
                    rows = cursor.fetchall()
                    
                    table_data = []
                    for row in rows:
                        table_data.append(dict(zip(columns, row)))
                    
                    backup_data[table_name] = table_data
                
                backup_json = f'backups/backup_{timestamp}.json'
                with open(backup_json, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
                
                backup_files.append(backup_json)
            
            # Clean old backups (keep last 30)
            backup_dir = 'backups/'
            if os.path.exists(backup_dir):
                files = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir)], 
                              key=os.path.getmtime)
                if len(files) > 30:
                    for old_file in files[:-30]:
                        os.remove(old_file)
            
            return backup_files
            
        except Exception as e:
            print(f"Backup error: {e}")
            return []
    
    def get_admin_stats(self) -> Dict:
        """Get comprehensive admin statistics"""
        try:
            conn = self.get_connection()
            
            stats = {}
            
            # Basic counts
            counts_query = '''
                SELECT 
                    (SELECT COUNT(*) FROM users) as total_users,
                    (SELECT COUNT(*) FROM users WHERE date(join_date) = date('now')) as new_users_today,
                    (SELECT COUNT(*) FROM lookups) as total_lookups,
                    (SELECT COUNT(*) FROM lookups WHERE date(timestamp) = date('now')) as lookups_today,
                    (SELECT SUM(credits) FROM users) as total_credits,
                    (SELECT AVG(total_lookups) FROM users) as avg_lookups_per_user
            '''
            
            counts_df = pd.read_sql_query(counts_query, conn)
            stats['counts'] = counts_df.to_dict('records')[0]
            
            # Daily activity
            daily_query = '''
                SELECT 
                    date(timestamp) as date,
                    COUNT(*) as lookups,
                    COUNT(DISTINCT user_id) as active_users
                FROM lookups 
                WHERE timestamp > date('now', '-30 days')
                GROUP BY date(timestamp)
                ORDER BY date
            '''
            
            daily_df = pd.read_sql_query(daily_query, conn)
            stats['daily_activity'] = daily_df.to_dict('records')
            
            # Top users
            top_users_query = '''
                SELECT 
                    u.user_id,
                    u.username,
                    u.first_name,
                    COUNT(l.id) as total_lookups,
                    SUM(CASE WHEN l.status = 'success' THEN 1 ELSE 0 END) as successful_lookups,
                    u.credits,
                    u.join_date
                FROM users u
                LEFT JOIN lookups l ON u.user_id = l.user_id
                GROUP BY u.user_id
                ORDER BY total_lookups DESC
                LIMIT 10
            '''
            
            top_users_df = pd.read_sql_query(top_users_query, conn)
            stats['top_users'] = top_users_df.to_dict('records')
            
            # Command distribution
            commands_query = '''
                SELECT 
                    command,
                    COUNT(*) as count,
                    AVG(api_response_time) as avg_response_time,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as fail_count
                FROM lookups
                GROUP BY command
                ORDER BY count DESC
            '''
            
            commands_df = pd.read_sql_query(commands_query, conn)
            stats['commands'] = commands_df.to_dict('records')
            
            # API performance
            api_query = '''
                SELECT 
                    api_name,
                    total_calls,
                    successful_calls,
                    failed_calls,
                    avg_response_time,
                    last_called
                FROM api_stats
                ORDER BY total_calls DESC
            '''
            
            api_df = pd.read_sql_query(api_query, conn)
            stats['api_performance'] = api_df.to_dict('records')
            
            return stats
            
        except Exception as e:
            print(f"Error getting admin stats: {e}")
            return {}

# Global database instance
db = DatabaseManager()
