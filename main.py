import streamlit as st
import plotly.express as px
import pandas as pd
import io
import time
from datetime import datetime
from database import Database
from gpt_processor import GPTProcessor
from transaction_manager import TransactionManager
from serve_static import serve_static_files

# Initialize application components
@st.cache_resource
def init_components():
    db = Database()
    gpt = GPTProcessor()
    return TransactionManager(db), gpt, db

# Page configuration and PWA setup
st.set_page_config(
    page_title="GPT Budget Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Serve static files for PWA
serve_static_files()

# Initialize session state for filters
if 'filter_column' not in st.session_state:
    st.session_state['filter_column'] = "None"
if 'filter_text' not in st.session_state:
    st.session_state['filter_text'] = ""
if 'filter_name' not in st.session_state:
    st.session_state['filter_name'] = ""
if 'saved_filter' not in st.session_state:
    st.session_state['saved_filter'] = "None"

def reset_filter_form():
    st.session_state['filter_column'] = "None"
    st.session_state['filter_text'] = ""
    st.session_state['filter_name'] = ""

# Inject PWA components
pwa_code = """
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#000000">
    <link rel="apple-touch-icon" href="/generated-icon.png">
    <link rel="icon" type="image/png" href="/generated-icon.png">
    <script>
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function() {
                navigator.serviceWorker.register('/sw.js')
                    .then(function(registration) {
                        console.log('ServiceWorker registration successful');
                    }, function(err) {
                        console.log('ServiceWorker registration failed: ', err);
                    });
            });
        }
    </script>
"""
st.markdown(pwa_code, unsafe_allow_html=True)

st.title("GPT Budget Tracker")

# Initialize components
transaction_manager, gpt_processor, db = init_components()

# Sidebar configuration
with st.sidebar:
    st.title("Settings")
    # Get current exchange rate from database
    current_rate = float(db.get_setting('exchange_rate') or 155.0)
    
    exchange_rate = st.number_input(
        "USD to JMD Exchange Rate",
        min_value=100.0,
        max_value=500.0,
        value=current_rate,
        step=0.1,
        help="Set the exchange rate for USD to JMD conversion"
    )
    
    # Update database and GPT processor if rate changes
    if exchange_rate != current_rate:
        db.update_setting('exchange_rate', exchange_rate)
        gpt_processor.set_exchange_rate(exchange_rate)
        st.rerun()  # Refresh the page to reflect the new rate
    else:
        # Always ensure GPT processor has current rate
        gpt_processor.set_exchange_rate(current_rate)

# Get transactions based on current filter
filter_column = st.session_state.get('filter_column', 'None')
filter_text = st.session_state.get('filter_text', '')
df = transaction_manager.get_filtered_transactions_df(filter_column, filter_text)

# Transaction history table and export options
st.subheader("Transaction History")

# Calculate stats based on filtered data
if df.empty:
    stats = {
        'total_expenses': 0,
        'total_subscriptions': 0,
        'current_balance': 0,
        'monthly_breakdown': {}
    }
else:
    stats = {
        'total_expenses': df[df['type'] == 'expense']['amount'].sum(),
        'total_subscriptions': df[df['type'] == 'subscription']['amount'].sum(),
        'current_balance': (
            df[df['type'] == 'income']['amount'].sum() -
            df[df['type'].isin(['expense', 'subscription'])]['amount'].sum()
        ),
        'monthly_breakdown': df.groupby(pd.to_datetime(df['date']).dt.strftime('%Y-%m'))['amount'].sum().to_dict()
    }

# Display transactions if available
if not df.empty:
    # Create editable columns
    edited_df = st.data_editor(
        df,
        column_config={
            "id": st.column_config.NumberColumn(
                "ID",
                help="Transaction ID",
                width=40,
                disabled=True,
            ),
            "date": st.column_config.DateColumn(
                "Date",
                help="Transaction date",
                width=100,
            ),
            "type": st.column_config.SelectboxColumn(
                "Type",
                help="Transaction type",
                width=80,
                options=["income", "expense", "subscription"],
            ),
            "amount": st.column_config.NumberColumn(
                "Amount",
                help="Transaction amount",
                width=80,
                format="$%.2f",
                step=0.01,
            ),
            "description": st.column_config.TextColumn(
                "Description",
                help="Transaction description",
                width=150,
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

def reset_filter_form():
    st.session_state['filter_column'] = "None"
    st.session_state['filter_text'] = ""
    st.session_state['filter_name'] = ""
    st.session_state['saved_filter'] = "None"

def on_filter_change():
    if st.session_state.filter_column == "None":
        st.session_state['filter_text'] = ""
    st.rerun()

def on_saved_filter_change():
    if st.session_state.saved_filter == "None":
        reset_filter_form()
    st.rerun()

# Quick Filters
with st.expander("Quick Filters", expanded=True):
    # Saved Filters Section
    saved_filters = db.get_saved_filters()
    if saved_filters:
        st.subheader("Saved Filters")
        selected_filter = st.selectbox(
            "Select a saved filter",
            ["None"] + [f"{f['name']} ({f['filter_column']}: {f['filter_text']})" for f in saved_filters],
            key="saved_filter",
            on_change=on_saved_filter_change
        )
        
        if selected_filter != "None":
            selected_idx = [f"{f['name']} ({f['filter_column']}: {f['filter_text']})" for f in saved_filters].index(selected_filter)
            filter_data = saved_filters[selected_idx]
            st.session_state.filter_column = filter_data['filter_column']
            st.session_state.filter_text = filter_data['filter_text']
            
            # Delete filter button
            if st.button(f"Delete '{filter_data['name']}'"):
                if db.delete_saved_filter(filter_data['id']):
                    st.success("Filter deleted successfully!")
                    st.rerun()
    
    # Filter inputs
    col1, col2 = st.columns([1, 2])
    with col1:
        st.selectbox(
            "Filter by column",
            ["None", "type", "description", "amount"],
            key="filter_column",
            on_change=on_filter_change
        )
    with col2:
        if st.text_input(
            "Search term",
            key="filter_text",
            placeholder="Enter search term...",
            disabled=st.session_state.filter_column == "None",
            on_change=lambda: st.rerun()
        ):
            st.rerun()
    
    # Save current filter (only show when no saved filter is selected)
    if filter_column != "None" and filter_text and st.session_state.saved_filter == "None":
        save_col1, save_col2 = st.columns([3, 1])
        with save_col1:
            filter_name = st.text_input(
                "Filter name",
                key="filter_name",
                placeholder="Enter a name to save this filter..."
            )
        with save_col2:
            if st.button("Save Filter", key="save_filter_button"):
                if not filter_name:
                    st.error("Please enter a name for the filter")
                else:
                    db.save_filter(filter_name, filter_column, filter_text)
                    st.success(f"Filter '{filter_name}' saved!")
                    # Clear form inputs
                    st.session_state.filter_name = ""
                    st.session_state.filter_column = "None"
                    st.session_state.filter_text = ""
                    st.rerun()

# Financial metrics are now calculated directly from the filtered df earlier in the code
filtered_stats = stats  # Using the stats calculated from the filtered df

# Financial summary in columns
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        "Current Balance",
        f"${filtered_stats['current_balance']:.2f}",
        delta=None
    )
with col2:
    st.metric("Total Expenses", f"${filtered_stats['total_expenses']:.2f}")
with col3:
    st.metric("Total Subscriptions", f"${filtered_stats['total_subscriptions']:.2f}")

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
                if isinstance(result, dict) and result.get("is_deletion"):
                    deletion_type = result.get("deletion_type")
                    ids_to_delete = []
                    
                    if deletion_type == "specific_ids":
                        ids_to_delete = result.get("transaction_ids", [])
                    elif deletion_type == "last_n":
                        n = result.get("n", 1)  # Default to 1 if not specified
                        ids_to_delete = db.get_latest_transaction_ids(limit=n)
                    elif deletion_type == "first_n":
                        n = result.get("n", 1)  # Default to 1 if not specified
                        ids_to_delete = list(reversed(db.get_latest_transaction_ids()))[:n]
                    elif deletion_type == "all":
                        ids_to_delete = db.get_latest_transaction_ids()
                    elif deletion_type == "all_except_last_n":
                        n = result.get("n", 1)  # Default to 1 if not specified
                        all_ids = db.get_latest_transaction_ids()
                        ids_to_delete = all_ids[n:]
                    elif deletion_type == "all_except_ids":
                        except_ids = set(result.get("transaction_ids", []))
                        all_ids = db.get_latest_transaction_ids()
                        ids_to_delete = [id for id in all_ids if id not in except_ids]
                    
                    if ids_to_delete:
                        results = transaction_manager.delete_transactions(ids_to_delete)
                        successful = [r["id"] for r in results if r["success"]]
                        failed = [(r["id"], r["error"]) for r in results if not r["success"]]
                        
                        if successful:
                            st.success(f"Successfully deleted {len(successful)} transaction(s)")
                        if failed:
                            st.error("Failed to delete some transactions:\n" + 
                                    "\n".join(f"ID {id}: {error}" for id, error in failed))
                    else:
                        st.warning("No transactions found to delete")
                else:
                    # Handle multiple transactions
                    transactions = result.get("transactions", [result])
                    for transaction in transactions:
                        transaction_manager.add_transaction(transaction)
                    
                    num_transactions = len(transactions)
                    st.success(f"Successfully added {num_transactions} transaction{'s' if num_transactions > 1 else ''}!")
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
