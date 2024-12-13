import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self.create_tables()

    def connect(self):
        """Establish a database connection with retry logic"""
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                if self.conn is None or self.conn.closed:
                    self.conn = psycopg2.connect(
                        dbname=os.environ.get('PGDATABASE'),
                        user=os.environ.get('PGUSER'),
                        password=os.environ.get('PGPASSWORD'),
                        host=os.environ.get('PGHOST'),
                        port=os.environ.get('PGPORT'),
                        connect_timeout=5
                    )
                return
            except psycopg2.OperationalError as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise Exception(f"Failed to connect to database after {max_retries} attempts") from e
                time.sleep(1)  # Wait before retrying

    def ensure_connection(self):
        """Ensure database connection is active"""
        try:
            # Test if connection is alive and reset it if not
            if self.conn is None or self.conn.closed:
                self.connect()
            else:
                # Test the connection with a simple query
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            self.connect()

    def create_tables(self):
        """Create necessary database tables with retry logic"""
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
                            description TEXT NOT NULL,
                            amount DECIMAL(10,2) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Create settings table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS settings (
                            key VARCHAR(50) PRIMARY KEY,
                            value TEXT NOT NULL,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Insert default exchange rate if not exists
                    cur.execute("""
                        INSERT INTO settings (key, value)
                        VALUES ('exchange_rate', '155.0')
                        ON CONFLICT (key) DO NOTHING;
                    """)
                    
                self.conn.commit()
                return
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to create tables") from e
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
                        RETURNING id;
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
                with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM transactions 
                        ORDER BY date DESC, created_at DESC;
                    """)
                    return cur.fetchall()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get transactions") from e
                self.connect()

    def get_balance(self):
        """Get current balance with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT COALESCE(SUM(
                            CASE WHEN type = 'expense' THEN -amount
                                 WHEN type = 'subscription' THEN -amount
                                 ELSE amount END
                        ), 0) as balance
                        FROM transactions;
                    """)
                    return cur.fetchone()[0]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get balance") from e
                self.connect()

    def update_transaction(self, id, field, value):
        """Update a specific field of a transaction with retry logic"""
        valid_fields = {'date', 'type', 'amount'}
        if field not in valid_fields:
            raise ValueError(f"Invalid field: {field}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute(f"""
                        UPDATE transactions 
                        SET {field} = %s
                        WHERE id = %s
                        RETURNING id;
                    """, (value, id))
                    self.conn.commit()
                    return cur.fetchone() is not None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to update transaction") from e
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
                        UPDATE settings 
                        SET value = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE key = %s
                        RETURNING key;
                    """, (str(value), key))
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
