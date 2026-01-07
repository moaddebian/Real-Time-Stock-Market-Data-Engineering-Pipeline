"""
Dashboard Streamlit pour visualisation en temps réel des données boursières
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json
from datetime import datetime, timedelta
import os
from typing import List, Dict, Any

# Configuration de la page
st.set_page_config(
    page_title="Stock Market Real-Time Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=5)
def load_data_from_directory(directory: str) -> pd.DataFrame:
    """
    Charge les données depuis un répertoire (JSON ou Parquet)
    
    Args:
        directory: Chemin du répertoire
        
    Returns:
        DataFrame avec toutes les données
    """
    dataframes = []
    
    if not os.path.exists(directory):
        return pd.DataFrame()
    
    # Charger les fichiers Parquet (priorité)
    parquet_files = list(Path(directory).glob("*.parquet"))
    if parquet_files:
        for file in parquet_files:
            try:
                df = pd.read_parquet(file)
                dataframes.append(df)
            except Exception as e:
                st.warning(f"Erreur lors du chargement de {file}: {e}")
    
    # Charger les fichiers JSON (fallback)
    json_files = list(Path(directory).glob("*.json"))
    if json_files:
        data = []
        for file in json_files:
            try:
                with open(file, 'r') as f:
                    content = json.load(f)
                    # Gérer les listes et les dictionnaires simples
                    if isinstance(content, list):
                        data.extend(content)
                    else:
                        data.append(content)
            except Exception as e:
                st.warning(f"Erreur lors du chargement de {file}: {e}")
        
        if data:
            dataframes.append(pd.DataFrame(data))
    
    if not dataframes:
        return pd.DataFrame()
    
    # Combiner tous les DataFrames
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Convertir les dates si présentes
    if 'Date' in combined_df.columns:
        try:
            combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')
        except:
            pass
    
    return combined_df


def create_price_chart(df: pd.DataFrame, symbol: str = None) -> go.Figure:
    """
    Crée un graphique de prix en chandelier
    
    Args:
        df: DataFrame avec les données
        symbol: Symbole à filtrer (optionnel)
        
    Returns:
        Figure Plotly
    """
    if symbol:
        df = df[df.get('Index', '') == symbol]
    
    if df.empty or 'Date' not in df.columns:
        return go.Figure()
    
    # Convertir les dates si nécessaire
    if df['Date'].dtype == 'object':
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Trier par date
    df = df.sort_values('Date')
    
    # Filtrer les valeurs NaN
    df = df.dropna(subset=['Date', 'Open', 'High', 'Low', 'Close'])
    
    if df.empty:
        return go.Figure()
    
    fig = go.Figure(data=go.Candlestick(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Prix"
    ))
    
    fig.update_layout(
        title=f"Graphique des Prix - {symbol if symbol else 'Tous les symboles'}",
        xaxis_title="Date",
        yaxis_title="Prix",
        template="plotly_white",
        height=500
    )
    
    return fig


def create_volume_chart(df: pd.DataFrame, symbol: str = None) -> go.Figure:
    """
    Crée un graphique de volume
    
    Args:
        df: DataFrame avec les données
        symbol: Symbole à filtrer (optionnel)
        
    Returns:
        Figure Plotly
    """
    if symbol:
        df = df[df.get('Index', '') == symbol]
    
    if df.empty or 'Date' not in df.columns:
        return go.Figure()
    
    df = df.sort_values('Date')
    
    fig = px.bar(
        df,
        x='Date',
        y=df.get('Volume', df.get('volume', 0)),
        title=f"Volume des Transactions - {symbol if symbol else 'Tous les symboles'}",
        labels={'Volume': 'Volume', 'Date': 'Date'}
    )
    
    fig.update_layout(
        template="plotly_white",
        height=300
    )
    
    return fig


def create_indicators_chart(df: pd.DataFrame, symbol: str = None) -> go.Figure:
    """
    Crée un graphique avec les indicateurs techniques
    
    Args:
        df: DataFrame avec les données
        symbol: Symbole à filtrer (optionnel)
        
    Returns:
        Figure Plotly
    """
    if symbol:
        df = df[df.get('Index', '') == symbol]
    
    if df.empty:
        return go.Figure()
    
    df = df.sort_values('Date')
    
    fig = go.Figure()
    
    # Prix de clôture
    if 'Close' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['Close'],
            name='Close Price',
            line=dict(color='blue')
        ))
    
    # SMA 20
    if 'indicators_sma_20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['indicators_sma_20'],
            name='SMA 20',
            line=dict(color='orange', dash='dash')
        ))
    
    # SMA 50
    if 'indicators_sma_50' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['indicators_sma_50'],
            name='SMA 50',
            line=dict(color='red', dash='dash')
        ))
    
    fig.update_layout(
        title=f"Indicateurs Techniques - {symbol if symbol else 'Tous les symboles'}",
        xaxis_title="Date",
        yaxis_title="Prix",
        template="plotly_white",
        height=400
    )
    
    return fig


def main():
    """Fonction principale du dashboard"""
    
    # Header
    st.markdown('<h1 class="main-header">📈 Stock Market Real-Time Dashboard</h1>', 
                unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Sélection du répertoire de données
        data_dir = st.text_input(
            "Répertoire des données",
            value="output",
            help="Chemin vers le répertoire contenant les fichiers Parquet ou JSON"
        )
        
        # Options d'affichage
        st.subheader("Options")
        auto_refresh = st.checkbox("Actualisation automatique", value=False)
        refresh_interval = st.slider("Intervalle (secondes)", 1, 60, 5)
        
        if auto_refresh:
            import time
            time.sleep(refresh_interval)
            st.rerun()
    
    # Charger les données avec gestion d'erreurs
    try:
        with st.spinner("Chargement des données..."):
            df = load_data_from_directory(data_dir)
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données: {e}")
        st.info("💡 Vérifiez que le consumer a sauvegardé des fichiers dans le répertoire 'output'")
        return
    
    if df.empty:
        st.warning("⚠️ Aucune donnée trouvée.")
        st.info("💡 Assurez-vous que:")
        st.info("1. Le consumer est en cours d'exécution")
        st.info("2. Des fichiers Parquet existent dans le répertoire 'output'")
        st.info("3. Le chemin du répertoire est correct")
        
        # Afficher les fichiers disponibles
        if os.path.exists(data_dir):
            files = list(Path(data_dir).glob("*"))
            if files:
                st.write("📁 Fichiers trouvés dans le répertoire:")
                for f in files[:10]:  # Afficher les 10 premiers
                    st.write(f"  - {f.name}")
        return
    
    # Métriques principales
    st.header("📊 Métriques Principales")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_messages = len(df)
        st.metric("Messages Totaux", f"{total_messages:,}")
    
    with col2:
        unique_symbols = df.get('Index', pd.Series()).nunique() if 'Index' in df.columns else 0
        st.metric("Symboles Uniques", unique_symbols)
    
    with col3:
        if 'Close' in df.columns:
            avg_price = df['Close'].mean()
            st.metric("Prix Moyen", f"${avg_price:,.2f}")
        else:
            st.metric("Prix Moyen", "N/A")
    
    with col4:
        if 'Volume' in df.columns:
            total_volume = df['Volume'].sum()
            st.metric("Volume Total", f"{total_volume:,.0f}")
        else:
            st.metric("Volume Total", "N/A")
    
    # Sélection du symbole
    st.header("📈 Analyse par Symbole")
    if 'Index' in df.columns:
        symbols = ['Tous'] + sorted(df['Index'].unique().tolist())
        selected_symbol = st.selectbox("Sélectionner un symbole", symbols)
        symbol_filter = None if selected_symbol == 'Tous' else selected_symbol
        
        # Afficher des informations sur le symbole sélectionné
        if selected_symbol != 'Tous':
            with st.expander("ℹ️ Informations sur le symbole"):
                symbol_info = {
                    'HSI': 'Hang Seng Index - Indice principal de Hong Kong 🇭🇰',
                    'N225': 'Nikkei 225 - Indice principal du Japon 🇯🇵',
                    'GDAXI': 'DAX - Indice principal de l\'Allemagne 🇩🇪',
                    'IXIC': 'NASDAQ Composite - Indice NASDAQ 🇺🇸',
                    'NYA': 'NYSE Composite - Indice de New York 🇺🇸',
                    'N100': 'Euronext 100 - Indice européen 🇪🇺',
                    'TWII': 'Taiwan Weighted Index - Indice de Taïwan 🇹🇼',
                    'GSPTSE': 'S&P/TSX Composite - Indice du Canada 🇨🇦',
                    'NSEI': 'Nifty 50 - Indice de l\'Inde 🇮🇳',
                    'SSMI': 'Swiss Market Index - Indice de la Suisse 🇨🇭',
                    '000001.SS': 'SSE Composite Index - Indice de Shanghai 🇨🇳',
                    '399001.SZ': 'Shenzhen Component - Indice de Shenzhen 🇨🇳',
                    'J203.JO': 'FTSE/JSE Top 40 - Indice d\'Afrique du Sud 🇿🇦',
                }
                info = symbol_info.get(selected_symbol, f'{selected_symbol} - Indice boursier')
                st.write(f"**{selected_symbol}** : {info}")
                
                # Statistiques du symbole
                symbol_df = df[df['Index'] == selected_symbol]
                if not symbol_df.empty:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Données disponibles", len(symbol_df))
                    with col2:
                        if 'Date' in symbol_df.columns:
                            dates = pd.to_datetime(symbol_df['Date'], errors='coerce')
                            date_range = f"{dates.min().strftime('%Y-%m-%d')} à {dates.max().strftime('%Y-%m-%d')}"
                            st.metric("Période", date_range)
                    with col3:
                        if 'Close' in symbol_df.columns:
                            avg_close = symbol_df['Close'].mean()
                            st.metric("Prix moyen", f"${avg_close:,.2f}")
    else:
        symbol_filter = None
        st.info("Colonne 'Index' non trouvée dans les données")
    
    # Graphiques
    st.header("📉 Graphiques")
    
    # Graphique de prix
    price_chart = create_price_chart(df, symbol_filter)
    if price_chart.data:
        st.plotly_chart(price_chart, use_container_width=True)
    else:
        st.info("Données insuffisantes pour le graphique de prix")
    
    # Indicateurs techniques
    indicators_chart = create_indicators_chart(df, symbol_filter)
    if indicators_chart.data:
        st.plotly_chart(indicators_chart, use_container_width=True)
    
    # Graphique de volume
    volume_chart = create_volume_chart(df, symbol_filter)
    if volume_chart.data:
        st.plotly_chart(volume_chart, use_container_width=True)
    
    # Tableau des données récentes
    st.header("📋 Données Récentes")
    if 'Date' in df.columns:
        df_sorted = df.sort_values('Date', ascending=False)
        st.dataframe(df_sorted.head(100), use_container_width=True)
    else:
        st.dataframe(df.head(100), use_container_width=True)
    
    # Statistiques des indicateurs
    st.header("🔍 Statistiques des Indicateurs")
    indicator_cols = [col for col in df.columns if 'indicators' in col.lower() or 'sma' in col.lower() or 'rsi' in col.lower() or 'volatility' in col.lower()]
    
    if indicator_cols:
        # Filtrer les colonnes qui existent vraiment
        existing_cols = [col for col in indicator_cols if col in df.columns]
        if existing_cols:
            # Sélectionner seulement les colonnes numériques
            numeric_cols = df[existing_cols].select_dtypes(include=['float64', 'int64']).columns.tolist()
            if numeric_cols:
                st.dataframe(df[numeric_cols].describe(), use_container_width=True)
            else:
                st.info("Aucune colonne numérique d'indicateurs trouvée")
        else:
            st.info("Aucun indicateur technique trouvé dans les données")
    else:
        st.info("Aucun indicateur technique trouvé dans les données")
    
    # Afficher les colonnes disponibles pour debug
    with st.expander("🔧 Debug: Colonnes disponibles"):
        st.write(f"Nombre de colonnes: {len(df.columns)}")
        st.write("Colonnes:", list(df.columns))
    
    # Footer
    st.markdown("---")
    st.markdown("**Dashboard créé avec Streamlit** | Données en temps réel via Kafka")


if __name__ == "__main__":
    main()

