"""API REST FastAPI pour les données du pipeline Kafka"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import pandas as pd
import json
from pathlib import Path
import os

from src.config import get_config

config = get_config()

app = FastAPI(
    title=config.api.title,
    version=config.api.version,
    description="API REST pour les données boursières en temps réel via Kafka"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StockData(BaseModel):
    """Modèle pour une donnée boursière"""
    Index: Optional[str] = None
    Date: Optional[str] = None
    Open: Optional[float] = None
    High: Optional[float] = None
    Low: Optional[float] = None
    Close: Optional[float] = None
    Volume: Optional[float] = None
    indicators: Optional[Dict[str, Any]] = None
    alerts: Optional[List[Dict[str, Any]]] = None


class StatsResponse(BaseModel):
    """Modèle pour les statistiques"""
    total_messages: int
    unique_symbols: int
    date_range: Dict[str, Optional[str]]
    average_price: Optional[float]
    total_volume: Optional[float]


_data_cache: Optional[pd.DataFrame] = None
_cache_timestamp: Optional[datetime] = None
CACHE_TTL = 30


def load_data_from_directory(directory: str = "output") -> pd.DataFrame:
    """Charge les données depuis un répertoire"""
    global _data_cache, _cache_timestamp
    
    if (_data_cache is not None and 
        _cache_timestamp and 
        (datetime.now() - _cache_timestamp).seconds < CACHE_TTL):
        return _data_cache
    
    data = []
    if not os.path.exists(directory):
        return pd.DataFrame()
    
    for file in Path(directory).glob("*.json"):
        try:
            with open(file, 'r') as f:
                content = json.load(f)
                if isinstance(content, list):
                    data.extend(content)
                else:
                    data.append(content)
        except Exception as e:
            print(f"Erreur lors du chargement de {file}: {e}")
    
    if not data:
        _data_cache = pd.DataFrame()
        _cache_timestamp = datetime.now()
        return _data_cache
    
    df = pd.DataFrame(data)
    _data_cache = df
    _cache_timestamp = datetime.now()
    return df


@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "message": "Stock Market Kafka API",
        "version": config.api.version,
        "endpoints": {
            "/health": "Health check",
            "/stats": "Statistiques générales",
            "/data": "Données boursières",
            "/symbols": "Liste des symboles",
            "/symbol/{symbol}": "Données pour un symbole",
            "/docs": "Documentation Swagger"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        df = load_data_from_directory()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "data_available": len(df) > 0,
            "data_count": len(df)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Retourne les statistiques générales"""
    df = load_data_from_directory()
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Aucune donnée disponible")
    
    stats = {
        "total_messages": len(df),
        "unique_symbols": df.get('Index', pd.Series()).nunique() if 'Index' in df.columns else 0,
        "date_range": {
            "min": None,
            "max": None
        },
        "average_price": None,
        "total_volume": None
    }
    
    if 'Date' in df.columns:
        dates = pd.to_datetime(df['Date'], errors='coerce')
        stats["date_range"]["min"] = dates.min().isoformat() if not dates.empty else None
        stats["date_range"]["max"] = dates.max().isoformat() if not dates.empty else None
    
    if 'Close' in df.columns:
        stats["average_price"] = float(df['Close'].mean())
    
    if 'Volume' in df.columns:
        stats["total_volume"] = float(df['Volume'].sum())
    
    return stats


@app.get("/data", response_model=List[StockData])
async def get_data(
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour la pagination"),
    symbol: Optional[str] = Query(None, description="Filtrer par symbole"),
    start_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)")
):
    """Retourne les données boursières avec filtres optionnels"""
    df = load_data_from_directory()
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Aucune donnée disponible")
    
    if symbol and 'Index' in df.columns:
        df = df[df['Index'] == symbol]
    
    if 'Date' in df.columns:
        if start_date:
            df = df[pd.to_datetime(df['Date'], errors='coerce') >= start_date]
        if end_date:
            df = df[pd.to_datetime(df['Date'], errors='coerce') <= end_date]
        df = df.sort_values('Date', ascending=False)
    
    df = df.iloc[offset:offset+limit]
    records = df.to_dict(orient='records')
    
    return records


@app.get("/symbols")
async def get_symbols():
    """Retourne la liste de tous les symboles disponibles"""
    df = load_data_from_directory()
    
    if df.empty or 'Index' not in df.columns:
        return {"symbols": []}
    
    symbols = sorted(df['Index'].unique().tolist())
    return {
        "symbols": symbols,
        "count": len(symbols)
    }


@app.get("/symbol/{symbol}", response_model=List[StockData])
async def get_symbol_data(
    symbol: str,
    limit: int = Query(100, ge=1, le=1000)
):
    """Retourne les données pour un symbole spécifique"""
    df = load_data_from_directory()
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Aucune donnée disponible")
    
    if 'Index' not in df.columns:
        raise HTTPException(status_code=400, detail="Colonne 'Index' non trouvée")
    
    df_symbol = df[df['Index'] == symbol]
    
    if df_symbol.empty:
        raise HTTPException(status_code=404, detail=f"Symbole '{symbol}' non trouvé")
    
    if 'Date' in df_symbol.columns:
        df_symbol = df_symbol.sort_values('Date', ascending=False)
    
    df_symbol = df_symbol.head(limit)
    
    records = df_symbol.to_dict(orient='records')
    return records


@app.get("/indicators/{symbol}")
async def get_indicators(symbol: str):
    """Retourne les indicateurs techniques pour un symbole"""
    df = load_data_from_directory()
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Aucune donnée disponible")
    
    if 'Index' not in df.columns:
        raise HTTPException(status_code=400, detail="Colonne 'Index' non trouvée")
    
    df_symbol = df[df['Index'] == symbol]
    
    if df_symbol.empty:
        raise HTTPException(status_code=404, detail=f"Symbole '{symbol}' non trouvé")
    
    indicator_cols = [col for col in df_symbol.columns 
                     if 'indicators' in col.lower() or 'sma' in col.lower() or 'rsi' in col.lower()]
    
    if not indicator_cols:
        return {"message": "Aucun indicateur trouvé", "indicators": {}}
    
    latest = df_symbol.iloc[-1] if len(df_symbol) > 0 else None
    
    indicators = {}
    for col in indicator_cols:
        if latest is not None and col in latest:
            indicators[col] = float(latest[col]) if pd.notna(latest[col]) else None
    
    return {
        "symbol": symbol,
        "indicators": indicators,
        "timestamp": latest.get('Date', None) if latest is not None else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=config.api.port,
        reload=True
    )

