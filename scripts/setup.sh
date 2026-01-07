#!/bin/bash

# Script de setup pour le projet Stock Market Kafka Pipeline

echo "🚀 Configuration du projet Stock Market Kafka Pipeline"
echo "=================================================="

# Vérifier Python
echo "📦 Vérification de Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi
echo "✅ Python $(python3 --version) trouvé"

# Vérifier Docker
echo "🐳 Vérification de Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi
echo "✅ Docker $(docker --version) trouvé"

# Créer l'environnement virtuel
echo "📦 Création de l'environnement virtuel..."
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
echo "📥 Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

# Créer les dossiers nécessaires
echo "📁 Création des dossiers..."
mkdir -p output
mkdir -p logs
mkdir -p data

# Copier le fichier de configuration exemple
if [ ! -f .env ]; then
    echo "📝 Création du fichier .env..."
    cp .env.example .env 2>/dev/null || echo "# Configuration" > .env
    echo "⚠️  N'oubliez pas de configurer le fichier .env avec vos credentials AWS"
fi

# Démarrer Kafka avec Docker
echo "🚀 Démarrage de Kafka avec Docker Compose..."
docker-compose up -d

# Attendre que Kafka soit prêt
echo "⏳ Attente que Kafka soit prêt..."
sleep 10

# Vérifier que Kafka fonctionne
echo "🔍 Vérification de Kafka..."
if docker ps | grep -q kafka; then
    echo "✅ Kafka est en cours d'exécution"
else
    echo "❌ Erreur lors du démarrage de Kafka"
    exit 1
fi

echo ""
echo "✅ Setup terminé avec succès !"
echo ""
echo "📋 Prochaines étapes :"
echo "1. Configurer le fichier .env avec vos credentials AWS (si vous utilisez S3)"
echo "2. Vérifier que le fichier indexProcessed.csv est présent"
echo "3. Démarrer le producer : python -m src.producer_enhanced"
echo "4. Démarrer le consumer : python -m src.consumer_enhanced"
echo "5. Démarrer le dashboard : streamlit run dashboard.py"
echo "6. Démarrer l'API : python -m api.main"
echo ""
echo "🌐 Accès aux services :"
echo "- Kafka UI : http://localhost:8080"
echo "- Dashboard : http://localhost:8501"
echo "- API : http://localhost:8000"
echo "- API Docs : http://localhost:8000/docs"

