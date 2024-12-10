import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD'),
            host=os.environ.get('PGHOST'),
            port=os.environ.get('PGPORT')
        )
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
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
            self.conn.commit()

    def add_transaction(self, date, type_trans, description, amount):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO transactions (date, type, description, amount)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (date, type_trans, description, amount))
            self.conn.commit()
            return cur.fetchone()[0]

    def get_transactions(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM transactions 
                ORDER BY date DESC, created_at DESC;
            """)
            return cur.fetchall()

    def get_balance(self):
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

    def update_transaction(self, id, field, value):
        """Update a specific field of a transaction."""
        valid_fields = {'date', 'type', 'amount'}
        if field not in valid_fields:
            raise ValueError(f"Invalid field: {field}")
        
        with self.conn.cursor() as cur:
            cur.execute(f"""
                UPDATE transactions 
                SET {field} = %s
                WHERE id = %s
                RETURNING id;
            """, (value, id))
            self.conn.commit()
            return cur.fetchone() is not None

    def delete_transaction(self, id):
        """Delete a transaction by ID."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM transactions
                    WHERE id = %s
                    RETURNING id;
                """, (id,))
                result = cur.fetchone()
                self.conn.commit()
                return result is not None
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to delete transaction: {str(e)}")

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
