"""Producer Kafka avec analytics et gestion d'erreurs"""
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError
from time import sleep
from json import dumps
import logging
from typing import Optional, Dict, Any
import structlog
from datetime import datetime

from src.config import get_config
from src.analytics import StockAnalytics

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


class EnhancedKafkaProducer:
    """Producer Kafka avec analytics"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialise le producer"""
        self.config = get_config(config_path)
        self.analytics = StockAnalytics() if self.config.analytics.enabled else None
        self.producer = None
        self.message_count = 0
        self.error_count = 0
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Initialise la connexion Kafka"""
        import time
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=[self.config.kafka.bootstrap_servers],
                    value_serializer=lambda x: dumps(x).encode('utf-8'),
                    acks=self.config.producer.acks,
                    retries=self.config.producer.retries,
                    batch_size=self.config.producer.batch_size,
                    linger_ms=self.config.producer.linger_ms,
                    max_in_flight_requests_per_connection=1,
                    request_timeout_ms=15000,
                    api_version=(0, 10, 1),
                )
                logger.info("producer_initialized", 
                           bootstrap_servers=self.config.kafka.bootstrap_servers,
                           attempt=attempt + 1)
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning("producer_connection_retry",
                                  attempt=attempt + 1,
                                  max_retries=max_retries,
                                  error=str(e))
                    time.sleep(retry_delay)
                else:
                    logger.error("producer_initialization_failed", 
                               error=str(e),
                               attempts=max_retries)
                    raise
    
    def _enrich_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrichit les données avec analytics"""
        if self.analytics:
            enriched = self.analytics.enrich_data(data)
            alerts = self.analytics.check_alerts(
                enriched,
                price_threshold=self.config.analytics.alert_thresholds.get("price_change_percent", 5.0),
                volume_threshold=self.config.analytics.alert_thresholds.get("volume_spike_percent", 200.0)
            )
            
            if alerts:
                enriched["alerts"] = alerts
                logger.warning("alerts_triggered", 
                             symbol=data.get("Index", "N/A"),
                             alerts=[a["type"] for a in alerts])
            
            return enriched
        return data
    
    def send_message(self, data: Dict[str, Any]) -> bool:
        """Envoie un message à Kafka"""
        try:
            enriched_data = self._enrich_data(data)
            enriched_data["_metadata"] = {
                "timestamp": datetime.now().isoformat(),
                "message_id": self.message_count,
                "producer_version": "2.0"
            }
            
            future = self.producer.send(
                self.config.kafka.topic_name,
                value=enriched_data
            )
            record_metadata = future.get(timeout=10)
            
            self.message_count += 1
            logger.info("message_sent",
                       topic=record_metadata.topic,
                       partition=record_metadata.partition,
                       offset=record_metadata.offset,
                       symbol=enriched_data.get("Index", "N/A"),
                       message_id=self.message_count)
            
            return True
            
        except KafkaError as e:
            self.error_count += 1
            logger.error("kafka_error",
                        error=str(e),
                        error_count=self.error_count)
            return False
        except Exception as e:
            self.error_count += 1
            logger.error("unexpected_error",
                        error=str(e),
                        error_type=type(e).__name__)
            return False
    
    def run(self, df: pd.DataFrame):
        """Boucle principale d'envoi de messages"""
        logger.info("producer_started",
                   topic=self.config.kafka.topic_name,
                   send_interval=self.config.producer.send_interval,
                   max_messages=self.config.producer.max_messages)
        
        try:
            while True:
                dict_stock = df.sample(1).to_dict(orient="records")[0]
                success = self.send_message(dict_stock)
                
                if not success:
                    logger.warning("message_send_failed",
                                 message_count=self.message_count)
                
                if (self.config.producer.max_messages and 
                    self.message_count >= self.config.producer.max_messages):
                    logger.info("max_messages_reached",
                              total_messages=self.message_count)
                    break
                
                sleep(self.config.producer.send_interval)
                
        except KeyboardInterrupt:
            logger.info("producer_stopped_by_user",
                       total_messages=self.message_count,
                       total_errors=self.error_count)
        except Exception as e:
            logger.error("producer_crashed",
                        error=str(e),
                        messages_sent=self.message_count)
        finally:
            self.close()
    
    def close(self):
        """Ferme proprement le producer"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("producer_closed",
                       total_messages=self.message_count,
                       total_errors=self.error_count)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du producer"""
        return {
            "messages_sent": self.message_count,
            "errors": self.error_count,
            "success_rate": (self.message_count - self.error_count) / max(self.message_count, 1) * 100
        }


def main():
    """Fonction principale"""
    import sys
    
    config = get_config()
    try:
        df = pd.read_csv(config.data.csv_path)
        logger.info("data_loaded", rows=len(df), columns=list(df.columns))
    except FileNotFoundError:
        logger.error("csv_file_not_found", 
                    path=config.data.csv_path)
        sys.exit(1)
    
    producer = EnhancedKafkaProducer()
    producer.run(df)


if __name__ == "__main__":
    main()

