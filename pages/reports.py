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
            title='Transaction Types Distribution',
            hole=0.4,  # Creates a donut chart
            labels={'label': 'Transaction Type', 'value': 'Count'},
            hover_data=['Percentage']  # Add percentage to hover info
        )
        fig_pie.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate="<b>%{label}</b><br>" +
                         "Count: %{value}<br>" +
                         "Percentage: %{percent}<br><extra></extra>"
        )
        st.plotly_chart(fig_pie)
    
    with col2:
        type_amounts = df.groupby('type')['amount'].sum()
        fig_bar = px.bar(
            x=type_amounts.index,
            y=type_amounts.values,
            title='Amount by Transaction Type',
            labels={'x': 'Transaction Type', 'y': 'Total Amount ($)'},
            color=type_amounts.index,  # Color bars by transaction type
            text=type_amounts.round(2)  # Show values on bars
        )
        fig_bar.update_traces(
            texttemplate='$%{text:,.2f}',
            textposition='auto',
        )
        fig_bar.update_layout(
            showlegend=False,
            hovermode='x unified'
        )
        st.plotly_chart(fig_bar)
    
    # Monthly Stats Table
    st.subheader("Monthly Statistics")
    monthly_stats = df.copy()
    monthly_stats['month'] = pd.to_datetime(monthly_stats['date']).dt.strftime('%Y-%m')
    
    # Create monthly statistics with enhanced metrics
    monthly_grouped = monthly_stats.groupby('month')
    stats_table = pd.DataFrame({
        'month': sorted(monthly_stats['month'].unique()),
        'Transaction Count': monthly_grouped.size(),
        'Total Amount': monthly_grouped['amount'].sum().round(2),
        'Average Amount': monthly_grouped['amount'].mean().round(2),
        'Highest Transaction': monthly_grouped['amount'].max().round(2),
        'Lowest Transaction': monthly_grouped['amount'].min().round(2)
    })
    
    # Calculate month-over-month changes
    stats_table['MoM Change'] = stats_table['Total Amount'].pct_change().round(3) * 100
    stats_table['MoM Change'] = stats_table['MoM Change'].map('{:+.1f}%'.format)
    
    # Add transaction count change
    stats_table['Count Change'] = stats_table['Transaction Count'].pct_change().round(3) * 100
    stats_table['Count Change'] = stats_table['Count Change'].map('{:+.1f}%'.format)
    
    # Display the enhanced statistics
    st.dataframe(stats_table.style.format({
        'Total Amount': '${:,.2f}'.format,
        'Average Amount': '${:,.2f}'.format,
        'Highest Transaction': '${:,.2f}'.format,
        'Lowest Transaction': '${:,.2f}'.format
    }), use_container_width=True)
    
    # Monthly transaction type breakdown
    st.subheader("Monthly Transaction Type Breakdown")
    type_counts = df.pivot_table(
        index=pd.to_datetime(df['date']).dt.strftime('%Y-%m'),
        columns='type',
        values='amount',
        aggfunc='count',
        fill_value=0
    ).reset_index()
    
    type_amounts = df.pivot_table(
        index=pd.to_datetime(df['date']).dt.strftime('%Y-%m'),
        columns='type',
        values='amount',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    
    # Create a combined view
    type_analysis = pd.DataFrame({
        'Month': type_counts.iloc[:, 0],
        'Income Count': type_counts['income'] if 'income' in type_counts else 0,
        'Income Amount': type_amounts['income'].map('${:,.2f}'.format) if 'income' in type_amounts else '$0.00',
        'Expense Count': type_counts['expense'] if 'expense' in type_counts else 0,
        'Expense Amount': type_amounts['expense'].map('${:,.2f}'.format) if 'expense' in type_amounts else '$0.00',
        'Subscription Count': type_counts['subscription'] if 'subscription' in type_counts else 0,
        'Subscription Amount': type_amounts['subscription'].map('${:,.2f}'.format) if 'subscription' in type_amounts else '$0.00'
    })
    
    st.dataframe(type_analysis, use_container_width=True)
    
    # Spending Trends by Transaction Type
    st.subheader("Spending Trends by Type")
    type_trends = df.copy()
    type_trends['month'] = pd.to_datetime(type_trends['date']).dt.strftime('%Y-%m')
    type_by_month = type_trends.pivot_table(
        index='month',
        columns='type',
        values='amount',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    
    # Create stacked area chart for spending trends
    fig_trends = go.Figure()
    for col in type_by_month.columns[1:]:  # Skip 'month' column
        fig_trends.add_trace(go.Scatter(
            x=type_by_month['month'],
            y=type_by_month[col],
            name=col.capitalize(),
            stackgroup='one',
            mode='lines',
            line=dict(width=0.5),
            hovertemplate="%{y:$.2f}<extra></extra>"
        ))
    
    fig_trends.update_layout(
        title='Monthly Spending by Transaction Type',
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    st.plotly_chart(fig_trends, use_container_width=True)
    
    # Detailed Type Distribution Analysis
    st.subheader("Transaction Type Analysis")
    type_analysis = pd.DataFrame({
        'Type': df['type'].unique(),
        'Count': df['type'].value_counts(),
        'Total Amount': df.groupby('type')['amount'].sum().round(2),
        'Average Amount': df.groupby('type')['amount'].mean().round(2),
        'Percentage': (df['type'].value_counts() / len(df) * 100).round(1)
    })
    
    # Format the analysis table
    type_analysis['Percentage'] = type_analysis['Percentage'].map('{:.1f}%'.format)
    type_analysis = type_analysis.sort_values('Total Amount', ascending=False)
    
    st.dataframe(type_analysis.style.format({
        'Total Amount': '${:,.2f}'.format,
        'Average Amount': '${:,.2f}'.format
    }), use_container_width=True)

else:
    st.info("No transaction data available for analysis")
