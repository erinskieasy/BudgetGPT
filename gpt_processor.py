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
        if not hasattr(self, 'conversation_history'):
            self.conversation_history = []
            self.last_context = None

        # Update conversation history with the new message and context
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "transactions_context": transactions_context
        })
        self.last_context = transactions_context

        # Build the conversation history for GPT
        conversation_summary = "\n\n".join([
            f"Previous message: {msg['content']}\n"
            f"Context at that time:\n{msg['transactions_context']}"
            for msg in self.conversation_history[-3:]  # Keep last 3 messages for context
        ])

        prompt = f"""
        You are a helpful financial assistant with perfect memory of our conversation.
        Here are the recent messages and their context:

        {conversation_summary}

        Current transactions:
        {transactions_context}

        Latest user message: "{message}"

        Important instructions:
        1. Remember the context from previous messages
        2. If the user refers to transactions mentioned before, use that context
        3. For vague references like "that transaction" or "it", look at the previous messages
        4. Use the transaction amounts and dates to maintain continuity

        Analyze the message and:
        1. If asking about transactions, provide detailed information
        2. If referring to previous transactions, use that context
        3. For modifications, be specific about which transaction

        Return JSON in this format:
        {{
            "message": "Your response, referencing specific transactions",
            "action": null,  # Or include command data if a change is needed:
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
                    "content": "You are a helpful financial assistant with perfect memory. Be specific when referring to transactions and maintain context from previous messages."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Add assistant's response to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": result["message"],
            "transactions_context": transactions_context
        })
        
        return result
    def generate_sql_command(self, action, transactions_context):
        """Generate SQL command for transaction modifications."""
        prompt = f"""
        You are a PostgreSQL expert. Generate a safe SQL command for the following action.
        Current transactions in the database:
        {transactions_context}

        Requested action:
        {json.dumps(action, indent=2)}

        Database schema:
        - Table name: transactions
        - Columns: id, date (date), type (text), description (text), amount (numeric), created_at (timestamp)

        Rules:
        1. Generate precise SQL that will affect only the intended transaction
        2. Use date ranges of ±1 day for date matching to be flexible
        3. Use ILIKE with wildcards for fuzzy description matching
        4. For updates, only include fields that are actually being modified
        5. Return a single SQL command with proper parameter placeholders (%s)
        6. For UPDATE commands:
           - Only update specified fields
           - Use the SET clause only for modified fields
           - Include both date and description in WHERE clause
        7. For DELETE commands:
           - Always include both date and description in WHERE clause
        8. For INSERT commands:
           - Include values for all required fields (date, type, description, amount)
           - created_at should be handled by database default

        Example formats:
        UPDATE: UPDATE transactions SET amount = %s WHERE date BETWEEN %s::date - INTERVAL '1 day' AND %s::date + INTERVAL '1 day' AND description ILIKE %s
        DELETE: DELETE FROM transactions WHERE date BETWEEN %s::date - INTERVAL '1 day' AND %s::date + INTERVAL '1 day' AND description ILIKE %s
        INSERT: INSERT INTO transactions (date, type, description, amount) VALUES (%s, %s, %s, %s)

        Return JSON in this format:
        {{
            "sql": "SQL command with %s placeholders",
            "params": ["list", "of", "parameters"],
            "type": "update|delete|insert"
        }}
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a PostgreSQL expert. Generate precise and safe SQL commands."
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