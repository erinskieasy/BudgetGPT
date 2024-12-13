import base64
import json
from datetime import datetime
from openai import OpenAI
import os

class GPTProcessor:
    def __init__(self):
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.exchange_rate = 155.0  # Default exchange rate
        
    def set_exchange_rate(self, rate):
        """Update the USD to JMD exchange rate"""
        self.exchange_rate = rate

    def process_text_input(self, text):
        # Check if it's a deletion request
        delete_prompt = f"""
        Determine if this is a request to delete transactions and extract all transaction IDs mentioned.
        Examples of delete requests:
        - "Delete transaction 1"
        - "Remove items 5, 7 and 9"
        - "Delete transactions number 11, 13 and 5"
        - "Delete the first transaction"
        
        Text: {text}
        
        Return JSON in this format:
        {{
            "is_deletion": true/false,
            "transaction_ids": [list of numbers] or []
        }}
        """

        # First check if it's a deletion request
        delete_response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": delete_prompt}],
            response_format={"type": "json_object"}
        )
        
        delete_result = json.loads(delete_response.choices[0].message.content)
        if delete_result.get("is_deletion") and delete_result.get("transaction_ids"):
            return {"action": "delete", "transaction_ids": delete_result["transaction_ids"]}

        # If not a deletion request, process as normal transaction
        current_date = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
        Extract ALL transactions from this text and return them as a JSON array. For each transaction, provide:
        1. date (in YYYY-MM-DD format)
           - If a specific date is mentioned, use that date
           - If no date is mentioned, use date: {current_date}
           - If "yesterday" is mentioned, calculate the appropriate date
        2. type (either 'income', 'expense', or 'subscription')
        3. description (a clear, concise summary)
        4. amount (numerical value)
        5. currency (detect if amount is specified in USD/US dollars and convert to JMD at rate of {self.exchange_rate} JMD = 1 USD)

        Transaction text: {text}

        Response format:
        {{
            "transactions": [
                {{
                    "date": "YYYY-MM-DD",
                    "type": "expense/subscription",
                    "description": "summary",
                    "amount": float,
                    "original_currency": "JMD/USD"
                }},
                ...
            ]
        }}

        Examples:
        Input: "today i bought gas for $500 and beer for $1000"
        {{
            "transactions": [
                {{
                    "date": "{current_date}",
                    "type": "expense",
                    "description": "Gas",
                    "amount": 500.00,
                    "original_currency": "JMD"
                }},
                {{
                    "date": "{current_date}",
                    "type": "expense",
                    "description": "Beer",
                    "amount": 1000.00,
                    "original_currency": "JMD"
                }}
            ]
        }}

        Input: "yesterday I spent $20 USD on lunch and $30 USD on dinner"
        {{
            "transactions": [
                {{
                    "date": "2024-12-12",
                    "type": "expense",
                    "description": "Lunch (converted from $20 USD)",
                    "amount": {20 * self.exchange_rate},
                    "original_currency": "USD"
                }},
                {{
                    "date": "2024-12-12",
                    "type": "expense",
                    "description": "Dinner (converted from $30 USD)",
                    "amount": {30 * self.exchange_rate},
                    "original_currency": "USD"
                }}
            ]
        }}

        Note: 
        - If the amount is in USD/US dollars, add a note about the conversion in the description
        - Split the input into individual transactions when multiple items are mentioned
        - Use the same date for all transactions unless specified otherwise
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)

    def process_receipt_image(self, image_data):
        # Convert the image data to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        prompt = """
        Extract the following information from this receipt image and return as JSON:
        1. date (in YYYY-MM-DD format)
        2. type (always 'expense' for receipts)
        3. description (main items or store name)
        4. amount (total amount)

        Return format:
        {
            "date": "YYYY-MM-DD",
            "type": "expense",
            "description": "summary",
            "amount": float
        }
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)
