"""Consumer Kafka avec support Parquet et batch processing"""
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from json import loads
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from s3fs import S3FileSystem

from src.config import get_config

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


class EnhancedKafkaConsumer:
    """Consumer Kafka avec batch processing et Parquet"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialise le consumer"""
        self.config = get_config(config_path)
        self.consumer = None
        self.message_buffer: List[Dict[str, Any]] = []
        self.message_count = 0
        self.batch_count = 0
        self.error_count = 0
        self.s3 = None
        
        self._initialize_consumer()
        self._initialize_storage()
    
    def _initialize_consumer(self):
        """Initialise la connexion Kafka"""
        import time
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.consumer = KafkaConsumer(
                    self.config.kafka.topic_name,
                    bootstrap_servers=[self.config.kafka.bootstrap_servers],
                    value_deserializer=lambda x: loads(x.decode('utf-8')),
                    auto_offset_reset=self.config.kafka.auto_offset_reset,
                    enable_auto_commit=self.config.kafka.enable_auto_commit,
                    max_poll_records=self.config.kafka.max_poll_records,
                    group_id=self.config.kafka.consumer_group_id,
                    request_timeout_ms=15000,
                    api_version=(0, 10, 1),
                )
                logger.info("consumer_initialized",
                           topic=self.config.kafka.topic_name,
                           group_id=self.config.kafka.consumer_group_id,
                           attempt=attempt + 1)
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning("consumer_connection_retry",
                                  attempt=attempt + 1,
                                  max_retries=max_retries,
                                  error=str(e))
                    time.sleep(retry_delay)
                else:
                    logger.error("consumer_initialization_failed", 
                               error=str(e),
                               attempts=max_retries)
                    raise
    
    def _initialize_storage(self):
        """Initialise le stockage (S3 ou local)"""
        if self.config.consumer.use_s3:
            try:
                self.s3 = S3FileSystem()
                logger.info("s3_initialized", bucket=self.config.consumer.s3_bucket)
            except Exception as e:
                logger.error("s3_initialization_failed", error=str(e))
                raise
        else:
            os.makedirs(self.config.consumer.local_output_dir, exist_ok=True)
            logger.info("local_storage_initialized",
                       directory=self.config.consumer.local_output_dir)
    
    def _convert_to_dataframe(self, messages: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convertit les messages en DataFrame"""
        normalized = []
        for msg in messages:
            flat = self._flatten_dict(msg)
            normalized.append(flat)
        
        return pd.DataFrame(normalized)
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Aplatit un dictionnaire imbriqué"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v) if v else None))
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _save_as_parquet(self, df: pd.DataFrame, filepath: str):
        """Sauvegarde un DataFrame en Parquet"""
        try:
            date_columns = ['Date', 'date', 'timestamp']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            table = pa.Table.from_pandas(df)
            
            if self.config.consumer.use_s3 and self.s3:
                with self.s3.open(filepath, 'wb') as f:
                    pq.write_table(table, f)
            else:
                pq.write_table(table, filepath)
            
            logger.info("parquet_saved",
                       filepath=filepath,
                       rows=len(df),
                       columns=len(df.columns))
        except Exception as e:
            logger.error("parquet_save_failed",
                        filepath=filepath,
                        error=str(e))
            raise
    
    def _save_as_json(self, messages: List[Dict[str, Any]], filepath: str):
        """Sauvegarde les messages en JSON"""
        try:
            if self.config.consumer.use_s3 and self.s3:
                with self.s3.open(filepath, 'w') as f:
                    json.dump(messages, f, indent=2, default=str)
            else:
                with open(filepath, 'w') as f:
                    json.dump(messages, f, indent=2, default=str)
            
            logger.info("json_saved",
                       filepath=filepath,
                       messages=len(messages))
        except Exception as e:
            logger.error("json_save_failed",
                        filepath=filepath,
                        error=str(e))
            raise
    
    def _get_filepath(self, batch_num: int, format: str) -> str:
        """Génère le chemin du fichier avec partitionnement"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.config.consumer.use_s3:
            base_path = f"s3://{self.config.consumer.s3_bucket}/stock_data"
            if "date" in self.config.consumer.partition_by:
                date_partition = datetime.now().strftime("%Y/%m/%d")
                base_path = f"{base_path}/date={date_partition}"
            
            filename = f"stock_market_batch_{batch_num}_{timestamp}.{format}"
            return f"{base_path}/{filename}"
        else:
            base_path = self.config.consumer.local_output_dir
            filename = f"stock_market_batch_{batch_num}_{timestamp}.{format}"
            return os.path.join(base_path, filename)
    
    def _save_batch(self):
        """Sauvegarde le batch actuel"""
        if not self.message_buffer:
            return
        
        try:
            self.batch_count += 1
            format = self.config.consumer.output_format
            
            if format == "parquet":
                df = self._convert_to_dataframe(self.message_buffer)
                filepath = self._get_filepath(self.batch_count, "parquet")
                self._save_as_parquet(df, filepath)
            else:
                filepath = self._get_filepath(self.batch_count, "json")
                self._save_as_json(self.message_buffer, filepath)
            
            self.message_buffer.clear()
            
        except Exception as e:
            self.error_count += 1
            logger.error("batch_save_failed",
                        batch_num=self.batch_count,
                        error=str(e))
    
    def process_message(self, message):
        """Traite un message individuel"""
        try:
            data = message.value
            self.message_buffer.append(data)
            self.message_count += 1
            
            if len(self.message_buffer) >= self.config.consumer.batch_size:
                self._save_batch()
            
        except Exception as e:
            self.error_count += 1
            logger.error("message_processing_failed",
                        error=str(e),
                        offset=message.offset)
    
    def run(self):
        """Boucle principale de consommation"""
        logger.info("consumer_started",
                   topic=self.config.kafka.topic_name,
                   batch_size=self.config.consumer.batch_size,
                   output_format=self.config.consumer.output_format)
        
        try:
            for message in self.consumer:
                self.process_message(message)
                
        except KeyboardInterrupt:
            logger.info("consumer_stopped_by_user",
                       total_messages=self.message_count,
                       total_batches=self.batch_count)
        except KafkaError as e:
            logger.error("kafka_error",
                        error=str(e))
        except Exception as e:
            logger.error("consumer_crashed",
                        error=str(e))
        finally:
            # Sauvegarder les messages restants
            if self.message_buffer:
                self._save_batch()
            self.close()
    
    def close(self):
        """Ferme proprement le consumer"""
        if self.consumer:
            self.consumer.close()
            logger.info("consumer_closed",
                       total_messages=self.message_count,
                       total_batches=self.batch_count,
                       total_errors=self.error_count)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du consumer"""
        return {
            "messages_processed": self.message_count,
            "batches_saved": self.batch_count,
            "errors": self.error_count,
            "buffer_size": len(self.message_buffer),
            "success_rate": (self.message_count - self.error_count) / max(self.message_count, 1) * 100
        }


def main():
    """Fonction principale"""
    consumer = EnhancedKafkaConsumer()
    consumer.run()


if __name__ == "__main__":
    main()

