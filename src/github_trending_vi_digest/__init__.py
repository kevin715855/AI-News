"""Tools for producing Vietnamese digests of GitHub Trending repositories."""

from .config import AppConfig
from .core import ExtractedDocument, RepositoryFile, RepositorySnapshot
from .extractor import DocumentExtractor, DocumentExtractorConfig, extract_documents
from .models import DigestItem, RepositoryCandidate

__version__ = "0.1.0"

__all__ = [
    "AppConfig",
    "DigestItem",
    "DocumentExtractor",
    "DocumentExtractorConfig",
    "ExtractedDocument",
    "RepositoryFile",
    "RepositoryCandidate",
    "RepositorySnapshot",
    "extract_documents",
    "__version__",
]
