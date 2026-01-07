"""Module de configuration centralisée"""
import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()


class KafkaConfig(BaseSettings):
    """Configuration Kafka"""
    bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    topic_name: str = Field(default="stock_market_data", env="KAFKA_TOPIC_NAME")
    consumer_group_id: str = Field(default="stock_market_consumers", env="KAFKA_CONSUMER_GROUP_ID")
    auto_offset_reset: str = Field(default="earliest", env="KAFKA_AUTO_OFFSET_RESET")
    enable_auto_commit: bool = Field(default=True, env="KAFKA_ENABLE_AUTO_COMMIT")
    max_poll_records: int = Field(default=100, env="KAFKA_MAX_POLL_RECORDS")


class ProducerConfig(BaseSettings):
    """Configuration Producer"""
    send_interval: float = Field(default=1.0, env="PRODUCER_SEND_INTERVAL")
    max_messages: Optional[int] = Field(default=None, env="PRODUCER_MAX_MESSAGES")
    acks: str = Field(default="all", env="PRODUCER_ACKS")
    retries: int = Field(default=3, env="PRODUCER_RETRIES")
    batch_size: int = Field(default=16384, env="PRODUCER_BATCH_SIZE")
    linger_ms: int = Field(default=10, env="PRODUCER_LINGER_MS")


class ConsumerConfig(BaseSettings):
    """Configuration Consumer"""
    output_format: str = Field(default="parquet", env="CONSUMER_OUTPUT_FORMAT")
    output_location: str = Field(default="output", env="CONSUMER_OUTPUT_LOCATION")
    use_s3: bool = Field(default=False, env="CONSUMER_USE_S3")
    s3_bucket: str = Field(default="", env="AWS_S3_BUCKET")
    local_output_dir: str = Field(default="output", env="CONSUMER_LOCAL_OUTPUT_DIR")
    partition_by: list = Field(default=["date", "index"])
    batch_size: int = Field(default=100, env="CONSUMER_BATCH_SIZE")


class AnalyticsConfig(BaseSettings):
    """Configuration Analytics"""
    enabled: bool = Field(default=True, env="ENABLE_ANALYTICS")
    calculate_indicators: bool = Field(default=True)
    indicators: list = Field(default=["sma_20", "sma_50", "ema_12", "rsi_14", "volatility"])
    alert_thresholds: Dict[str, float] = Field(default={
        "price_change_percent": 5.0,
        "volume_spike_percent": 200.0
    })


class APIConfig(BaseSettings):
    """Configuration API"""
    enabled: bool = Field(default=True, env="ENABLE_API")
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    title: str = Field(default="Stock Market Kafka API")
    version: str = Field(default="1.0.0")


class DashboardConfig(BaseSettings):
    """Configuration Dashboard"""
    enabled: bool = Field(default=True, env="ENABLE_DASHBOARD")
    host: str = Field(default="0.0.0.0", env="DASHBOARD_HOST")
    port: int = Field(default=8501, env="DASHBOARD_PORT")
    refresh_interval: int = Field(default=5)


class DataConfig(BaseSettings):
    """Configuration des données"""
    csv_path: str = Field(default="indexProcessed.csv", env="DATA_CSV_PATH")
    date_column: str = Field(default="Date")
    index_column: str = Field(default="Index")
    price_columns: list = Field(default=["Open", "High", "Low", "Close", "Adj Close"])
    volume_column: str = Field(default="Volume")


class LoggingConfig(BaseSettings):
    """Configuration Logging"""
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(default="json")
    file: str = Field(default="logs/pipeline.log")
    max_bytes: int = Field(default=10485760)  # 10MB
    backup_count: int = Field(default=5)


class Config:
    """Configuration principale"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialise la configuration"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                self._load_from_dict(yaml_config)
        else:
            default_config_paths = [
                Path("config/config.yaml"),
                Path("config.yaml"),
                Path("../config/config.yaml")
            ]
            config_found = False
            for path in default_config_paths:
                if path.exists():
                    with open(path, 'r') as f:
                        yaml_config = yaml.safe_load(f)
                        self._load_from_dict(yaml_config)
                        config_found = True
                        break
            
            if not config_found:
                self._load_defaults()
    
    def _load_from_dict(self, config_dict: Dict[str, Any]):
        """Charge la configuration depuis un dictionnaire"""
        self.kafka = KafkaConfig(**config_dict.get('kafka', {}))
        self.producer = ProducerConfig(**config_dict.get('producer', {}))
        self.consumer = ConsumerConfig(**config_dict.get('consumer', {}))
        self.analytics = AnalyticsConfig(**config_dict.get('analytics', {}))
        self.api = APIConfig(**config_dict.get('api', {}))
        self.dashboard = DashboardConfig(**config_dict.get('dashboard', {}))
        self.data = DataConfig(**config_dict.get('data', {}))
        self.logging = LoggingConfig(**config_dict.get('logging', {}))
    
    def _load_defaults(self):
        """Charge les valeurs par défaut"""
        self.kafka = KafkaConfig()
        self.producer = ProducerConfig()
        self.consumer = ConsumerConfig()
        self.analytics = AnalyticsConfig()
        self.api = APIConfig()
        self.dashboard = DashboardConfig()
        self.data = DataConfig()
        self.logging = LoggingConfig()


_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """Obtient l'instance de configuration (singleton)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance

