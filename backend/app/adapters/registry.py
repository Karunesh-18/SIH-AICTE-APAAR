"""The national APAAR registry, behind a seam. MockRegistry reads the synthetic registry_entry table."""
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.rules import RegistryInfo
from app.models.student import RegistryEntry


class RegistryAdapter(Protocol):
    def lookup(self, apaar_id: str) -> RegistryInfo | None: ...


class MockRegistry:
    def __init__(self, db: Session):
        self.db = db

    def lookup(self, apaar_id: str) -> RegistryInfo | None:
        e = self.db.scalars(select(RegistryEntry).where(RegistryEntry.apaar_id == apaar_id)).first()
        return RegistryInfo(name=e.name, dob=e.dob) if e else None
