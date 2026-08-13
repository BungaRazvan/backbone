import os
import logging
import boto3
from django.conf import settings
from botocore.exceptions import BotoCoreError, ClientError

from .base import BaseUploadProvider
from .parameters import UploadParameters, UploadResult

logger = logging.getLogger(__name__)


class BackblazeB2Provider(BaseUploadProvider):
    """Backblaze B2 S3 provider implementation."""

    def __init__(
        self,
    ):

        self._s3_client = None

    def validate_config(self, args: UploadParameters) -> bool:

        return all([args.access_key_id, args.secret_access_key, args.endpoint_url])

    def _get_client(self, args: UploadParameters):

        if self._s3_client is None:
            if not self.validate_config(args):
                raise ValueError(
                    "Backblaze B2 configuration is incomplete or missing in Django settings."
                )

            self._s3_client = boto3.client(
                "s3",
                endpoint_url=args.endpoint_url,
                aws_access_key_id=args.access_key_id,
                aws_secret_access_key=args.secret_access_key,
                region_name=args.region_name,
            )

        return self._s3_client

    def upload(self, args: UploadParameters) -> UploadResult:

        file_name = args.destination_file_name or os.path.basename(args.local_path)

        try:
            client = self._get_client(args)

            extra_args = {
                "ContentType": args.content_type,
                "ServerSideEncryption": "AES256",
            }
            if args.extra_metadata:
                extra_args["Metadata"] = args.extra_metadata

            client.upload_file(
                Filename=args.local_path,
                Bucket=args.bucket_name,
                Key=file_name,
                ExtraArgs=extra_args,
            )

            return UploadResult(
                success=True,
                file_key=file_name,
                bucket_name=args.bucket_name,
            )

        except (BotoCoreError, ClientError, ValueError) as err:

            return UploadResult(
                success=False,
                file_key=file_name,
                bucket_name=args.bucket_name,
                error_message=str(err),
            )
