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

    def process_chat_message(self, message, transactions_context):
        """Process a chat message about transactions and determine appropriate actions."""
        prompt = f"""
        You are a helpful financial assistant. Help the user manage their transactions.
        The user is chatting with you about their transactions. Below are the current transactions:

        {transactions_context}

        User message: "{message}"

        Analyze the user's message and:
        1. If they're asking about transactions, provide helpful information
        2. If they want to modify transactions, suggest specific changes
        3. If they want to add new transactions, help format the data

        Return JSON in this format:
        {{
            "message": "Your helpful response to the user",
            "action": null  # Or include command data if a change is needed:
            # For adding: {{"command": "add", "transaction": {{"date": "YYYY-MM-DD", "type": "expense|income|subscription", "description": "string", "amount": float}}}}
            # For updating: {{"command": "update", "criteria": {{"date": "YYYY-MM-DD", "description": "string"}}, "updates": {{"date?": "YYYY-MM-DD", "type?": "string", "description?": "string", "amount?": float}}}}
            # For deleting: {{"command": "delete", "criteria": {{"date": "YYYY-MM-DD", "description": "string"}}}}
        }}
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful financial assistant. Be friendly and clear in your responses."
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