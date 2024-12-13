import base64
import json
from datetime import datetime, timedelta
from openai import OpenAI
import os

class GPTProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.exchange_rate = 155.0  # Default exchange rate
        
    def set_exchange_rate(self, rate):
        """Update the USD to JMD exchange rate"""
        self.exchange_rate = rate

    def process_text_input(self, text):
        # Check if it's a deletion request
        delete_prompt = f"""
        Analyze if this is a request to delete transactions and determine the deletion parameters.
        
        Examples of delete requests and their interpretations:
        1. "Delete transaction 1" 
           → specific ID deletion
        2. "Remove items 5, 7 and 9" 
           → multiple specific IDs deletion
        3. "Delete the last 3 transactions" 
           → last N transactions deletion
        4. "Delete all transactions" 
           → all transactions deletion
        5. "Delete the first transaction" 
           → first transaction deletion
        6. "Delete transactions number 11, 13 and 5" 
           → multiple specific IDs deletion
        7. "Delete all transactions except the last one" 
           → all except last N deletion
        8. "Remove all except number 5, 7 and 10" 
           → all except specific IDs deletion
        9. "Delete the last 3" 
           → last N transactions deletion
        10. "Remove all except the last 3" 
           → all except last N deletion
        
        Text: {text}
        
        Return JSON in this format:
        {{
            "is_deletion": true/false,
            "deletion_type": "specific_ids" | "last_n" | "first_n" | "all" | "all_except_last_n" | "all_except_ids" | null,
            "transaction_ids": [list of specific IDs] or [],
            "n": number or null (for last_n, first_n, or all_except_last_n types)
        }}
        """

        # First check if it's a deletion request
        delete_response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": delete_prompt}],
            response_format={"type": "json_object"}
        )
        
        delete_result = json.loads(delete_response.choices[0].message.content)
        if delete_result.get("is_deletion"):
            return delete_result

        # If not a deletion request, process as normal transaction
        current_date = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        prompt = f"""
        Extract ALL transactions from this text and return them as a JSON array. For each transaction, provide:
        1. date (in YYYY-MM-DD format)
           - If a specific date is mentioned, use that date
           - If no date is mentioned, use date: {current_date}
           - If "yesterday" is mentioned, use date: {yesterday}
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
                    "type": "expense/subscription/income",
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
                    "date": "{yesterday}",
                    "type": "expense",
                    "description": "Lunch (converted from $20 USD)",
                    "amount": {20 * self.exchange_rate},
                    "original_currency": "USD"
                }},
                {{
                    "date": "{yesterday}",
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
