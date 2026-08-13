import os
import sqlite3
import tempfile
import logging
import gnupg
import tarfile

from datetime import datetime
from celery import shared_task
from django.conf import settings

from common.services.upload import UploadService, UploadParameters

logger = logging.getLogger(__name__)


@shared_task
def sqlite_db_backup(
    db_dir: str,
    provider: str,
    bucket_name: str,
    region_name: str,
    access_key_id: str,
    secret_access_key: str,
    endpoint_url: str,
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"db_backup_{timestamp}.tar.gz.gpg"

    if not getattr(settings, "BACKUP_ENCRYPTION_PASSPHRASE", None):
        error_msg = "passphrase not set up"
        logger.error(error_msg)
        return error_msg

    try:
        gpg = gnupg.GPG()

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = os.path.join(temp_dir, "snapshots")
            raw_tar_path = os.path.join(temp_dir, "backup.tar.gz")
            encrypted_path = os.path.join(temp_dir, filename)

            #  Safe SQLite online snapshots
            for root, _, files in os.walk(db_dir):
                for file in files:
                    if not file.endswith((".db", ".sqlite", ".sqlite3")):
                        continue

                    src_db_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_db_path, db_dir)
                    dest_db_path = os.path.join(snapshot_dir, rel_path)

                    os.makedirs(os.path.dirname(dest_db_path), exist_ok=True)

                    src_conn = sqlite3.connect(src_db_path)
                    dest_conn = sqlite3.connect(dest_db_path)

                    with dest_conn:
                        src_conn.backup(dest_conn)

                    dest_conn.close()
                    src_conn.close()

            #  Package snapshots into tar.gz
            with tarfile.open(raw_tar_path, "w:gz") as tar:
                tar.add(snapshot_dir, arcname="databases")

            # Encrypt file with GPG
            with open(raw_tar_path, "rb") as tar_file:
                status = gpg.encrypt_file(
                    tar_file,
                    recipients=None,
                    symmetric="AES256",
                    passphrase=settings.BACKUP_ENCRYPTION_PASSPHRASE,
                    output=encrypted_path,
                )

            if not status.ok:
                # Fixes: Include status.stderr to identify missing GPG binary/config issues
                raise RuntimeError(
                    f"GPG Encryption failed: {status.status} | Details: {status.stderr}"
                )

            #  Upload
            result = UploadService().execute_upload(
                params=UploadParameters(
                    provider=provider,
                    bucket_name=bucket_name,
                    region_name=region_name,
                    access_key_id=access_key_id,
                    secret_access_key=secret_access_key,
                    endpoint_url=endpoint_url,
                    local_path=encrypted_path,
                )
            )

            if result.success:
                logger.info(f"Database backup succeeded.")
                return f"Success! Uploaded encrypted backup"

            if result.error_message:
                logger.error(result.error_message)

            return "Backup task failed"

    except Exception as exc:
        logger.error(f"Backup task failed: {exc}", exc_info=True)
        return "Backup task failed"
