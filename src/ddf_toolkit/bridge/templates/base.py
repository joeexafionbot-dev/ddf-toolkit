"""Base template contract for domain-specific HA → DDF mapping."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ddf_toolkit.bridge.models import HAEntity, HAService
from ddf_toolkit.parser.ast import Item, WriteCommand


class DomainTemplate(ABC):
    """Abstract base for domain-specific HA → DDF templates."""

    domain: str

    @abstractmethod
    def can_handle(self, entity: HAEntity) -> bool:
        """Check if this template can handle the given entity."""
        ...

    @abstractmethod
    def build_items(self, entities: list[HAEntity]) -> list[Item]:
        """Build DDF *ITEM entries from HA entities."""
        ...

    @abstractmethod
    def build_writes(
        self, entities: list[HAEntity], services: list[HAService]
    ) -> list[WriteCommand]:
        """Build DDF *WRITE entries with inline formulas and ARGS."""
        ...
