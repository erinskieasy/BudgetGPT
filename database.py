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

    def get_transactions_for_matching(self, date, days_range=30):
        """Get transactions within a date range for matching."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT *, 
                    ABS(DATE '%s' - date) as date_diff 
                FROM transactions 
                ORDER BY date_diff ASC, created_at DESC;
            """, (date,))
            return cur.fetchall()


    def delete_transaction(self, date, description):
        with self.conn.cursor() as cur:
            # Use a date range of ±1 day to be more flexible
            cur.execute("""
                DELETE FROM transactions
                WHERE date BETWEEN %s::date - INTERVAL '1 day' AND %s::date + INTERVAL '1 day'
                AND description ILIKE %s
                RETURNING id;
            """, (date, date, f"%{description}%"))
            deleted = cur.fetchone()
            if not deleted:
                # Check if the transaction exists at all
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM transactions 
                        WHERE description ILIKE %s
                    );
                """, (f"%{description}%",))
                exists = cur.fetchone()[0]
                self.conn.commit()
                if exists:
                    raise ValueError(f"Found transaction with description '{description}' but date doesn't match. Try being more specific.")
                else:
                    raise ValueError(f"No transaction found with description containing '{description}'")
            return True

    def update_transaction(self, date, description, updates):
        update_fields = []
        update_values = []
        
        if 'date' in updates:
            update_fields.append("date = %s")
            update_values.append(updates['date'])
        if 'type' in updates:
            update_fields.append("type = %s")
            update_values.append(updates['type'])
        if 'description' in updates:
            update_fields.append("description = %s")
            update_values.append(updates['description'])
        if 'amount' in updates:
            update_fields.append("amount = %s")
            update_values.append(updates['amount'])
            
        if not update_fields:
            return False
            
        update_values.extend([date, date, f"%{description}%"])
        
        with self.conn.cursor() as cur:
            # Use a date range of ±1 day to be more flexible
            cur.execute(f"""
                UPDATE transactions
                SET {", ".join(update_fields)}
                WHERE date BETWEEN %s::date - INTERVAL '1 day' AND %s::date + INTERVAL '1 day'
                AND description ILIKE %s
                RETURNING id;
            """, tuple(update_values))
            self.conn.commit()
            updated = cur.fetchone()
            if not updated:
                # Check if the transaction exists at all
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM transactions 
                        WHERE description ILIKE %s
                    );
                """, (f"%{description}%",))
                exists = cur.fetchone()[0]
                if exists:
                    raise ValueError(f"Found transaction with description '{description}' but date doesn't match. Try being more specific.")
                else:
                    raise ValueError(f"No transaction found with description containing '{description}'")
            return True

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

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
