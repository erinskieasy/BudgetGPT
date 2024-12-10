import streamlit as st
import plotly.express as px
import pandas as pd
import io
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

# Sidebar for input methods
st.sidebar.title("Add Transaction")
input_method = st.sidebar.radio(
    "Choose input method:",
    ["Text Input", "Receipt Upload"]
)

# Text input section
if input_method == "Text Input":
    st.sidebar.subheader("Enter Transaction Details")
    text_input = st.sidebar.text_area(
        "Describe your transaction:",
        placeholder="Example: Spent $45.99 at Grocery Store yesterday"
    )
    
    if st.sidebar.button("Process Transaction"):
        if text_input:
            with st.spinner("Processing transaction..."):
                try:
                    transaction_data = gpt_processor.process_text_input(text_input)
                    transaction_manager.add_transaction(transaction_data)
                    st.sidebar.success("Transaction added successfully!")
                except Exception as e:
                    st.sidebar.error(f"Error processing transaction: {str(e)}")
        else:
            st.sidebar.warning("Please enter a transaction description")

# Receipt upload section
else:
    st.sidebar.subheader("Upload Receipt")
    uploaded_file = st.sidebar.file_uploader("Choose a receipt image", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file is not None:
        if st.sidebar.button("Process Receipt"):
            with st.spinner("Processing receipt..."):
                try:
                    image_bytes = uploaded_file.getvalue()
                    transaction_data = gpt_processor.process_receipt_image(image_bytes)
                    transaction_manager.add_transaction(transaction_data)
                    st.sidebar.success("Receipt processed successfully!")
                except Exception as e:
                    st.sidebar.error(f"Error processing receipt: {str(e)}")

# Main content area
col1, col2 = st.columns([2, 1])

# Transaction history table
with col1:
    st.subheader("Transaction History")
    df = transaction_manager.get_transactions_df()
    if not df.empty:
        st.dataframe(
            df[['date', 'type', 'description', 'amount']],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No transactions recorded yet")

# Financial summary
with col2:
    st.subheader("Financial Overview")
    stats = transaction_manager.get_summary_stats()
    
    # Display current balance
    st.metric(
        "Current Balance",
        f"${stats['current_balance']:.2f}",
        delta=None
    )
    
    # Display expenses and subscriptions
    col_exp, col_sub = st.columns(2)
    with col_exp:
        st.metric("Total Expenses", f"${stats['total_expenses']:.2f}")
    with col_sub:
        st.metric("Total Subscriptions", f"${stats['total_subscriptions']:.2f}")

# Monthly breakdown chart
if stats['monthly_breakdown']:
    st.subheader("Monthly Spending")
    monthly_data = pd.DataFrame(
        list(stats['monthly_breakdown'].items()),
        columns=['Month', 'Amount']
    )
    fig = px.bar(
        monthly_data,
        x='Month',
        y='Amount',
        title='Monthly Spending Overview'
    )
    st.plotly_chart(fig, use_container_width=True)
