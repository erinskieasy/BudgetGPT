import streamlit as st
import plotly.express as px
import pandas as pd
import io
import time
from datetime import datetime
from database import Database
from gpt_processor import GPTProcessor
from transaction_manager import TransactionManager

# Initialize application components
@st.cache_resource
def init_components():
    db = Database()
    gpt = GPTProcessor()
    return TransactionManager(db), gpt

# Page configuration
st.set_page_config(page_title="GPT Budget Tracker", layout="wide")
st.title("GPT Budget Tracker")

# Initialize components
transaction_manager, gpt_processor = init_components()

# Get financial stats
stats = transaction_manager.get_summary_stats()

# Transaction history table and export options
st.subheader("Transaction History")
df = transaction_manager.get_transactions_df()

# Export buttons
if not df.empty:
    col1, col2 = st.columns([1, 6])
    with col1:
        # Create a buffer for CSV data
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="Export CSV",
            data=csv_buffer.getvalue(),
            file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    # Create editable columns
    edited_df = st.data_editor(
        df,
        column_config={
            "id": st.column_config.NumberColumn(
                "ID",
                help="Transaction ID",
                width="small",
                disabled=True,
            ),
            "date": st.column_config.DateColumn(
                "Date",
                help="Transaction date",
                width="medium",
            ),
            "type": st.column_config.SelectboxColumn(
                "Type",
                help="Transaction type",
                width="medium",
                options=["income", "expense", "subscription"],
            ),
            "amount": st.column_config.NumberColumn(
                "Amount",
                help="Transaction amount",
                width="medium",
                format="$%.2f",
                step=0.01,
            ),
            "description": st.column_config.TextColumn(
                "Description",
                help="Transaction description",
                width="large",
                disabled=True,
            ),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
    )
    
    # Check for changes and update the database
    if not df.equals(edited_df):
        for index, row in edited_df.iterrows():
            original_row = df.loc[index]
            for field in ['date', 'type', 'amount']:
                if row[field] != original_row[field]:
                    try:
                        transaction_manager.update_transaction_field(
                            row['id'], field, row[field]
                        )
                        st.success(f"Updated {field} for transaction {row['id']}")
                        time.sleep(0.5)  # Brief pause to show success message
                        st.rerun()  # Refresh to show updated data
                    except Exception as e:
                        st.error(f"Error updating {field}: {str(e)}")
else:
    st.info("No transactions recorded yet")

# Financial summary in columns
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        "Current Balance",
        f"${stats['current_balance']:.2f}",
        delta=None
    )
with col2:
    st.metric("Total Expenses", f"${stats['total_expenses']:.2f}")
with col3:
    st.metric("Total Subscriptions", f"${stats['total_subscriptions']:.2f}")

# Input section below transaction table
# st.subheader("Add Transaction")
input_method = st.radio(
    "Choose input method:",
    ["Text Input", "Receipt Upload"]
)

# Text input section
if input_method == "Text Input":
    text_input = st.chat_input(
        placeholder="What did you buy?"
    )
    
    if text_input:
        with st.spinner("Processing input..."):
            try:
                result = gpt_processor.process_text_input(text_input)
                if isinstance(result, dict) and result.get("action") == "delete":
                    # Handle deletion request
                    results = transaction_manager.delete_transactions(result["transaction_ids"])
                    
                    # Show results
                    successful = [r["id"] for r in results if r["success"]]
                    failed = [(r["id"], r["error"]) for r in results if not r["success"]]
                    
                    if successful:
                        st.success(f"Successfully deleted transactions: {', '.join(map(str, successful))}")
                    if failed:
                        st.error("Failed to delete some transactions:\n" + 
                                "\n".join(f"ID {id}: {error}" for id, error in failed))
                else:
                    # Handle normal transaction
                    transaction_manager.add_transaction(result)
                    st.success("Transaction added successfully!")
                st.rerun()  # Refresh to show the updated transactions
            except Exception as e:
                st.error(f"Error processing input: {str(e)}")

# Receipt upload section
else:
    uploaded_file = st.file_uploader("Choose a receipt image", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file is not None:
        if st.button("Process Receipt"):
            with st.spinner("Processing receipt..."):
                try:
                    image_bytes = uploaded_file.getvalue()
                    transaction_data = gpt_processor.process_receipt_image(image_bytes)
                    transaction_manager.add_transaction(transaction_data)
                    st.success("Receipt processed successfully!")
                except Exception as e:
                    st.error(f"Error processing receipt: {str(e)}")

# Monthly spending chart moved to reports.py
