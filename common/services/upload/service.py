import os
from dataclasses import asdict
from typing import Dict, Type, Union, Any, Optional


from .base import BaseUploadProvider
from .parameters import UploadParameters, UploadResult
from .backblaze import BackblazeB2Provider

SERVICE_MAP: Dict[str, Type[BaseUploadProvider]] = {
    "backblaze": BackblazeB2Provider,
}


class UploadService:

    def resolve_provider(self, provider_name: str) -> BaseUploadProvider:
        """Looks up the provider class in SERVICE_MAP and builds configuration."""

        provider_cls = SERVICE_MAP.get(provider_name)

        if not provider_cls:
            raise ValueError(
                f"Unsupported storage provider '{provider_name}'. "
                f"Available providers: {list(SERVICE_MAP.keys())}"
            )

        return provider_cls()

    def execute_upload(
        self, params: Union[UploadParameters, Dict[str, Any]]
    ) -> UploadResult:

        upload_params = (
            UploadParameters(**params) if isinstance(params, dict) else params
        )
        result: UploadResult = self.resolve_provider(upload_params.provider).upload(
            upload_params
        )
        return asdict(result)
