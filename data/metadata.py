# data/metadata.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import time
import uuid

SCHEMA_VERSION = "1.0.0"


def _now() -> float:
    return time.time()


def _id() -> str:
    return str(uuid.uuid4())


def _validate_confidence(value: float):
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"Confidence must be between 0 and 1, got {value}")


@dataclass
class Evidence:
    id: str
    source: str
    content: str
    confidence: float
    timestamp: float
    provenance: Dict[str, Any]
    schema_version: str = SCHEMA_VERSION

    @staticmethod
    def create(
        source: str,
        content: str,
        confidence: float = 0.7,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> "Evidence":
        _validate_confidence(confidence)
        return Evidence(
            id=_id(),
            source=source,
            content=content,
            confidence=confidence,
            timestamp=_now(),
            provenance=provenance or {},
        )


@dataclass
class SpecialistOutput:
    id: str
    specialist: str
    content: str
    reasoning: Optional[str]
    evidence: List[Evidence]
    confidence: float
    timestamp: float
    lineage: Dict[str, Any]
    metadata: Dict[str, Any]
    schema_version: str = SCHEMA_VERSION

    @staticmethod
    def create(
        specialist: str,
        content: str,
        reasoning: Optional[str] = None,
        evidence: Optional[List[Evidence]] = None,
        confidence: float = 0.7,
        lineage: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "SpecialistOutput":
        _validate_confidence(confidence)
        return SpecialistOutput(
            id=_id(),
            specialist=specialist,
            content=content,
            reasoning=reasoning,
            evidence=evidence or [],
            confidence=confidence,
            timestamp=_now(),
            lineage=lineage or {"parents": [], "specialist": specialist},
            metadata=metadata or {},
        )


@dataclass
class FinalOutput:
    id: str
    content: str
    merged_from: List[str]
    evidence: List[Evidence]
    confidence: float
    timestamp: float
    lineage: Dict[str, Any]
    metadata: Dict[str, Any]
    schema_version: str = SCHEMA_VERSION

    @staticmethod
    def create(
        content: str,
        merged_from: List[str],
        evidence: List[Evidence],
        confidence: float = 0.8,
        lineage: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "FinalOutput":
        _validate_confidence(confidence)
        return FinalOutput(
            id=_id(),
            content=content,
            merged_from=merged_from,
            evidence=evidence,
            confidence=confidence,
            timestamp=_now(),
            lineage=lineage or {"parents": merged_from, "merge_strategy": "weighted"},
            metadata=metadata or {},
        )
