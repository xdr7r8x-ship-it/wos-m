"""
WOS-M Gift Codes Models
© MANSOUR — WOS-M. All rights reserved.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class GiftCodeStatus(Enum):
    """Gift code status enum."""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    REDEEMING = "redeeming"
    REDEEMED = "redeemed"
    ALREADY_REDEEMED = "already_redeemed"
    FAILED = "failed"


@dataclass
class GiftCode:
    """Gift code model."""
    id: Optional[int]
    code: str
    alliance_id: Optional[int]
    status: GiftCodeStatus
    added_by: Optional[str]
    added_at: datetime
    redeemed_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row) -> "GiftCode":
        """Create from database row."""
        return cls(
            id=row["id"],
            code=row["code"],
            alliance_id=row["alliance_id"] if "alliance_id" in row.keys() else None,
            status=GiftCodeStatus(row["status"]),
            added_by=row["added_by"] if "added_by" in row.keys() else None,
            added_at=datetime.fromisoformat(row["added_at"]) if "added_at" in row.keys() and row["added_at"] else datetime.now(),
            redeemed_at=datetime.fromisoformat(row["redeemed_at"]) if "redeemed_at" in row.keys() and row["redeemed_at"] else None
        )


@dataclass
class GiftRedemption:
    """Gift redemption model."""
    id: Optional[int]
    code_id: int
    player_id: int
    status: str
    redeemed_at: Optional[datetime]
    error_message: Optional[str]
    
    @classmethod
    def from_row(cls, row) -> "GiftRedemption":
        """Create from database row."""
        return cls(
            id=row["id"],
            code_id=row["code_id"],
            player_id=row["player_id"],
            status=row["status"],
            redeemed_at=datetime.fromisoformat(row["redeemed_at"]) if "redeemed_at" in row.keys() and row["redeemed_at"] else None,
            error_message=row["error_message"] if "error_message" in row.keys() else None
        )


@dataclass
class GiftRedemptionBatch:
    """Gift redemption batch model."""
    id: Optional[int]
    code: str
    alliance_id: Optional[int]
    total_count: int
    success_count: int
    failure_count: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row) -> "GiftRedemptionBatch":
        """Create from database row."""
        return cls(
            id=row["id"],
            code=row["code"],
            alliance_id=row["alliance_id"] if "alliance_id" in row.keys() else None,
            total_count=row["total_count"] or 0,
            success_count=row["success_count"] or 0,
            failure_count=row["failure_count"] or 0,
            status=row["status"],
            started_at=datetime.fromisoformat(row["started_at"]) if "started_at" in row.keys() and row["started_at"] else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"]) if "completed_at" in row.keys() and row["completed_at"] else None
        )


@dataclass
class GiftRedemptionResult:
    """Gift redemption result model."""
    id: Optional[int]
    batch_id: int
    player_id: int
    player_name: str
    status: str
    error_message: Optional[str]
    redeemed_at: Optional[datetime]
    
    @classmethod
    def from_row(cls, row) -> "GiftRedemptionResult":
        """Create from database row."""
        return cls(
            id=row["id"],
            batch_id=row["batch_id"],
            player_id=row["player_id"],
            player_name=row["player_name"] if "player_name" in row.keys() else "",
            status=row["status"],
            error_message=row["error_message"] if "error_message" in row.keys() else None,
            redeemed_at=datetime.fromisoformat(row["redeemed_at"]) if "redeemed_at" in row.keys() and row["redeemed_at"] else None
        )


@dataclass
class GiftCodeStats:
    """Gift code statistics."""
    total_codes: int = 0
    pending_codes: int = 0
    valid_codes: int = 0
    redeemed_codes: int = 0
    failed_codes: int = 0
    total_redemptions: int = 0
    successful_redemptions: int = 0
    failed_redemptions: int = 0
