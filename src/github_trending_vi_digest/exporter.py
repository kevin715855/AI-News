"""Digest export stage."""

from __future__ import annotations

from .models import DigestItem


def export_digest(items: list[DigestItem]) -> str:
    raise NotImplementedError("Digest exporter is not implemented yet.")
