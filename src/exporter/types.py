"""Shared type definitions for exporter implementations."""

from __future__ import annotations

from typing import Any, Literal, TypeAlias

ExportFormat: TypeAlias = Literal["markdown", "json"]
Metadata: TypeAlias = dict[str, Any]
SourceFiles: TypeAlias = list[str]
