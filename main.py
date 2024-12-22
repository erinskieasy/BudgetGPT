import streamlit as st
import plotly.express as px
import pandas as pd
import time
from datetime import datetime
from database import Database
from gpt_processor import GPTProcessor
from transaction_manager import TransactionManager
from serve_static import serve_static_files
from auth import Auth

# Page configuration must be the first Streamlit command
st.set_page_config(
    page_title="GPT Budget Tracker",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Serve static files for PWA
serve_static_files()

# Initialize authentication
@st.cache_resource
def init_auth():
    return Auth()

auth = init_auth()

# Initialize session state for authentication
if 'user' not in st.session_state:
    st.session_state['user'] = None

def login_user(username, password):
    user = auth.authenticate_user(username, password)
    if user:
        st.session_state['user'] = user
        token = auth.create_access_token({"user_id": user["id"]})
        st.session_state['token'] = token
        return True
    return False

def logout_user():
    # Clear all session state variables
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Reinitialize essential session state variables
    st.session_state['user'] = None
    st.session_state['token'] = None
    st.session_state['filter_column'] = "None"
    st.session_state['filter_text'] = ""
    st.session_state['filter_name'] = ""
    st.session_state['saved_filter'] = "None"
    
    # Force component reinitialization
    st.cache_resource.clear()
    st.rerun()

# Initialize components
@st.cache_resource
def init_components():
    db = Database()
    gpt = GPTProcessor()
    transaction_manager = TransactionManager(db)
    if st.session_state.get('user'):
        transaction_manager.set_user_id(st.session_state['user']['id'])
    return transaction_manager, gpt, db

# Authentication UI
if not st.session_state.get('user'):
    st.title("Login")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                if login_user(username, password):
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            register = st.form_submit_button("Register")

            if register:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    try:
                        user = auth.register_user(new_username, new_password)
                        st.success("Registration successful! Please login.")
                        time.sleep(1)
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error("Registration failed. Please try again.")

    st.stop()

# Initialize session state for filters
# Initialize filter-related session state if not present
for key, default_value in {
    'filter_column': "None",
    'filter_text': "",
    'filter_name': "",
    'saved_filter': "None"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

def reset_filter_form():
    """Reset all filter-related session state variables"""
    # Instead of directly modifying session state, we'll use rerun
    # to reset the state naturally through the widget initialization
    st.cache_resource.clear()
    time.sleep(0.1)  # Small delay to ensure UI updates
    st.rerun()

def handle_saved_filter_change():
    """Handle when a saved filter is selected"""
    if st.session_state.saved_filter == "None":
        # Reset Quick Filters when None is selected
        st.session_state.filter_column = "None"
        st.session_state.filter_text = ""
        return "None", ""
        
    saved_filters = db.get_saved_filters(user_id=st.session_state['user']['id'])
    if saved_filters:
        filter_options = [f"{f['name']} ({f['filter_column']}: {f['filter_text']})" for f in saved_filters]
        if st.session_state.saved_filter in filter_options:
            selected_idx = filter_options.index(st.session_state.saved_filter)
            filter_data = saved_filters[selected_idx]
            return filter_data['filter_column'], filter_data['filter_text']
    return "None", ""

def handle_filter_column_change():
    """Handle when the filter column changes"""
    if st.session_state.filter_column == "None":
        if 'filter_text' in st.session_state:
            st.session_state.filter_text = ""

# Initialize application components
transaction_manager, gpt_processor, db = init_components()

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

# Sidebar configuration
with st.sidebar:
    st.title("Settings")

    # User profile section
    if st.session_state.get('user'):
        st.write(f"Logged in as: {st.session_state['user']['username']}")
        
        # Profile management expander
        with st.expander("Profile Settings", expanded=False):
            with st.form("change_password_form"):
                st.subheader("Change Password")
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_new_password = st.text_input("Confirm New Password", type="password")
                submit_change = st.form_submit_button("Change Password")
                
                if submit_change:
                    if not current_password or not new_password or not confirm_new_password:
                        st.error("Please fill in all password fields")
                    elif new_password != confirm_new_password:
                        st.error("New passwords do not match")
                    else:
                        if auth.change_password(
                            st.session_state['user']['id'],
                            current_password,
                            new_password
                        ):
                            st.success("Password changed successfully!")
                            time.sleep(1)
                            logout_user()  # Force re-login with new password
                        else:
                            st.error("Failed to change password. Please verify your current password.")

        if st.button("Logout"):
            logout_user()

    # Exchange Rate Section
    st.header("Exchange Rate")
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
        st.rerun()
    else:
        gpt_processor.set_exchange_rate(current_rate)

    # Saved Filters Section
    st.header("Saved Filters")
    
    # Personal Filters
    with st.expander("My Filters", expanded=True):
        saved_filters = db.get_saved_filters(user_id=st.session_state['user']['id'])
        if saved_filters:
            filter_options = ["None"] + [f"{f['name']} ({f['filter_column']}: {f['filter_text']})" for f in saved_filters]
            selected_filter = st.selectbox(
                "Select a saved filter",
                options=filter_options,
                key="saved_filter",
                on_change=handle_saved_filter_change
            )
            
            if selected_filter != "None":
                filter_options = [f"{f['name']} ({f['filter_column']}: {f['filter_text']})" for f in saved_filters]
                selected_idx = filter_options.index(selected_filter)
                filter_data = saved_filters[selected_idx]
                
                # Set filter values
                if filter_data['filter_column'] != st.session_state.get('filter_column') or \
                   filter_data['filter_text'] != st.session_state.get('filter_text'):
                    st.session_state.filter_column = filter_data['filter_column']
                    st.session_state.filter_text = filter_data['filter_text']

                col1, col2 = st.columns([1, 1])
                with col1:
                    # Delete filter button
                    delete_button_key = f"delete_filter_{filter_data['id']}"
                    if st.button("Delete Filter", key=delete_button_key):
                        if db.delete_saved_filter(filter_data['id']):
                            st.success("Filter deleted successfully!")
                            st.cache_resource.clear()
                            time.sleep(0.1)
                            st.rerun()
                
                with col2:
                    # Share filter button
                    partners = db.get_partners(st.session_state['user']['id'])
                    if partners:
                        share_with = st.selectbox(
                            "Share with",
                            options=[p['username'] for p in partners],
                            key=f"share_filter_{filter_data['id']}"
                        )
                        if st.button("Share Filter"):
                            partner_id = next(p['id'] for p in partners if p['username'] == share_with)
                            success, error = db.share_filter(
                                filter_data['id'],
                                st.session_state['user']['id'],
                                partner_id
                            )
                            if success:
                                st.success(f"Filter shared with {share_with}")
                            else:
                                st.error(error or "Failed to share filter")
                    else:
                        st.info("Add partners to share filters")

    # Shared Filters
    with st.expander("Shared With Me", expanded=True):
        shared_filters = db.get_shared_filters(st.session_state['user']['id'])
        if shared_filters:
            filter_options = ["None"] + [
                f"{f['name']} (by {f['shared_by']}) - {f['filter_column']}: {f['filter_text']}"
                for f in shared_filters
            ]
            selected_shared = st.selectbox(
                "Select a shared filter",
                options=filter_options,
                key="selected_shared_filter",
                on_change=handle_saved_filter_change  # Use the same handler as personal filters
            )
            
            if selected_shared != "None":
                selected_idx = filter_options.index(selected_shared) - 1  # Adjust for "None" option
                filter_data = shared_filters[selected_idx]
                
                # Set filter values and temporarily switch to partner's transactions
                if filter_data['filter_column'] != st.session_state.get('filter_column') or \
                   filter_data['filter_text'] != st.session_state.get('filter_text'):
                    st.session_state.filter_column = filter_data['filter_column']
                    st.session_state.filter_text = filter_data['filter_text']
                    st.session_state['viewing_partner_id'] = filter_data.get('owner_id')
                    transaction_manager.set_user_id(filter_data.get('owner_id'), temporary=True)
            else:
                # Reset to original user's transactions
                if st.session_state.get('viewing_partner_id'):
                    transaction_manager.restore_user_id()
                    del st.session_state['viewing_partner_id']
                    # Reset all filter forms
                    # Reset filter states
                    if 'filter_column' in st.session_state:
                        st.session_state.filter_column = "None"
                    if 'filter_text' in st.session_state:
                        st.session_state.filter_text = ""
                    if 'filter_name' in st.session_state:
                        st.session_state.filter_name = ""
                    st.rerun()
        else:
            st.info("No filters have been shared with you")

    # Partnerships Section
    with st.expander("Manage Partnerships", expanded=False):
        # Send Partnership Request
        partner_username = st.text_input("Add partner by username")
        if st.button("Send Request"):
            if partner_username:
                partnership_id, error = db.send_partnership_request(
                    st.session_state['user']['id'],
                    partner_username
                )
                if partnership_id:
                    st.success(f"Partnership request sent to {partner_username}")
                else:
                    st.error(error or "Failed to send request")

        # Partnership Requests
        requests = db.get_partnership_requests(st.session_state['user']['id'])
        if requests:
            st.subheader("Partnership Requests")
            for req in requests:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"From: {req['username']}")
                with col2:
                    if st.button("Accept", key=f"accept_{req['id']}"):
                        if db.update_partnership_status(req['id'], st.session_state['user']['id'], 'accepted'):
                            st.success("Partnership accepted!")
                            st.rerun()
                with col3:
                    if st.button("Reject", key=f"reject_{req['id']}"):
                        if db.update_partnership_status(req['id'], st.session_state['user']['id'], 'rejected'):
                            st.success("Partnership rejected!")
                            st.rerun()

        # Current Partners
        partners = db.get_partners(st.session_state['user']['id'])
        if partners:
            st.subheader("Current Partners")
            for partner in partners:
                st.write(f"• {partner['username']}")

# Get all transactions first for total metrics
all_df = transaction_manager.get_transactions_df()
stats = {
    'total_expenses': all_df[all_df['type'] == 'expense']['amount'].sum() if not all_df.empty else 0,
    'total_subscriptions': all_df[all_df['type'] == 'subscription']['amount'].sum() if not all_df.empty else 0,
    'current_balance': (
        all_df[all_df['type'] == 'income']['amount'].sum() -
        all_df[all_df['type'].isin(['expense', 'subscription'])]['amount'].sum()
    ) if not all_df.empty else 0
}

# Get filtered transactions for display
filter_column = st.session_state.get('filter_column', 'None')
filter_text = st.session_state.get('filter_text', '')
df = transaction_manager.get_filtered_transactions_df(filter_column, filter_text)

# Transaction history table and export options
st.subheader("Transaction History")

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

# Input section below transaction table
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

# Quick Filters
with st.expander("Quick Filters", expanded=False):
    # Filter inputs
    col1, col2 = st.columns([1, 2])
    with col1:
        st.selectbox(
            "Filter by column",
            ["None", "type", "description", "amount"],
            key="filter_column",
            on_change=handle_filter_column_change
        )
    with col2:
        st.text_input(
            "Search term",
            key="filter_text",
            placeholder="Enter search term...",
            disabled=st.session_state.filter_column == "None"
        )

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
                    db.save_filter(filter_name, filter_column, filter_text, user_id=st.session_state['user']['id'])
                    st.success(f"Filter '{filter_name}' saved!")
                    # Reset filter form using rerun
                    reset_filter_form()
                    time.sleep(0.5)  # Brief pause to show success message
                    st.rerun()

# Financial metrics are now calculated directly from the filtered df earlier in the code
filtered_stats = stats  # Using the stats calculated from the filtered df

# Financial summary in columns
col1, col2, col3, col4 = st.columns(4)
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
with col4:
    # Calculate filtered balance only if a filter is applied
    filtered_balance = df['amount'].sum() if not df.empty and (filter_column != "None" or filter_text) else 0
    st.metric("Filter Balance", f"${filtered_balance:.2f}")