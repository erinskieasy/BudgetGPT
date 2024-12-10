from datetime import datetime
import pandas as pd

class TransactionManager:
    def __init__(self, database, gpt_processor=None):
        self.db = database
        self.gpt = gpt_processor

    def process_command(self, command_data):
        try:
            command = command_data.get('command', '').lower()
            
            if command == 'add':
                transaction = command_data.get('transaction', {})
                return self.add_transaction(transaction)
            
            elif command in ['delete', 'update']:
                # Get transactions context for GPT
                transactions_df = self.get_transactions_df()
                transactions_context = transactions_df.to_string() if not transactions_df.empty else "No transactions"
                
                # Let GPT generate the SQL command
                sql_command = self.gpt.generate_sql_command(command_data, transactions_context)
                
                # Execute the SQL command
                with self.db.conn.cursor() as cur:
                    cur.execute(sql_command['sql'], tuple(sql_command['params']))
                    affected = cur.rowcount
                    self.db.conn.commit()
                    
                    if affected == 0:
                        raise ValueError("No matching transaction found. Please be more specific.")
                    return True
            
            else:
                raise ValueError(f"Unknown command: {command}")
                
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid command data: {str(e)}")

    def add_transaction(self, transaction_data):
        # Validate and process the transaction data
        try:
            date = datetime.strptime(transaction_data['date'], '%Y-%m-%d').date()
            amount = float(transaction_data['amount'])
            type_trans = transaction_data['type'].lower()
            description = transaction_data['description']

            # Validate transaction type
            if type_trans not in ['expense', 'subscription', 'income']:
                raise ValueError("Invalid transaction type")

            # Add to database
            return self.db.add_transaction(date, type_trans, description, amount)
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid transaction data: {str(e)}")

    def get_transactions_df(self):
        transactions = self.db.get_transactions()
        if not transactions:
            return pd.DataFrame(columns=['date', 'type', 'description', 'amount'])
        
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df

    def get_summary_stats(self):
        df = self.get_transactions_df()
        if df.empty:
            return {
                'total_expenses': 0,
                'total_subscriptions': 0,
                'current_balance': 0,
                'monthly_breakdown': {}
            }

        stats = {
            'total_expenses': df[df['type'] == 'expense']['amount'].sum(),
            'total_subscriptions': df[df['type'] == 'subscription']['amount'].sum(),
            'current_balance': self.db.get_balance(),
        }

        # Monthly breakdown
        df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
        monthly = df.groupby('month')['amount'].sum()
        stats['monthly_breakdown'] = monthly.to_dict()

        return stats
