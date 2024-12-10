import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
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
st.title("Financial Reports & Insights")

# Get transaction data and statistics
stats = transaction_manager.get_summary_stats()
df = transaction_manager.get_transactions_df()

# Financial Overview Section
st.header("Financial Overview")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Current Balance", f"${stats['current_balance']:.2f}")
with col2:
    st.metric("Total Expenses", f"${stats['total_expenses']:.2f}")
with col3:
    st.metric("Total Subscriptions", f"${stats['total_subscriptions']:.2f}")

# Export options
st.subheader("Export Reports")
col1, col2 = st.columns([1, 1])
with col1:
    if stats['monthly_breakdown']:
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
    summary_data = {
        'Metric': ['Total Expenses', 'Total Subscriptions', 'Current Balance'],
        'Amount': [stats['total_expenses'], stats['total_subscriptions'], stats['current_balance']]
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

# Monthly Trends Analysis
st.header("Monthly Trends Analysis")
if not df.empty:
    # Monthly breakdown chart
    monthly_data = pd.DataFrame(list(stats['monthly_breakdown'].items()), columns=['Month', 'Amount'])
    monthly_data['Month'] = pd.to_datetime(monthly_data['Month'] + '-01')
    monthly_data = monthly_data.sort_values('Month')
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_data['Month'],
        y=monthly_data['Amount'],
        mode='lines+markers',
        name='Total Amount',
        line=dict(width=3)
    ))
    
    fig.update_layout(
        title='Monthly Spending Trend',
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Transaction Type Distribution
    st.subheader("Transaction Distribution")
    col1, col2 = st.columns(2)
    
    with col1:
        type_dist = df['type'].value_counts()
        fig_pie = px.pie(
            values=type_dist.values,
            names=type_dist.index,
            title='Transaction Types Distribution'
        )
        st.plotly_chart(fig_pie)
    
    with col2:
        type_amounts = df.groupby('type')['amount'].sum()
        fig_bar = px.bar(
            x=type_amounts.index,
            y=type_amounts.values,
            title='Amount by Transaction Type',
            labels={'x': 'Transaction Type', 'y': 'Total Amount ($)'}
        )
        st.plotly_chart(fig_bar)
    
    # Monthly Stats Table
    st.subheader("Monthly Statistics")
    monthly_stats = df.copy()
    monthly_stats['month'] = pd.to_datetime(monthly_stats['date']).dt.strftime('%Y-%m')
    
    # Create monthly statistics with simpler aggregation
    stats_table = pd.DataFrame({
        'month': sorted(monthly_stats['month'].unique()),
        'Transaction Count': monthly_stats.groupby('month').size(),
        'Total Amount': monthly_stats.groupby('month')['amount'].sum().round(2),
        'Average Amount': monthly_stats.groupby('month')['amount'].mean().round(2)
    })
    
    # Display the statistics
    st.dataframe(stats_table, use_container_width=True)
    
    # Separate transaction type analysis
    st.subheader("Transaction Types by Month")
    type_by_month = df.pivot_table(
        index=pd.to_datetime(df['date']).dt.strftime('%Y-%m'),
        columns='type',
        values='amount',
        aggfunc='count',
        fill_value=0
    ).reset_index()
    st.dataframe(type_by_month, use_container_width=True)

else:
    st.info("No transaction data available for analysis")
