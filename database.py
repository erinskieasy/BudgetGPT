import os
import psycopg2
from datetime import datetime
import time

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self.setup_database()

    def connect(self):
        """Connect to the PostgreSQL database with retry logic"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                if self.conn is None or self.conn.closed:
                    self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
                    self.conn.autocommit = False
                return
            except psycopg2.Error as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to connect to database") from e
                time.sleep(retry_delay)

    def ensure_connection(self):
        """Ensure database connection is active"""
        try:
            # Try a simple query to test connection
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
        except (psycopg2.Error, AttributeError):
            self.connect()

    def setup_database(self):
        """Set up the database schema"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    # Create transactions table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS transactions (
                            id SERIAL PRIMARY KEY,
                            date DATE NOT NULL,
                            type VARCHAR(20) NOT NULL,
                            description TEXT,
                            amount DECIMAL(10,2) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create settings table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS settings (
                            key VARCHAR(50) PRIMARY KEY,
                            value TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    self.conn.commit()
                    return
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to set up database") from e
                self.connect()

    def add_transaction(self, date, type_trans, description, amount):
        """Add a transaction with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO transactions (date, type, description, amount)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (date, type_trans, description, amount))
                    self.conn.commit()
                    return cur.fetchone()[0]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to add transaction") from e
                self.connect()

    def get_transactions(self):
        """Get all transactions with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, date, type, description, amount 
                        FROM transactions 
                        ORDER BY date DESC, id DESC
                    """)
                    columns = ['id', 'date', 'type', 'description', 'amount']
                    results = cur.fetchall()
                    return [dict(zip(columns, row)) for row in results]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get transactions") from e
                self.connect()

    def get_balance(self):
        """Calculate current balance with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            COALESCE(SUM(CASE 
                                WHEN type = 'income' THEN amount 
                                ELSE -amount 
                            END), 0) as balance
                        FROM transactions
                    """)
                    return cur.fetchone()[0]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to calculate balance") from e
                self.connect()

    def update_transaction(self, transaction_id, field, value):
        """Update a transaction field with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute(f"""
                        UPDATE transactions 
                        SET {field} = %s 
                        WHERE id = %s
                        RETURNING id
                    """, (value, transaction_id))
                    self.conn.commit()
                    return cur.fetchone() is not None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to update transaction") from e
                self.connect()

    def get_latest_transaction_ids(self, limit=None):
        """Get the IDs of the latest transactions, ordered by date"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    query = """
                        SELECT id FROM transactions
                        ORDER BY date DESC, id DESC
                    """
                    if limit:
                        query += " LIMIT %s"
                        cur.execute(query, (limit,))
                    else:
                        cur.execute(query)
                    results = cur.fetchall()
                    return [r[0] for r in results]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get latest transaction IDs") from e
                self.connect()

    def get_setting(self, key):
        """Get a setting value by key with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT value FROM settings
                        WHERE key = %s;
                    """, (key,))
                    result = cur.fetchone()
                    return result[0] if result else None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to get setting {key}") from e
                self.connect()

    def update_setting(self, key, value):
        """Update a setting value by key with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO settings (key, value)
                        VALUES (%s, %s)
                        ON CONFLICT (key) DO UPDATE
                        SET value = EXCLUDED.value,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING key;
                    """, (key, str(value)))
                    self.conn.commit()
                    return cur.fetchone() is not None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to update setting {key}") from e
                self.connect()

    def delete_transaction(self, transaction_id):
        """Delete a transaction by ID with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM transactions
                        WHERE id = %s
                        RETURNING id;
                    """, (transaction_id,))
                    self.conn.commit()
                    return cur.fetchone() is not None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to delete transaction") from e
                self.connect()

    def __del__(self):
        """Safely close the database connection"""
        if hasattr(self, 'conn') and self.conn is not None:
            try:
                self.conn.close()
            except:
                pass  # Ignore any errors during cleanup
