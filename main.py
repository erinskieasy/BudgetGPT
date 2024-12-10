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
    return TransactionManager(db, gpt), gpt

# Page configuration
st.set_page_config(page_title="GPT Budget Tracker", layout="wide")
st.title("GPT Budget Tracker")

# Initialize components
transaction_manager, gpt_processor = init_components()

# Initialize chat history in session state if it doesn't exist
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Sidebar for input methods
st.sidebar.title("Add Transaction")
input_method = st.sidebar.radio(
    "Choose input method:",
    ["Chat Assistant", "Receipt Upload"]
)

# Chat interface section
if input_method == "Chat Assistant":
    # Display current transactions
    st.subheader("Current Transactions")
    df = transaction_manager.get_transactions_df()
    if not df.empty:
        st.dataframe(
            df[['date', 'type', 'description', 'amount']],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No transactions recorded yet")

    # Display chat history
    st.subheader("Chat with GPT Assistant")
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    if prompt := st.chat_input("Chat about your transactions..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Get current transactions for context
        transactions_df = transaction_manager.get_transactions_df()
        transactions_context = transactions_df.to_string() if not transactions_df.empty else "No transactions yet"
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Process the chat message
                    response = gpt_processor.process_chat_message(prompt, transactions_context)
                    
                    # Display the response
                    st.write(response['message'])
                    
                    # Add assistant's response to chat history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response['message']
                    })
                    
                    # If there's a suggested action, ask for confirmation
                    if 'action' in response and response['action']:
                        # Store the action in session state
                        st.session_state.pending_action = response['action']
                        if st.button("Apply this change?"):
                            try:
                                # Process the command
                                if transaction_manager.process_command(st.session_state.pending_action):
                                    st.success("Changes applied successfully!")
                                    # Clear the pending action and chat history to refresh the context
                                    st.session_state.pending_action = None
                                    # Force refresh to show updated data
                                    st.experimental_rerun()  # Using experimental_rerun for more reliable refresh
                                else:
                                    st.error("Failed to apply changes. Please try again.")
                            except Exception as e:
                                st.error(f"Failed to apply changes: {str(e)}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

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
