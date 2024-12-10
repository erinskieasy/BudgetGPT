import json
import os
from datetime import datetime
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
class GPTProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-4o"

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
        """Process an uploaded receipt image and extract transaction details."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract transaction details from this receipt image. Include total amount, date, and merchant/description."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_bytes}"}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return {
            "date": datetime.now().strftime('%Y-%m-%d'),  # Default to today if not found
            "type": "expense",
            "description": result.get('merchant', 'Receipt purchase'),
            "amount": float(result.get('amount', 0))
        }

    def find_matching_transaction(self, description, transactions):
        """Find the best matching transaction based on semantic similarity."""
        if not transactions:
            return None
            
        transactions_list = "\n".join(
            f"{t['date']} | {t['description']} | ${float(t['amount']):.2f}"
            for t in transactions
        )
        
        prompt = f"""
        You are a semantic matching expert. Given a user's description of a transaction,
        find the most semantically similar transaction from the available list.

        User's description: "{description}"

        Available transactions (date | description | amount):
        {transactions_list}

        Consider these matching rules:
        1. Focus on semantic meaning, not exact text matching
        2. "gas purchase", "bought gas", "filled up gas tank", "gas station" are semantically similar
        3. Match key concepts and intentions, not just words
        4. Consider merchant names, purchase types, and general descriptions
        5. Assign high confidence (0.8-1.0) for clear semantic matches
        6. Assign medium confidence (0.5-0.7) for probable matches
        7. Assign low confidence (0.0-0.4) for weak or uncertain matches

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