import json
import os
import base64
from datetime import datetime
from openai import OpenAI
import pandas as pd

class GPTProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024

    def process_text_input(self, text):
        """Process natural language input into structured transaction data."""
        prompt = f"""
        Convert this transaction-related text into a structured command.
        Text: "{text}"
        
        Return JSON in this format for add/update/delete commands:
        For adding: {{"command": "add", "transaction": {{"date": "YYYY-MM-DD", "type": "expense|income|subscription", "description": "string", "amount": float}}}}
        For updating: {{"command": "update", "criteria": {{"date": "YYYY-MM-DD", "description": "search text"}}, "updates": {{"date?": "YYYY-MM-DD", "type?": "string", "description?": "string", "amount?": float}}}}
        For deleting: {{"command": "delete", "criteria": {{"date": "YYYY-MM-DD", "description": "search text"}}}}
        
        Current date if needed: {datetime.now().strftime('%Y-%m-%d')}
        Use semantic understanding to determine the command type and extract relevant details.
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)

    def process_receipt_image(self, image_bytes):
        """Process a receipt image and extract transaction information."""
        # Convert image bytes to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt = """
        Analyze this receipt image and extract the following information:
        - Total amount
        - Date
        - Description (store name or purpose)
        
        Return the information in this JSON format:
        {
            "date": "YYYY-MM-DD",
            "type": "expense",
            "description": "extracted description",
            "amount": float
        }
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a receipt processing assistant."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate the extracted data
        try:
            # Ensure date is in correct format
            datetime.strptime(result['date'], '%Y-%m-%d')
            # Ensure amount is a float
            result['amount'] = float(result['amount'])
            # Set type as expense for receipts
            result['type'] = 'expense'
            # Ensure description exists
            if not result.get('description'):
                raise ValueError("No description found in receipt")
        except (ValueError, KeyError) as e:
            raise ValueError(f"Failed to process receipt: {str(e)}")
            
        return result

    def process_chat_message(self, message, transactions_df):
        """Process a chat message and generate an appropriate response and action."""
        prompt = f"""
        You are a financial assistant helping users manage their transactions.
        
        Current transactions in the database (with row numbers):
        {transactions_df.to_string() if not transactions_df.empty else "No transactions"}
        
        User message: {message}
        
        Analyze the message and:
        1. If it's asking for information, provide a helpful response
        2. If it's requesting a transaction modification, use one of these functions:
           a) Add new transaction:
              - Command: "add"
              - Needs: date, type (expense/income/subscription), description, amount
           
           b) Delete transaction by row:
              - Command: "delete"
              - Needs: row_number from table
           
           c) Update transaction by row:
              - Command: "update"
              - Needs: row_number from table
              - Can update: date, type, description, amount

        Return JSON in this format:
        {{
            "message": "Your response to the user",
            "action": {{
                "command": "add|update|delete",
                ... command specific fields ...
            }} or null if no action needed
        }}
        
        Important:
        - Use exact row numbers from the table (they start at 1)
        - For updates and deletes, reference the specific row number
        - Format dates as YYYY-MM-DD
        - Transaction types must be: expense, income, or subscription
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful financial assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Process the command if present
        if result.get('action'):
            command = result['action'].get('command')
            
            # Validate row numbers for update and delete commands
            if command in ['update', 'delete']:
                row_number = result['action'].get('row_number')
                if not row_number or not isinstance(row_number, int) or row_number < 1:
                    result['action'] = None
                    result['message'] += "\nI couldn't determine which transaction to modify. Could you specify which row number?"
                elif transactions_df.empty or row_number > len(transactions_df):
                    result['action'] = None
                    result['message'] += f"\nRow number {row_number} doesn't exist in the transaction table."
            
            # Validate add transaction data
            elif command == 'add':
                transaction = result['action'].get('transaction', {})
                required_fields = ['date', 'type', 'description', 'amount']
                if not all(field in transaction for field in required_fields):
                    result['action'] = None
                    result['message'] += "\nI couldn't get all the required information for adding a transaction."
        
        return result

    def process_transaction_command(self, user_intent, transactions_df):
        """
        Process user intent and return appropriate transaction command.
        
        Available Functions:
        1. add_transaction(transaction_data):
           - Adds a new transaction
           - Required fields: date (YYYY-MM-DD), type (expense/income/subscription), description, amount
        
        2. delete_transaction_by_row(row_number):
           - Deletes transaction by its row number in the table
           - Required: row_number (int)
        
        3. update_transaction_by_row(row_number, updates):
           - Updates transaction by its row number
           - Required: row_number (int)
           - updates can include: date, type, description, amount
        
        Example commands:
        {
            "command": "add",
            "transaction": {
                "date": "2024-12-10",
                "type": "expense",
                "description": "Grocery shopping",
                "amount": 50.00
            }
        }
        
        {
            "command": "delete",
            "row_number": 1  # Deletes first transaction in table
        }
        
        {
            "command": "update",
            "row_number": 1,  # Updates first transaction in table
            "updates": {
                "amount": 75.00,
                "description": "Updated description"
            }
        }
        """
        prompt = f"""
        You are a transaction processing assistant. Analyze the user's intent and the current transactions table to generate the appropriate command.
        
        Current transactions (with row numbers):
        {transactions_df.to_string() if not transactions_df.empty else "No transactions"}
        
        User intent: {user_intent}
        
        Generate a command that uses one of these functions:
        1. Add new transaction:
           - Command: "add"
           - Needs: date, type (expense/income/subscription), description, amount
        
        2. Delete transaction by row:
           - Command: "delete"
           - Needs: row_number from table
        
        3. Update transaction by row:
           - Command: "update"
           - Needs: row_number from table
           - Can update: date, type, description, amount
        
        Return the command as a JSON object with these fields:
        - command: "add", "delete", or "update"
        - For add: include "transaction" object with all required fields
        - For delete: include "row_number"
        - For update: include "row_number" and "updates" object with fields to change
        
        Example: See function documentation above.
        
        Important:
        - Row numbers start at 1
        - Use exact row numbers from the table
        - For updates and deletes, user must reference existing transaction
        - Dates must be in YYYY-MM-DD format
        - Transaction types must be: expense, income, or subscription
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a transaction processing assistant. Generate precise commands based on user intent."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)

    def find_matching_transaction(self, description, transactions):
        """Find the best matching transaction based on semantic similarity."""
        if not transactions:
            return None
            
        transactions_list = "\n".join(
            f"{t['date']} | {t['description']} | ${float(t['amount']):.2f}"
            for t in transactions
        )
        
        print(f"Processing transactions list:\n{transactions_list}")
        
        prompt = f"""
        You are a semantic matching expert with expertise in financial transactions.
        Find the most semantically similar transaction from the list based on meaning,
        not exact wording. Be very lenient with matching.

        User's search: "{description}"

        Available transactions to search through:
        {transactions_list}

        Matching rules (BE VERY LENIENT):
        1. Prioritize semantic meaning over exact words
        2. Common equivalent expressions:
           - Any mention of "gas", "fuel", "gasoline", "fill up", "station" are related to gas purchases
           - Words like "bought", "purchased", "paid for", "got" are equivalent
           - Numbers and amounts don't need to match
        3. Focus on the core concept (e.g., "gas purchase" = "bought gas")
        4. Word order and exact phrasing don't matter
        5. Confidence scoring (BE GENEROUS):
           - High (0.7-1.0): Core concept matches (e.g., both about gas)
           - Medium (0.4-0.6): Related concepts
           - Low (0.2-0.3): Possible but uncertain relation
           - Zero (0.0): Completely unrelated

        Return JSON in this format:
        {{
            "best_match": {{
                "date": "YYYY-MM-DD",
                "description": "exact description from list",
                "confidence": float  # between 0 and 1
            }}
        }}

        If no good match is found, set confidence to 0.
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a semantic matching expert. Find the best matching transaction based on meaning, not just text similarity."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get('best_match')