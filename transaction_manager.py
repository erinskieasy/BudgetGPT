from datetime import datetime
import pandas as pd

class TransactionManager:
    def __init__(self, database):
        self.db = database

    def process_command(self, command_data):
        try:
            command = command_data.get('command', '').lower()
            
            if command == 'add':
                transaction = command_data.get('transaction', {})
                return self.add_transaction(transaction)
            
            elif command in ['delete', 'update']:
                criteria = command_data.get('criteria', {})
                if not criteria:
                    raise ValueError("No criteria provided for modification")
                
                # Use today's date if no date is provided
                date_str = criteria.get('date', datetime.now().strftime('%Y-%m-%d'))
                if not date_str:
                    date_str = datetime.now().strftime('%Y-%m-%d')
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                description = criteria.get('description', '')
                if not description:
                    raise ValueError("No description provided for finding the transaction")
                
                try:
                    if command == 'delete':
                        return self.db.delete_transaction(date, description)
                    else:  # update
                        updates = command_data.get('updates', {})
                        if 'date' in updates:
                            updates['date'] = datetime.strptime(updates['date'], '%Y-%m-%d').date()
                        return self.db.update_transaction(date, description, updates)
                except ValueError as e:
                    raise ValueError(str(e))
            
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
