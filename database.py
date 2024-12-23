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
    def filter_transactions(self, column, value, user_id=None, owner_id=None):
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
                    
                    # Use owner_id if provided, otherwise use user_id
                    if owner_id is not None:
                        query += " AND user_id = %s"
                        params.append(owner_id)
                    elif user_id is not None:
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
                        search_terms = [term.strip() for term in value.split(',')]
                        type_conditions = []
                        for term in search_terms:
                            type_conditions.append("LOWER(type) LIKE LOWER(%s)")
                            params.append(f"%{term}%")
                        if type_conditions:
                            query += f" AND ({' OR '.join(type_conditions)})"
                    elif column == "description":
                        search_terms = [term.strip() for term in value.split(',')]
                        desc_conditions = []
                        for term in search_terms:
                            desc_conditions.append("LOWER(description) LIKE LOWER(%s)")
                            params.append(f"%{term}%")
                        if desc_conditions:
                            query += f" AND ({' OR '.join(desc_conditions)})"
                    
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
                        INSERT INTO saved_filters (name, filter_column, filter_text, user_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id;
                    """, (name, filter_column, filter_text, user_id))
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
                            SELECT id, name, filter_column, filter_text
                            FROM saved_filters
                            WHERE user_id = %s
                            ORDER BY name ASC
                        """, (user_id,))
                    else:
                        cur.execute("""
                            SELECT id, name, filter_column, filter_text
                            FROM saved_filters
                            ORDER BY name ASC
                        """)
                    columns = ['id', 'name', 'filter_column', 'filter_text']
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

    def send_partnership_request(self, user_id, partner_username):
        """Send a partnership request to another user"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    # First get the partner's user ID
                    cur.execute("""
                        SELECT id FROM users WHERE username = %s;
                    """, (partner_username,))
                    partner = cur.fetchone()
                    if not partner:
                        return None, "User not found"
                    
                    partner_id = partner[0]
                    if partner_id == user_id:
                        return None, "Cannot partner with yourself"

                    # Check if partnership already exists
                    cur.execute("""
                        SELECT status FROM user_partnerships 
                        WHERE (user_id = %s AND partner_id = %s)
                        OR (user_id = %s AND partner_id = %s);
                    """, (user_id, partner_id, partner_id, user_id))
                    
                    existing = cur.fetchone()
                    if existing:
                        return None, f"Partnership already exists with status: {existing[0]}"

                    # Create the partnership request
                    cur.execute("""
                        INSERT INTO user_partnerships (user_id, partner_id, status)
                        VALUES (%s, %s, 'pending')
                        RETURNING id;
                    """, (user_id, partner_id))
                    self.conn.commit()
                    return cur.fetchone()[0], None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to send partnership request") from e
                self.connect()

    def get_partnership_requests(self, user_id):
        """Get all pending partnership requests for a user"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT p.id, u.username, p.status, p.created_at
                        FROM user_partnerships p
                        JOIN users u ON u.id = p.user_id
                        WHERE p.partner_id = %s AND p.status = 'pending'
                        ORDER BY p.created_at DESC;
                    """, (user_id,))
                    columns = ['id', 'username', 'status', 'created_at']
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get partnership requests") from e
                self.connect()

    def update_partnership_status(self, partnership_id, user_id, status):
        """Update the status of a partnership request"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_partnerships
                        SET status = %s
                        WHERE id = %s AND partner_id = %s
                        RETURNING id;
                    """, (status, partnership_id, user_id))
                    self.conn.commit()
                    return cur.fetchone() is not None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to update partnership status") from e
                self.connect()

    def get_partners(self, user_id):
        """Get all accepted partners for a user"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT u.id, u.username
                        FROM user_partnerships p
                        JOIN users u ON (u.id = p.partner_id OR u.id = p.user_id)
                        WHERE (p.user_id = %s OR p.partner_id = %s)
                        AND p.status = 'accepted'
                        AND u.id != %s;
                    """, (user_id, user_id, user_id))
                    columns = ['id', 'username']
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get partners") from e
                self.connect()

    def share_filter(self, filter_id, owner_id, partner_id):
        """Share a filter with a partner"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    # Verify partnership exists and is accepted
                    cur.execute("""
                        SELECT id FROM user_partnerships
                        WHERE ((user_id = %s AND partner_id = %s)
                        OR (user_id = %s AND partner_id = %s))
                        AND status = 'accepted';
                    """, (owner_id, partner_id, partner_id, owner_id))
                    if not cur.fetchone():
                        return False, "No active partnership found"

                    # Share the filter
                    cur.execute("""
                        INSERT INTO shared_filters (filter_id, owner_id, shared_with_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (filter_id, owner_id, shared_with_id) DO NOTHING
                        RETURNING id;
                    """, (filter_id, owner_id, partner_id))
                    self.conn.commit()
                    return True, None
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to share filter") from e
                self.connect()

    def get_shared_filters(self, user_id):
        """Get all filters shared with a user"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.ensure_connection()
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            f.id,
                            f.name,
                            f.filter_column,
                            f.filter_text,
                            u.username as shared_by,
                            sf.created_at as shared_at
                        FROM shared_filters sf
                        JOIN saved_filters f ON f.id = sf.filter_id
                        JOIN users u ON u.id = sf.owner_id
                        WHERE sf.shared_with_id = %s
                        ORDER BY sf.created_at DESC;
                    """, (user_id,))
                    columns = ['id', 'name', 'filter_column', 'filter_text', 'shared_by', 'shared_at']
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_retries - 1:
                    raise Exception("Failed to get shared filters") from e
                self.connect()

    def __del__(self):
        """Safely close the database connection"""
        if hasattr(self, 'conn') and self.conn is not None:
            try:
                self.conn.close()
            except:
                pass  # Ignore any errors during cleanup