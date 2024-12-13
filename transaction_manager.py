from datetime import datetime
import pandas as pd

class TransactionManager:
    def __init__(self, database):
        self.db = database

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
    def get_filtered_transactions_df(self, filter_column=None, filter_text=None):
        """Get transactions with optional filtering"""
        if not filter_column or filter_column == "None" or not filter_text:
            return self.get_transactions_df()
        
        transactions = self.db.filter_transactions(filter_column, filter_text)
        if not transactions:
            return pd.DataFrame(columns=['date', 'type', 'description', 'amount'])
        
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df


    def update_transaction_field(self, transaction_id, field, value):
        """Update a specific field of a transaction."""
        try:
            if field == 'type' and value not in ['expense', 'subscription', 'income']:
                raise ValueError("Invalid transaction type")
            elif field == 'amount':
                value = float(value)
            elif field == 'date':
                if isinstance(value, str):
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                elif not isinstance(value, type(datetime.now().date())):
                    raise ValueError("Invalid date format")
            
            return self.db.update_transaction(transaction_id, field, value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid {field} value: {str(e)}")

    def delete_transaction(self, transaction_id):
        """Delete a single transaction by ID."""
        try:
            transaction_id = int(transaction_id)
            if self.db.delete_transaction(transaction_id):
                return True
            raise ValueError(f"Transaction {transaction_id} not found")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid transaction ID: {str(e)}")
    
    def delete_transactions(self, transaction_ids):
        """Delete multiple transactions by their IDs."""
        results = []
        for tid in transaction_ids:
            try:
                if self.delete_transaction(tid):
                    results.append({"id": tid, "success": True})
                else:
                    results.append({"id": tid, "success": False, "error": "Transaction not found"})
            except ValueError as e:
                results.append({"id": tid, "success": False, "error": str(e)})
        return results

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
