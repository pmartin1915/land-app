"""
Enhanced Visualization components for the Streamlit dashboard.
Advanced analytics and intelligence-based visualizations.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List

def create_radar_chart(property_data: pd.Series):
    """
    Creates an intelligence score radar chart for a single property.

    Args:
        property_data: A Pandas Series representing a single property.

    Returns:
        A Plotly Figure object for the radar chart.
    """
    intelligence_scores = {
        'Market': property_data.get('county_market_score', 0),
        'Geography': property_data.get('geographic_score', 0),
        'Timing': property_data.get('market_timing_score', 0),
        'Description': property_data.get('total_description_score', 0),
        'Road Access': property_data.get('road_access_score', 0),
        'Water': property_data.get('water_score', 0) * 5 # Scale water score to be comparable
    }

    labels = list(intelligence_scores.keys())
    values = list(intelligence_scores.values())

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels,
        fill='toself',
        name='Intelligence Profile'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        title=f"Intelligence Profile for Parcel: {property_data.get('parcel_id', 'N/A')}",
        height=400
    )

    return fig

def create_county_heatmap(df: pd.DataFrame):
    """
    Creates a bar chart showing the average county market score by county.

    Args:
        df: DataFrame with property data.

    Returns:
        A Plotly Figure object for the bar chart.
    """
    if 'county' not in df.columns or 'county_market_score' not in df.columns:
        return go.Figure()

    county_avg_scores = df.groupby('county')['county_market_score'].mean().sort_values(ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=county_avg_scores.index,
        y=county_avg_scores.values,
        marker_color='indianred'
    ))

    fig.update_layout(
        title_text='Average County Market Score',
        xaxis_title="County",
        yaxis_title="Average Market Score",
        height=400
    )
    return fig

def create_correlation_heatmap(df: pd.DataFrame):
    """
    Creates a correlation heatmap for key numeric columns.

    Args:
        df: DataFrame with property data.

    Returns:
        A Plotly Figure object for the heatmap.
    """
    correlation_cols = [
        'amount', 'acreage', 'price_per_acre', 'investment_score',
        'water_score', 'county_market_score', 'geographic_score',
        'market_timing_score', 'total_description_score', 'road_access_score'
    ]
    
    # Ensure columns exist in the dataframe
    existing_cols = [col for col in correlation_cols if col in df.columns]
    
    if len(existing_cols) < 2:
        return go.Figure()

    corr_matrix = df[existing_cols].corr()

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='Viridis',
        zmin=-1,
        zmax=1
    ))

    fig.update_layout(
        title_text='Correlation Matrix of Key Metrics',
        height=500
    )
    return fig

def create_multi_county_radar_comparison(df: pd.DataFrame, counties: List[str]) -> go.Figure:
    """
    Creates a multi-county radar chart comparison showing intelligence scores.

    Args:
        df: DataFrame with property data
        counties: List of counties to compare

    Returns:
        A Plotly Figure object for the multi-county radar chart
    """
    if df.empty or not counties:
        return go.Figure()

    fig = go.Figure()

    # Define colors for each county
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']

    for i, county in enumerate(counties[:8]):  # Limit to 8 counties for readability
        county_data = df[df['county'] == county]
        if county_data.empty:
            continue

        # Calculate average scores for this county
        avg_scores = {
            'Market Score': county_data['county_market_score'].mean(),
            'Geographic Score': county_data['geographic_score'].mean(),
            'Timing Score': county_data['market_timing_score'].mean(),
            'Description Score': county_data['total_description_score'].mean(),
            'Road Access': county_data['road_access_score'].mean(),
            'Investment Score': county_data['investment_score'].mean()
        }

        fig.add_trace(go.Scatterpolar(
            r=list(avg_scores.values()),
            theta=list(avg_scores.keys()),
            fill='toself',
            name=f'{county} County',
            line_color=colors[i % len(colors)]
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        title="County Intelligence Comparison - Radar Chart",
        height=600
    )

    return fig

def create_investment_bubble_chart(df: pd.DataFrame) -> go.Figure:
    """
    Creates a bubble chart showing investment opportunities with multiple dimensions.

    Args:
        df: DataFrame with property data

    Returns:
        A Plotly Figure object for the bubble chart
    """
    if df.empty:
        return go.Figure()

    # Filter to properties with intelligence scores
    df_intel = df[df['county_market_score'] > 0].copy()

    if df_intel.empty:
        return go.Figure()

    # Calculate bubble size based on acreage (with min/max limits)
    df_intel['bubble_size'] = df_intel['acreage'].fillna(1)
    df_intel['bubble_size'] = np.clip(df_intel['bubble_size'] * 10, 5, 50)

    fig = go.Figure()

    # Create scatter plot with bubbles
    fig.add_trace(go.Scatter(
        x=df_intel['county_market_score'],
        y=df_intel['investment_score'],
        mode='markers',
        marker=dict(
            size=df_intel['bubble_size'],
            color=df_intel['geographic_score'],
            colorscale='Viridis',
            colorbar=dict(title="Geographic Score"),
            line=dict(width=1, color='black'),
            opacity=0.7
        ),
        text=df_intel.apply(lambda row:
            f"Parcel: {row['parcel_id']}<br>"
            f"County: {row['county']}<br>"
            f"Price: ${row['amount']:,.2f}<br>"
            f"Acreage: {row['acreage']:.2f}<br>"
            f"Market Timing: {row['market_timing_score']:.1f}", axis=1),
        hovertemplate='%{text}<extra></extra>',
        name='Properties'
    ))

    fig.update_layout(
        title='Investment Opportunity Bubble Chart<br><sub>X: County Market Score, Y: Investment Score, Size: Acreage, Color: Geographic Score</sub>',
        xaxis_title='County Market Score',
        yaxis_title='Investment Score',
        height=600,
        showlegend=False
    )

    return fig

def create_intelligence_distribution_analysis(df: pd.DataFrame) -> go.Figure:
    """
    Creates a distribution analysis of intelligence scores across all properties.

    Args:
        df: DataFrame with property data

    Returns:
        A Plotly Figure with distribution histograms
    """
    if df.empty:
        return go.Figure()

    # Filter to properties with intelligence scores
    df_intel = df[df['county_market_score'] > 0].copy()

    if df_intel.empty:
        return go.Figure()

    # Create subplots for different intelligence metrics
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=('County Market Score', 'Geographic Score', 'Market Timing Score',
                       'Investment Score', 'Description Score', 'Road Access Score'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
    )

    # Intelligence metrics to plot
    metrics = [
        ('county_market_score', 'County Market Score'),
        ('geographic_score', 'Geographic Score'),
        ('market_timing_score', 'Market Timing Score'),
        ('investment_score', 'Investment Score'),
        ('total_description_score', 'Description Score'),
        ('road_access_score', 'Road Access Score')
    ]

    for i, (col, title) in enumerate(metrics):
        row = (i // 3) + 1
        col_pos = (i % 3) + 1

        if col in df_intel.columns:
            fig.add_trace(
                go.Histogram(
                    x=df_intel[col],
                    name=title,
                    showlegend=False,
                    marker_color='lightblue',
                    opacity=0.7
                ),
                row=row, col=col_pos
            )

    fig.update_layout(
        title_text="Intelligence Score Distribution Analysis",
        height=600,
        showlegend=False
    )

    return fig

def create_county_performance_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Creates a comprehensive heatmap showing county performance across all metrics.

    Args:
        df: DataFrame with property data

    Returns:
        A Plotly Figure with county performance heatmap
    """
    if df.empty:
        return go.Figure()

    # Group by county and calculate metrics
    county_metrics = df.groupby('county').agg({
        'county_market_score': 'mean',
        'geographic_score': 'mean',
        'market_timing_score': 'mean',
        'investment_score': 'mean',
        'total_description_score': 'mean',
        'road_access_score': 'mean',
        'water_score': 'mean',
        'amount': ['count', 'mean'],
        'acreage': 'mean'
    }).round(1)

    # Flatten column names
    county_metrics.columns = [
        'Market Score', 'Geographic Score', 'Timing Score', 'Investment Score',
        'Description Score', 'Road Access', 'Water Score', 'Property Count',
        'Avg Price', 'Avg Acreage'
    ]

    # Filter to counties with data
    county_metrics = county_metrics[county_metrics['Market Score'] > 0]

    if county_metrics.empty:
        return go.Figure()

    # Select key intelligence metrics for heatmap
    heatmap_cols = ['Market Score', 'Geographic Score', 'Timing Score',
                   'Investment Score', 'Description Score', 'Road Access']

    fig = go.Figure(data=go.Heatmap(
        z=county_metrics[heatmap_cols].values,
        x=heatmap_cols,
        y=county_metrics.index,
        colorscale='RdYlBu_r',
        text=county_metrics[heatmap_cols].values,
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False,
        zmin=0,
        zmax=100
    ))

    fig.update_layout(
        title="County Performance Heatmap - Intelligence Metrics",
        xaxis_title="Intelligence Metrics",
        yaxis_title="Alabama Counties",
        height=400 + len(county_metrics) * 20,  # Dynamic height based on county count
        font=dict(size=11)
    )

    return fig

def create_investment_timeline_analysis(df: pd.DataFrame) -> go.Figure:
    """
    Creates timeline analysis of investment opportunities by county market conditions.

    Args:
        df: DataFrame with property data

    Returns:
        A Plotly Figure with timeline analysis
    """
    if df.empty:
        return go.Figure()

    # Filter to properties with intelligence data and timing scores
    df_timeline = df[(df['county_market_score'] > 0) & (df['market_timing_score'] > 0)].copy()

    if df_timeline.empty:
        return go.Figure()

    # Create timing categories
    df_timeline['timing_category'] = pd.cut(
        df_timeline['market_timing_score'],
        bins=[0, 33, 66, 100],
        labels=['Emerging Market', 'Growth Phase', 'Peak Opportunity']
    )

    # Count properties by county and timing category
    timeline_data = df_timeline.groupby(['county', 'timing_category']).size().reset_index(name='property_count')

    fig = go.Figure()

    # Add bars for each timing category
    categories = ['Emerging Market', 'Growth Phase', 'Peak Opportunity']
    colors = ['lightcoral', 'gold', 'lightgreen']

    for i, category in enumerate(categories):
        category_data = timeline_data[timeline_data['timing_category'] == category]

        fig.add_trace(go.Bar(
            x=category_data['county'],
            y=category_data['property_count'],
            name=category,
            marker_color=colors[i],
            opacity=0.8
        ))

    fig.update_layout(
        title="Investment Timing Analysis by County",
        xaxis_title="County",
        yaxis_title="Number of Properties",
        barmode='stack',
        height=500,
        showlegend=True
    )

    return fig
