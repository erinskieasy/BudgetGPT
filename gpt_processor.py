import json
import os
import base64
from datetime import datetime
from openai import OpenAI
import pandas as pd

class GPTProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        if not os.environ.get('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024

    def process_chat_message(self, message, transactions_df):
        """Process a chat message and generate an appropriate response and action."""
        prompt = f"""
        You are a financial assistant helping users manage their transactions.
        
        Current transactions (with row numbers):
        {transactions_df.to_string() if not transactions_df.empty else "No transactions"}
        
        User message: {message}
        
        Analyze the message and:
        1. If it's asking for information, provide a helpful response
        2. If it's requesting a transaction modification, determine the type and extract details:
        
           For adding transactions:
           - Command: "add"
           - Return format:
              {{
                  "command": "add",
                  "transaction": {{
                      "date": "YYYY-MM-DD",
                      "type": "expense|income|subscription",
                      "description": "string",
                      "amount": float
                  }}
              }}
           
           For deleting transactions:
           - Command: "delete"
           - Return format:
              {{
                  "command": "delete",
                  "row_number": int  # The row number from the table
              }}
           
           For updating transactions:
           - Command: "update"
           - Return format:
              {{
                  "command": "update",
                  "row_number": int,  # The row number from the table
                  "updates": {{  # Only include fields that should be updated
                      "date?": "YYYY-MM-DD",
                      "type?": "expense|income|subscription",
                      "description?": "string",
                      "amount?": float
                  }}
              }}

        Return this exact JSON format:
        {{
            "message": "Your response to the user explaining what you understood and what action will be taken",
            "action": {{
                "command": "add|update|delete",
                ... command specific fields as shown above ...
            }} or null if no action needed
        }}
        
        Important rules:
        1. Always use today's date ({datetime.now().strftime('%Y-%m-%d')}) if no date is specified
        2. Row numbers start at 1 and must exist in the current table
        3. For expenses and subscriptions, make sure the amount is positive (it will be treated as negative internally)
        4. Amounts should be parsed as float values
        5. If the user mentions "subscription" or "recurring", use type "subscription"
        6. If unsure about any required field, ask for clarification instead of guessing
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful financial assistant that processes transaction commands."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate the action if present
            if result.get('action'):
                command = result['action'].get('command')
                
                if command == 'add':
                    # Validate required fields for add
                    transaction = result['action'].get('transaction', {})
                    required_fields = ['date', 'type', 'description', 'amount']
                    if not all(field in transaction for field in required_fields):
                        result['action'] = None
                        result['message'] = "I couldn't get all the required information. Please provide the date, type (expense/income/subscription), description, and amount."
                    else:
                        # Ensure amount is float
                        try:
                            result['action']['transaction']['amount'] = float(transaction['amount'])
                        except (TypeError, ValueError):
                            result['action'] = None
                            result['message'] = "The amount provided is not a valid number. Please specify a valid amount."
                
                elif command in ['update', 'delete']:
                    # Validate row number
                    row_number = result['action'].get('row_number')
                    if not isinstance(row_number, int) or row_number < 1:
                        result['action'] = None
                        result['message'] = "I couldn't determine which transaction to modify. Please specify a valid row number."
                    elif transactions_df.empty or row_number > len(transactions_df):
                        result['action'] = None
                        result['message'] = f"Row number {row_number} doesn't exist in the transaction table."
                    
                    # For updates, validate the updates object
                    if command == 'update' and result['action']:
                        updates = result['action'].get('updates', {})
                        if not updates:
                            result['action'] = None
                            result['message'] = "No updates were specified. Please specify what you want to change."
                        else:
                            # Validate amount if present
                            if 'amount' in updates:
                                try:
                                    updates['amount'] = float(updates['amount'])
                                except (TypeError, ValueError):
                                    result['action'] = None
                                    result['message'] = "The new amount is not a valid number. Please specify a valid amount."
            
            return result
        except Exception as e:
            return {
                "message": f"I encountered an error while processing your request: {str(e)}",
                "action": None
            }

    def process_receipt_image(self, image_bytes):
        """Process a receipt image and extract transaction information."""
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt = """
        Analyze this receipt image and extract:
        1. Total amount
        2. Date
        3. Store name or description
        
        Return JSON format:
        {
            "date": "YYYY-MM-DD",
            "type": "expense",
            "description": "store name or purpose",
            "amount": float
        }
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate the extracted data
            if 'date' in result:
                datetime.strptime(result['date'], '%Y-%m-%d')
            else:
                result['date'] = datetime.now().strftime('%Y-%m-%d')
                
            result['amount'] = float(result['amount'])
            result['type'] = 'expense'
            
            if not result.get('description'):
                raise ValueError("No description found in receipt")
                
            return result
        except Exception as e:
            raise ValueError(f"Failed to process receipt: {str(e)}")
