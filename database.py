import os
import psycopg2
from datetime import datetime
import pandas as pd

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self.setup_tables()

    def connect(self):
        """Connect to the PostgreSQL database with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.conn is not None:
                    try:
                        self.conn.close()
                    except:
                        pass
                
                self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
                self.conn.autocommit = False
                return
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to connect to database") from e

    def ensure_connection(self):
        """Ensure database connection is active"""
        try:
            # Try a simple query to test connection
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            self.connect()

    def setup_tables(self):
        """Initialize database tables with retry logic"""
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
                            type VARCHAR(50) NOT NULL,
                            description TEXT,
                            amount DECIMAL(10,2) NOT NULL,
                            user_id INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create settings table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS settings (
                            key VARCHAR(50) PRIMARY KEY,
                            value TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Create saved_filters table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS saved_filters (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(100) NOT NULL,
                            filter_column VARCHAR(50) NOT NULL,
                            filter_text TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    self.conn.commit()
                    return
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to setup tables") from e
                self.connect()

    def add_transaction(self, date, type_trans, description, amount, user_id=None):
        """Add a new transaction with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO transactions (date, type, description, amount, user_id)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (date, type_trans, description, amount, user_id))
                    self.conn.commit()
                    return cur.fetchone()[0]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to add transaction") from e
                self.connect()
    def filter_transactions(self, column, value, user_id=None):
        """Get filtered transactions with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    query = """
                        SELECT id, date, type, description, amount
                        FROM transactions
                        WHERE 1=1
                    """
                    params = []
                    
                    # Add user_id filter if provided
                    if user_id is not None:
                        query += " AND user_id = %s"
                        params.append(user_id)
                    
                    if column == "amount":
                        try:
                            float_value = float(value)
                            query += " AND amount = %s"
                            params.append(float_value)
                        except ValueError:
                            # Invalid amount, return empty result
                            return []
                    elif column == "type":
                        query += " AND LOWER(type) LIKE LOWER(%s)"
                        params.append(f"%{value}%")
                    elif column == "description":
                        query += " AND LOWER(description) LIKE LOWER(%s)"
                        params.append(f"%{value}%")
                    
                    query += " ORDER BY date DESC, created_at DESC"
                    cur.execute(query, tuple(params))
                    
                    columns = ['id', 'date', 'type', 'description', 'amount']
                    results = cur.fetchall()
                    return [dict(zip(columns, row)) for row in results]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get filtered transactions") from e
                self.connect()
            except Exception as e:
                # Log any other errors and return empty result
                print(f"Error in filter_transactions: {str(e)}")
                return []
        return []  # Return empty list if all retries failed


    def get_transactions(self, user_id=None):
        """Get all transactions with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    if user_id is not None:
                        cur.execute("""
                            SELECT id, date, type, description, amount
                            FROM transactions
                            WHERE user_id = %s
                            ORDER BY date DESC, created_at DESC
                        """, (user_id,))
                    else:
                        cur.execute("""
                            SELECT id, date, type, description, amount
                            FROM transactions
                            ORDER BY date DESC, created_at DESC
                        """)
                    columns = ['id', 'date', 'type', 'description', 'amount']
                    results = cur.fetchall()
                    return [dict(zip(columns, row)) for row in results]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get transactions") from e
                self.connect()

    def get_balance(self, user_id=None):
        """Calculate current balance with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    if user_id is not None:
                        cur.execute("""
                            SELECT 
                                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) -
                                COALESCE(SUM(CASE WHEN type IN ('expense', 'subscription') THEN amount ELSE 0 END), 0)
                            FROM transactions
                            WHERE user_id = %s
                        """, (user_id,))
                    else:
                        cur.execute("""
                            SELECT 
                                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) -
                                COALESCE(SUM(CASE WHEN type IN ('expense', 'subscription') THEN amount ELSE 0 END), 0)
                            FROM transactions
                        """)
                    return cur.fetchone()[0] or 0
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
                        RETURNING id;
                    """, (value, transaction_id))
                    self.conn.commit()
                    return cur.fetchone() is not None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to update transaction {transaction_id}") from e
                self.connect()

    def get_latest_transaction_ids(self, limit=None):
        """Get IDs of the latest transactions with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    query = """
                        SELECT id FROM transactions
                        ORDER BY created_at DESC, id DESC
                    """
                    if limit:
                        query += f" LIMIT {limit}"
                    cur.execute(query)
                    return [row[0] for row in cur.fetchall()]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get latest transaction IDs") from e
                self.connect()

    def get_setting(self, key):
        """Get a setting value with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT value
                        FROM settings
                        WHERE key = %s;
                    """, (key,))
                    result = cur.fetchone()
                    return result[0] if result else None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to get setting {key}") from e
                self.connect()

    def update_setting(self, key, value):
        """Update a setting with retry logic"""
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

    def save_filter(self, name, filter_column, filter_text, user_id=None):
        """Save a filter preset with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO saved_filters (name, filter_column, filter_text, user_id, owner_id, is_shared)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (name, filter_column, filter_text, user_id, user_id, False))
                    self.conn.commit()
                    return cur.fetchone()[0]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to save filter") from e
                self.connect()

    def get_saved_filters(self, user_id=None):
        """Get all saved filters with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    if user_id is not None:
                        cur.execute("""
                            SELECT f.id, f.name, f.filter_column, f.filter_text, 
                                   f.owner_id, f.is_shared,
                                   CASE 
                                       WHEN f.owner_id = %s THEN 'owner'
                                       ELSE 'shared'
                                   END as filter_type
                            FROM saved_filters f
                            WHERE f.user_id = %s OR (
                                f.id IN (
                                    SELECT filter_id 
                                    FROM filter_sharing 
                                    WHERE shared_with_id = %s AND status = 'accepted'
                                )
                            )
                            ORDER BY name ASC
                        """, (user_id, user_id, user_id))
                    else:
                        cur.execute("""
                            SELECT id, name, filter_column, filter_text, 
                                   owner_id, is_shared, 'owner' as filter_type
                            FROM saved_filters
                            ORDER BY name ASC
                        """)
                    columns = ['id', 'name', 'filter_column', 'filter_text', 
                             'owner_id', 'is_shared', 'filter_type']
                    results = cur.fetchall()
                    return [dict(zip(columns, row)) for row in results]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get saved filters") from e
                self.connect()

    def delete_saved_filter(self, filter_id):
        """Delete a saved filter by ID with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM saved_filters
                        WHERE id = %s
                        RETURNING id;
                    """, (filter_id,))
                    self.conn.commit()
                    return cur.fetchone() is not None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to delete saved filter") from e
                self.connect()

    def delete_transaction(self, transaction_id):
        """Delete a transaction by ID with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
    def share_filter(self, filter_id, owner_id, shared_with_username):
        """Share a filter with another user"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    # First, verify filter ownership
                    cur.execute("""
                        SELECT id FROM saved_filters
                        WHERE id = %s AND owner_id = %s
                    """, (filter_id, owner_id))
                    if not cur.fetchone():
                        raise Exception("Filter not found or you don't have permission to share it")
                    
                    # Get the user ID of the username to share with
                    cur.execute("""
                        SELECT id FROM users
                        WHERE username = %s
                    """, (shared_with_username,))
                    shared_user = cur.fetchone()
                    if not shared_user:
                        raise Exception(f"User {shared_with_username} not found")
                    
                    shared_with_id = shared_user[0]
                    if shared_with_id == owner_id:
                        raise Exception("Cannot share filter with yourself")

                    # Create sharing invitation
                    cur.execute("""
                        INSERT INTO filter_sharing (filter_id, shared_with_id)
                        VALUES (%s, %s)
                        ON CONFLICT (filter_id, shared_with_id) 
                        DO UPDATE SET status = 'pending'
                        RETURNING id;
                    """, (filter_id, shared_with_id))
                    
                    # Mark the filter as shared
                    cur.execute("""
                        UPDATE saved_filters
                        SET is_shared = TRUE
                        WHERE id = %s
                    """, (filter_id,))
                    
                    self.conn.commit()
                    return True
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to share filter") from e
                self.connect()

    def get_pending_filter_invitations(self, user_id):
        """Get all pending filter sharing invitations for a user"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT fs.id as invitation_id, 
                               f.id as filter_id,
                               f.name as filter_name,
                               u.username as shared_by,
                               fs.created_at
                        FROM filter_sharing fs
                        JOIN saved_filters f ON fs.filter_id = f.id
                        JOIN users u ON f.owner_id = u.id
                        WHERE fs.shared_with_id = %s 
                        AND fs.status = 'pending'
                        ORDER BY fs.created_at DESC
                    """, (user_id,))
                    columns = ['invitation_id', 'filter_id', 'filter_name', 
                             'shared_by', 'created_at']
                    results = cur.fetchall()
                    return [dict(zip(columns, row)) for row in results]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get pending invitations") from e
                self.connect()

    def handle_filter_invitation(self, invitation_id, user_id, accept=True):
        """Accept or reject a filter sharing invitation"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    # Verify invitation exists and belongs to user
                    cur.execute("""
                        SELECT filter_id FROM filter_sharing
                        WHERE id = %s AND shared_with_id = %s AND status = 'pending'
                    """, (invitation_id, user_id))
                    if not cur.fetchone():
                        raise Exception("Invalid invitation")

                    # Update invitation status
                    status = 'accepted' if accept else 'rejected'
                    cur.execute("""
                        UPDATE filter_sharing
                        SET status = %s
                        WHERE id = %s AND shared_with_id = %s
                        RETURNING filter_id
                    """, (status, invitation_id, user_id))
                    
                    self.conn.commit()
                    return True
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to handle invitation") from e
                self.connect()

    def get_filter_transactions(self, filter_id, user_id):
        """Get transactions for a specific filter, checking access rights"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    # Check if user has access to this filter
                    cur.execute("""
                        SELECT f.filter_column, f.filter_text, f.owner_id
                        FROM saved_filters f
                        LEFT JOIN filter_sharing fs ON f.id = fs.filter_id
                        WHERE f.id = %s AND (
                            f.owner_id = %s OR
                            (fs.shared_with_id = %s AND fs.status = 'accepted')
                        )
                    """, (filter_id, user_id, user_id))
                    
                    filter_data = cur.fetchone()
                    if not filter_data:
                        raise Exception("Filter not found or access denied")
                    
                    filter_column, filter_text, owner_id = filter_data
                    
                    # Get filtered transactions using the owner's user_id
                    return self.filter_transactions(filter_column, filter_text, owner_id)
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get filter transactions") from e
                self.connect()

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