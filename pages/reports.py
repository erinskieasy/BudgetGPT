import streamlit as st
import plotly.express as px
import pandas as pd
import io
from datetime import datetime
from database import Database
from transaction_manager import TransactionManager

# Initialize components
@st.cache_resource
def init_components():
    db = Database()
    return TransactionManager(db)

transaction_manager = init_components()

# Page configuration
st.title("Financial Reports")

# Get statistics
stats = transaction_manager.get_summary_stats()

# Export options
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if stats['monthly_breakdown']:
        # Export monthly breakdown
        monthly_data = pd.DataFrame(
            list(stats['monthly_breakdown'].items()),
            columns=['Month', 'Amount']
        )
        csv_buffer = io.StringIO()
        monthly_data.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="Export Monthly Data",
            data=csv_buffer.getvalue(),
            file_name=f"monthly_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with col2:
    # Export full financial summary
    summary_data = {
        'Metric': ['Total Expenses', 'Total Subscriptions', 'Current Balance'],
        'Amount': [
            stats['total_expenses'],
            stats['total_subscriptions'],
            stats['current_balance']
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    summary_csv = io.StringIO()
    summary_df.to_csv(summary_csv, index=False)
    
    st.download_button(
        label="Export Summary",
        data=summary_csv.getvalue(),
        file_name=f"financial_summary_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# Monthly breakdown chart
if stats['monthly_breakdown']:
    st.subheader("Monthly Spending Overview")
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
else:
    st.info("No transaction data available for monthly breakdown")
