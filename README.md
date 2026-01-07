# Real-Time Stock Market Data Engineering Pipeline

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache-Kafka-231F20?style=for-the-badge&logo=apache-kafka&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

---

## Overview

Ce projet est une **solution complète d'ingénierie de données en temps réel** qui simule et traite des données boursières en utilisant Apache Kafka comme système de messagerie distribué. Il intègre des fonctionnalités avancées d'analytics, de visualisation interactive, et une API REST complète pour l'analyse et l'interrogation des données.

Le pipeline permet de :
- Ingérer des données boursières en temps réel via Kafka
- Calculer automatiquement des indicateurs techniques (SMA, EMA, RSI, Volatilité)
- Détecter des anomalies et alertes en temps réel
- Stocker les données de manière optimisée (format Parquet avec 90% de compression)
- Visualiser les données via un dashboard interactif Streamlit
- Exposer les données via une API REST documentée avec FastAPI
- Intégrer avec AWS (S3, Glue, Athena) pour l'analyse à grande échelle

### Architecture

```
┌──────────────┐
│   Dataset    │  Stock Market Historical Data (CSV)
│     CSV      │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Enhanced Producer│  • Technical Indicators Calculation
│    + Analytics   │  • Alert Detection (Price/Volume)
└────────┬─────────┘  • Structured JSON Logging
         │
         │ JSON Messages
         ▼
┌──────────────────┐
│  Apache Kafka    │  • Distributed Message Queue
│    + Zookeeper   │  • Topic: stock_market_data
└────────┬─────────┘  • High Throughput & Reliability
         │
         │ Real-time Streaming
         ▼
┌──────────────────┐
│ Enhanced Consumer│  • Batch Processing (100 msg/batch)
│   + Parquet      │  • Parquet Format (90% compression)
└────────┬─────────┘  • S3 Partitioning (date/symbol)
         │
         ▼
┌──────────────────────────────────────────────┐
│         Storage Layer (S3 / Local)           │
│  output/stock_market_batch_*.parquet         │
└────────┬─────────────────────────────────────┘
         │
    ┌────┴─────┬──────────┬───────────┐
    │          │          │           │
    ▼          ▼          ▼           ▼
┌────────┐ ┌──────┐ ┌─────────┐ ┌─────────┐
│Streamlit│ │FastAPI│ │AWS Glue │ │ Athena  │
│Dashboard│ │  API  │ │ Crawler │ │   SQL   │
└─────────┘ └───────┘ └─────────┘ └─────────┘
```

---

## Features

### 🚀 Pipeline de Données
- **Streaming Kafka** : Ingestion et traitement de données en temps réel
- **Analytics Automatiques** : Calcul d'indicateurs techniques (SMA, EMA, RSI, Volatilité)
- **Alertes Intelligentes** : Détection automatique de variations de prix et pics de volume
- **Batch Processing** : Traitement optimisé par lots pour meilleures performances
- **Format Parquet** : Compression et stockage optimisés (90% d'économie d'espace)

### 📊 Visualisation & API
- **Dashboard Interactif** : Interface Streamlit avec graphiques en temps réel
- **API REST** : FastAPI avec documentation Swagger automatique
- **Graphiques Avancés** : Chandeliers japonais, indicateurs techniques, volumes

### 🏗️ Infrastructure
- **Docker Compose** : Déploiement Kafka en une commande
- **Configuration Centralisée** : Fichier YAML et variables d'environnement
- **AWS Integration** : Support S3, Glue, et Athena
- **Production-Ready** : Gestion d'erreurs, retry logic, logging structuré

### 📈 Indicateurs Techniques Calculés

| Indicateur | Description | Période |
|-----------|-------------|---------|
| **SMA** | Simple Moving Average | 20 et 50 jours |
| **EMA** | Exponential Moving Average | 12 jours |
| **RSI** | Relative Strength Index | 14 jours |
| **Volatilité** | Écart-type des rendements | 20 jours |
| **Changement de Prix** | Variation en pourcentage | Jour à jour |
| **Volume Moyen** | Moyenne mobile du volume | 20 jours |

### 🔌 API Endpoints

- `GET /` - Informations API et liste des endpoints
- `GET /health` - Health check et statut du système
- `GET /stats` - Statistiques globales (messages, symboles, prix moyens)
- `GET /data` - Données avec filtres (pagination, symbole, dates)
- `GET /symbols` - Liste de tous les symboles disponibles
- `GET /symbol/{symbol}` - Données pour un symbole spécifique
- `GET /indicators/{symbol}` - Indicateurs techniques d'un symbole

---

## Requirements

### Prérequis Système
- **Python** 3.8 ou supérieur
- **Docker** et Docker Compose
- **8GB RAM** minimum recommandé
- **AWS CLI** configuré (optionnel, pour S3)

### Dépendances Python

Les dépendances sont listées dans `requirements.txt` et incluent :
- `kafka-python` - Client Kafka
- `pandas` - Traitement de données
- `pyarrow` - Format Parquet
- `fastapi` - API REST
- `streamlit` - Dashboard interactif
- `structlog` - Logging structuré
- `s3fs` - Intégration AWS S3 (optionnel)

---

## Getting Started

### 1. Cloner le repository

```bash
git clone https://github.com/moaddebian/Real-Time-Stock-Market-Data-Engineering-Pipeline.git
cd Real-Time-Stock-Market-Data-Engineering-Pipeline
```

### 2. Installer les dépendances

```bash
# Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Installer les packages
pip install -r requirements.txt
```

### 3. Démarrer Kafka avec Docker

```bash
docker-compose up -d
```

### 4. Vérifier l'installation

```bash
# Vérifier les containers
docker ps

# Accéder à Kafka UI
# Ouvrir http://localhost:8080 dans votre navigateur
```

### 5. Démarrer le Pipeline

**Terminal 1 - Producer** :
```bash
python -m src.producer_enhanced
```


**Terminal 2 - Consumer** :
```bash
python -m src.consumer_enhanced
```


**Terminal 3 - Dashboard** :
```bash
streamlit run dashboard.py
```

**Terminal 4 - API REST** (optionnel) :
```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```


### Configuration

Tous les paramètres sont configurables via `config/config.yaml` :

```yaml
kafka:
  bootstrap_servers: "localhost:9092"
  topic_name: "stock_market_data"

producer:
  send_interval: 1  # secondes entre messages
  max_messages: null  # null = infini

consumer:
  output_format: "parquet"  # json ou parquet
  batch_size: 100
  use_s3: false  # true pour AWS S3
  local_output_dir: "output"

analytics:
  enabled: true
  calculate_indicators: true
  alert_thresholds:
    price_change_percent: 5.0
    volume_spike_percent: 200.0
```

---

## Contact Me

<div align="center">

**MOAD DABYANE**

Data Engineer & Software Developer

[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/moaddebian)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/dabyane-moad/)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:mouaddebien@gmail.com)

Made with ❤️ and ☕ by MOAD DABYANE

</div>

---

## License

Ce projet est sous licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
