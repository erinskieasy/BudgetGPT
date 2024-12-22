import streamlit as st
from database import Database
import pandas as pd
from datetime import datetime

# Initialize database
db = Database()

# Page title
st.title("Admin Dashboard")

# Check if user is logged in and has admin privileges
if not st.session_state.get('user'):
    st.error("Please log in to access this page.")
    st.stop()

if st.session_state['user']['username'] != 'erinskie':
    st.error("You do not have permission to access this page.")
    st.stop()

# Display all transactions
st.header("All Transactions")

try:
    # Get all transactions from database
    with db.conn.cursor() as cur:
        cur.execute("""
            SELECT 
                t.id,
                t.date,
                t.type,
                t.description,
                t.amount,
                t.user_id,
                u.username
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.id
            ORDER BY t.date DESC, t.created_at DESC
        """)
        columns = ['id', 'date', 'type', 'description', 'amount', 'user_id', 'username']
        results = cur.fetchall()
        
        if results:
            # Convert to DataFrame
            df = pd.DataFrame(results, columns=columns)
            
            # Format the data
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df['amount'] = df['amount'].apply(lambda x: f"${x:,.2f}")
            
            # Display as table
            st.dataframe(
                df,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width=50),
                    "date": st.column_config.TextColumn("Date", width=100),
                    "type": st.column_config.TextColumn("Type", width=100),
                    "description": st.column_config.TextColumn("Description", width=200),
                    "amount": st.column_config.TextColumn("Amount", width=100),
                    "username": st.column_config.TextColumn("User", width=100),
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Export functionality
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Export to CSV",
                csv,
                f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("No transactions found in the database.")
            
except Exception as e:
    st.error(f"Error fetching transactions: {str(e)}")
