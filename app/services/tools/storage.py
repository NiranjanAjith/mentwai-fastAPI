import json
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, List

from app.core.logging import Logger
logger = Logger(name="StorageTool")

from app.framework.tools import Tool, ToolNotReadyError
from app.core.config import settings


# --------------------------------------------------------------------------------
#        Storage Provider Base Class Start
# --------------------------------------------------------------------------------


class StorageProvider(Tool):
    name: str = "StorageProvider"
    description: str = "Base class for all storage providers"
    version: str = "1.0"
    tags: list[str] = Tool.tags + ["storage", "persistence"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client = None
        super().__init__()

    def confirm_setup(self) -> bool:
        """Confirm that the storage provider is configured properly."""
        return True
    
    def run(self, *args, **kwargs) -> None:
        return True

    def save(self, key: str, data: Any) -> bool:
        """Save data to storage."""
        raise NotImplementedError(f"save() not implemented in base StorageProvider")

    def load(self, key: str) -> Any:
        """Load data from storage."""
        raise NotImplementedError(f"load() not implemented in base StorageProvider")

    def delete(self, key: str) -> bool:
        """Delete data from storage."""
        raise NotImplementedError(f"delete() not implemented in base StorageProvider")

    def teardown(self) -> None:
        logger.debug(f"[{self.name}] Tearing down storage client (noop).")
        self.client = None


# --------------------------------------------------------------------------------
#        Storage Provider Base Class End
# --------------------------------------------------------------------------------


# --------------------------------------------------------------------------------
#        AWS S3 Storage Provider Class Start
# --------------------------------------------------------------------------------


class S3StorageProvider(StorageProvider):
    name: str = "S3StorageProvider"
    description: str = "Storage provider for AWS S3"
    version: str = "1.0"
    tags: list[str] = StorageProvider.tags + ["aws", "s3"]

    def __init__(self):
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.region_name = settings.AWS_REGION
        self.client = None
        super().__init__()


    def confirm_setup(self) -> bool:
        if not hasattr(settings, 'AWS_S3_BUCKET_NAME') or not settings.AWS_S3_BUCKET_NAME:
            raise ToolNotReadyError("AWS_S3_BUCKET_NAME not set in settings")

        if not hasattr(settings, 'AWS_REGION') or not settings.AWS_REGION:
            raise ToolNotReadyError("AWS_REGION not set in settings")

        try:
            self.client = boto3.client(
                's3',
                region_name=self.region_name,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            return True
        except Exception as e:
            logger.error(f"[S3StorageProvider] Initialization failed: {e}")
            return False


    def save(self, key: str, data: Any) -> bool:
        """Save data to S3 bucket."""
        if not self.client:
            raise ToolNotReadyError("S3 client not initialized")

        try:
            # Convert data to JSON string
            json_data = json.dumps(data)
            
            # Upload to S3
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_data,
                ContentType='application/json'
            )
            logger.info(f"[S3StorageProvider] Successfully saved data with key: {key}")
            return True
        except ClientError as e:
            logger.error(f"[S3StorageProvider] Error saving data: {e}")
            return False


    def load(self, key: str) -> Any:
        """Load data from S3 bucket."""
        if not self.client:
            raise ToolNotReadyError("S3 client not initialized")

        try:
            # Get object from S3
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            # Read and parse JSON data
            json_data = response['Body'].read().decode('utf-8')
            data = json.loads(json_data)
            
            logger.info(f"[S3StorageProvider] Successfully loaded data with key: {key}")
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"[S3StorageProvider] No data found with key: {key}")
                return None
            else:
                logger.error(f"[S3StorageProvider] Error loading data: {e}")
                raise


    def delete(self, key: str) -> bool:
        """Delete data from S3 bucket."""
        if not self.client:
            raise ToolNotReadyError("S3 client not initialized")

        try:
            # Delete object from S3
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"[S3StorageProvider] Successfully deleted data with key: {key}")
            return True
        except ClientError as e:
            logger.error(f"[S3StorageProvider] Error deleting data: {e}")
            return False


# --------------------------------------------------------------------------------
#        AWS S3 Storage Provider Class End
# --------------------------------------------------------------------------------


# Global instance
storage_client = S3StorageProvider()