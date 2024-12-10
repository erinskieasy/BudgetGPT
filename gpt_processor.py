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

    def process_text_input(self, text):
        prompt = f"""
        Analyze the input text and determine if it's a new transaction or a modification command.
        If it's a modification command (delete/update), return a command object.
        If it's a new transaction, extract the transaction details.

        Input text: {text}

        For new transactions, return JSON in this format:
        {{
            "command": "add",
            "transaction": {{
                "date": "YYYY-MM-DD",
                "type": "income/expense/subscription",
                "description": "summary",
                "amount": float
            }}
        }}

        For modification commands, return JSON in this format:
        {{
            "command": "delete/update",
            "criteria": {{
                "date": "YYYY-MM-DD",  # Date of transaction to modify
                "description": "search terms"  # Keywords to identify transaction
            }},
            "updates": {{  # Only for update command
                "date": "YYYY-MM-DD",  # New date if changing date
                "type": "income/expense/subscription",  # New type if changing type
                "description": "new description",  # New description if changing description
                "amount": float  # New amount if changing amount
            }}
        }}

        Example modifications:
        - "Delete the grocery transaction from yesterday"
        - "Change the date of my coffee expense to last Friday"
        - "Update the type of my salary entry to income"
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
