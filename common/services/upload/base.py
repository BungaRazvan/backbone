from abc import ABC, abstractmethod
from .parameters import UploadParameters, UploadResult


class BaseUploadProvider(ABC):
    """Abstract interface for all file upload providers."""

    @abstractmethod
    def upload(self, params: UploadParameters) -> UploadResult:
        """Uploads a local file to the remote storage destination."""
        raise NotImplementedError

    @abstractmethod
    def validate_config(self) -> bool:
        """Validates that provider credentials/settings are complete."""
        raise NotImplementedError
