from datetime import datetime
import pandas as pd

class TransactionManager:
    def __init__(self, database, gpt_processor=None):
        self.db = database
        self.gpt = gpt_processor

    def process_command(self, command_data):
        """
        Process a command by routing it to the appropriate function.
        Available commands:
        
        1. add_transaction:
           Input: {
               "command": "add",
               "transaction": {
                   "date": "YYYY-MM-DD",
                   "type": "expense|income|subscription",
                   "description": "string",
                   "amount": float
               }
           }
           
        2. delete_transaction:
           Input: {
               "command": "delete",
               "row_number": int  # Row number from the displayed table
           }
           
        3. update_transaction:
           Input: {
               "command": "update",
               "row_number": int,  # Row number from the displayed table
               "updates": {  # Only include fields that need updating
                   "date": "YYYY-MM-DD",  # optional
                   "type": "expense|income|subscription",  # optional
                   "description": "string",  # optional
                   "amount": float  # optional
               }
           }
        """
        try:
            command = command_data.get('command', '').lower()
            print(f"Processing command: {command} with data: {command_data}")  # Debug log
            
            if command == 'add':
                transaction = command_data.get('transaction', {})
                if not all(k in transaction for k in ['date', 'type', 'description', 'amount']):
                    raise ValueError("Missing required fields in transaction data")
                return self.add_transaction(transaction)
                
            elif command == 'delete':
                row_number = command_data.get('row_number')
                if not isinstance(row_number, int) or row_number < 1:
                    raise ValueError("Invalid row number for delete command")
                return self.delete_transaction_by_row(row_number)
                
            elif command == 'update':
                row_number = command_data.get('row_number')
                updates = command_data.get('updates', {})
                if not isinstance(row_number, int) or row_number < 1:
                    raise ValueError("Invalid row number for update command")
                if not updates:
                    raise ValueError("No updates provided")
                return self.update_transaction_by_row(row_number, updates)
                
            else:
                raise ValueError(f"Unknown command: {command}")
                
        except (ValueError, KeyError) as e:
            print(f"Error processing command: {str(e)}")  # Debug log
            raise ValueError(f"Invalid command data: {str(e)}")

    def delete_transaction_by_row(self, row_number):
        """
        Delete a transaction by its row number in the displayed table.
        
        Parameters:
        - row_number (int): The row number from the displayed transaction table (1-based indexing)
        
        Returns:
        - bool: True if successful
        
        Example command for GPT:
        {
            "command": "delete",
            "row_number": 1  # Delete the first transaction in the table
        }
        """
        if not isinstance(row_number, int) or row_number < 1:
            raise ValueError("Invalid row number. Must be a positive integer.")
            
        df = self.get_transactions_df()
        if df.empty or row_number > len(df):
            raise ValueError(f"Row number {row_number} does not exist in the transaction table.")
            
        # Get the transaction details from the DataFrame
        transaction = df.iloc[row_number - 1]
        
        with self.db.conn.cursor() as cur:
            cur.execute("""
                DELETE FROM transactions
                WHERE date = %s AND description = %s AND amount = %s
                RETURNING id;
            """, (transaction['date'], transaction['description'], transaction['amount']))
            self.db.conn.commit()
            if cur.rowcount == 0:
                raise ValueError("Failed to delete transaction. Please try again.")
        return True

    def update_transaction_by_row(self, row_number, updates):
        """
        Update a transaction by its row number in the displayed table.
        
        Parameters:
        - row_number (int): The row number from the displayed transaction table (1-based indexing)
        - updates (dict): Dictionary containing the fields to update. Can include:
            - date (str): New date in 'YYYY-MM-DD' format
            - type (str): New type ('expense', 'income', or 'subscription')
            - description (str): New description
            - amount (float): New amount
        
        Returns:
        - bool: True if successful
        
        Example command for GPT:
        {
            "command": "update",
            "row_number": 1,  # Update the first transaction in the table
            "updates": {
                "amount": 50.00,
                "description": "Updated description"
            }
        }
        """
        if not isinstance(row_number, int) or row_number < 1:
            raise ValueError("Invalid row number. Must be a positive integer.")
            
        df = self.get_transactions_df()
        if df.empty or row_number > len(df):
            raise ValueError(f"Row number {row_number} does not exist in the transaction table.")
            
        # Get the transaction to update
        transaction = df.iloc[row_number - 1]
        
        # Validate updates
        if 'date' in updates:
            try:
                updates['date'] = datetime.strptime(updates['date'], '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
                
        if 'type' in updates and updates['type'] not in ['expense', 'income', 'subscription']:
            raise ValueError("Invalid transaction type")
            
        if 'amount' in updates:
            try:
                updates['amount'] = float(updates['amount'])
            except ValueError:
                raise ValueError("Invalid amount format")
                
        # Build the SQL update
        set_clauses = []
        params = []
        for field, value in updates.items():
            set_clauses.append(f"{field} = %s")
            params.append(value)
            
        # Add WHERE clause parameters
        params.extend([transaction['date'], transaction['description'], transaction['amount']])
        
        with self.db.conn.cursor() as cur:
            cur.execute(f"""
                UPDATE transactions 
                SET {', '.join(set_clauses)}
                WHERE date = %s AND description = %s AND amount = %s
                RETURNING id;
            """, tuple(params))
            self.db.conn.commit()
            if cur.rowcount == 0:
                raise ValueError("Failed to update transaction. Please try again.")
        return True

    def add_transaction(self, transaction_data):
        # Validate and process the transaction data
        try:
            print(f"DEBUG: Adding transaction with data: {transaction_data}")  # Debug log
            
            date = datetime.strptime(transaction_data['date'], '%Y-%m-%d').date()
            print(f"DEBUG: Parsed date: {date}")  # Debug log
            
            amount = float(transaction_data['amount'])
            print(f"DEBUG: Parsed amount: {amount}")  # Debug log
            
            type_trans = transaction_data['type'].lower()
            print(f"DEBUG: Transaction type: {type_trans}")  # Debug log
            
            description = transaction_data['description']
            print(f"DEBUG: Description: {description}")  # Debug log

            # Validate transaction type
            if type_trans not in ['expense', 'subscription', 'income']:
                raise ValueError("Invalid transaction type")

            # Add to database
            result = self.db.add_transaction(date, type_trans, description, amount)
            print(f"DEBUG: Database add result: {result}")  # Debug log
            return result
            
        except (ValueError, KeyError) as e:
            error_msg = f"Invalid transaction data: {str(e)}"
            print(f"DEBUG: Error in add_transaction: {error_msg}")  # Debug log
            raise ValueError(error_msg)

    def get_transactions_df(self):
        """
        Get transactions as a DataFrame with row numbers.
        The row numbers can be used by GPT to identify specific transactions for updates or deletions.
        """
        transactions = self.db.get_transactions()
        if not transactions:
            return pd.DataFrame(columns=['row', 'date', 'type', 'description', 'amount'])
        
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date']).dt.date
        # Add row numbers starting from 1
        df.insert(0, 'row', range(1, len(df) + 1))
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
