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
        prompt = f"""
        Extract the following information from this transaction description and return as JSON:
        1. date (in YYYY-MM-DD format):
           - If no date mentioned, use today's date
           - For relative dates like "yesterday", "last week", use appropriate date
           - For partial dates like "jan 1st" or "the 4th", assume current year
           - For month/day without year like "4th of november", assume current year
        2. type (either 'income', 'expense', or 'subscription')
        3. description (a clear, concise summary)
        4. amount (numerical value)

        Current date for reference: {datetime.now().strftime('%Y-%m-%d')}
        Transaction text: {text}

        Response format:
        {{
            "date": "YYYY-MM-DD",
            "type": "expense/subscription",
            "description": "summary",
            "amount": float
        }}

        Examples of date processing:
        - "yesterday" -> date should be yesterday's date
        - "jan 1st" -> should be "2024-01-01" (assuming current year)
        - "4th of november" -> should be "2024-11-04" (assuming current year)
        - No date mentioned -> use today's date ({datetime.now().strftime('%Y-%m-%d')})
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
