from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class UploadParameters:

    provider: str
    local_path: str
    bucket_name: str
    region_name: str
    access_key_id: str
    secret_access_key: str
    endpoint_url: Optional[str] = None
    destination_file_name: Optional[str] = None
    content_type: str = "application/octet-stream"
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UploadResult:

    success: bool
    file_key: str
    bucket_name: str
    error_message: Optional[str] = None
