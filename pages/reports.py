import streamlit as st
import plotly.express as px
import pandas as pd
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
