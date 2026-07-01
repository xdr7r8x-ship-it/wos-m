"""
WOS-M Gift Codes Service
© MANSOUR — WOS-M. All rights reserved.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.database import db
from modules.gift_codes.models import GiftCode, GiftRedemption, GiftRedemptionBatch, GiftCodeStatus


class GiftCodeService:
    """Service for gift code operations."""
    
    async def add_code(self, code: str, alliance_id: Optional[int] = None, added_by: Optional[str] = None) -> int:
        """Add a new gift code."""
        cursor = await db.execute(
            """INSERT INTO gift_codes (code, alliance_id, status, added_by) 
               VALUES (?, ?, ?, ?)""",
            (code.upper(), alliance_id, GiftCodeStatus.PENDING.value, added_by)
        )
        await db.commit()
        return cursor.lastrowid
    
    async def get_code(self, code_id: int) -> Optional[GiftCode]:
        """Get a gift code by ID."""
        row = await db.fetchone("SELECT * FROM gift_codes WHERE id = ?", (code_id,))
        return GiftCode.from_row(row) if row else None
    
    async def get_code_by_code(self, code: str) -> Optional[GiftCode]:
        """Get a gift code by code string."""
        row = await db.fetchone("SELECT * FROM gift_codes WHERE code = ?", (code.upper(),))
        return GiftCode.from_row(row) if row else None
    
    async def get_codes_by_alliance(self, alliance_id: int) -> List[GiftCode]:
        """Get all gift codes for an alliance."""
        rows = await db.fetchall(
            "SELECT * FROM gift_codes WHERE alliance_id = ? ORDER BY added_at DESC",
            (alliance_id,)
        )
        return [GiftCode.from_row(row) for row in rows]
    
    async def get_all_codes(self, status: Optional[str] = None, limit: int = 100) -> List[GiftCode]:
        """Get all gift codes."""
        query = "SELECT * FROM gift_codes"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY added_at DESC LIMIT ?"
        params.append(limit)
        
        rows = await db.fetchall(query, tuple(params))
        return [GiftCode.from_row(row) for row in rows]
    
    async def update_code_status(self, code_id: int, status: GiftCodeStatus) -> bool:
        """Update gift code status."""
        await db.execute(
            "UPDATE gift_codes SET status = ? WHERE id = ?",
            (status.value, code_id)
        )
        await db.commit()
        return True
    
    async def mark_as_redeemed(self, code_id: int) -> bool:
        """Mark code as redeemed."""
        await db.execute(
            """UPDATE gift_codes 
               SET status = ?, redeemed_at = CURRENT_TIMESTAMP 
               WHERE id = ?""",
            (GiftCodeStatus.REDEEMED.value, code_id)
        )
        await db.commit()
        return True
    
    async def delete_code(self, code_id: int) -> bool:
        """Delete a gift code."""
        await db.execute("DELETE FROM gift_codes WHERE id = ?", (code_id,))
        await db.commit()
        return True
    
    async def check_code_exists(self, code: str, player_id: int) -> bool:
        """Check if code was already redeemed by player."""
        row = await db.fetchone(
            """SELECT * FROM gift_redemptions 
               WHERE player_id = ? 
               AND code_id IN (SELECT id FROM gift_codes WHERE code = ?)""",
            (player_id, code.upper())
        )
        return row is not None
    
    async def add_redemption(
        self,
        code_id: int,
        player_id: int,
        status: str = GiftCodeStatus.PENDING.value,
        error_message: Optional[str] = None,
        provider: Optional[str] = None,
        api_status: Optional[str] = None,
    ) -> int:
        """Add a redemption record."""
        cursor = await db.execute(
            """INSERT INTO gift_redemptions (code_id, player_id, status, error_message, provider, api_status) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (code_id, player_id, status, error_message, provider, api_status)
        )
        await db.commit()
        return cursor.lastrowid
    
    async def update_redemption_status(
        self,
        redemption_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Update redemption status."""
        query = "UPDATE gift_redemptions SET status = ?"
        params = [status]
        
        if status == GiftCodeStatus.REDEEMED.value:
            query += ", redeemed_at = CURRENT_TIMESTAMP"
        
        if error_message:
            query += ", error_message = ?"
            params.append(error_message)
        
        query += " WHERE id = ?"
        params.append(redemption_id)
        
        await db.execute(query, tuple(params))
        await db.commit()
        return True
    
    async def get_player_redemptions(self, player_id: int) -> List[GiftRedemption]:
        """Get all redemptions for a player."""
        rows = await db.fetchall(
            "SELECT * FROM gift_redemptions WHERE player_id = ? ORDER BY redeemed_at DESC",
            (player_id,)
        )
        return [GiftRedemption.from_row(row) for row in rows]
    
    async def create_batch(
        self,
        code: str,
        alliance_id: Optional[int] = None
    ) -> int:
        """Create a redemption batch."""
        cursor = await db.execute(
            """INSERT INTO gift_redemption_batches (code, alliance_id, status) 
               VALUES (?, ?, ?)""",
            (code.upper(), alliance_id, "pending")
        )
        await db.commit()
        return cursor.lastrowid
    
    async def update_batch(
        self,
        batch_id: int,
        total: int = None,
        success: int = None,
        failure: int = None,
        status: str = None
    ) -> bool:
        """Update batch progress."""
        updates = []
        params = []
        
        if total is not None:
            updates.append("total_count = ?")
            params.append(total)
        
        if success is not None:
            updates.append("success_count = ?")
            params.append(success)
        
        if failure is not None:
            updates.append("failure_count = ?")
            params.append(failure)
        
        if status:
            updates.append("status = ?")
            params.append(status)
            
            if status in ("completed", "failed"):
                updates.append("completed_at = CURRENT_TIMESTAMP")
        
        if updates:
            query = f"UPDATE gift_redemption_batches SET {', '.join(updates)} WHERE id = ?"
            params.append(batch_id)
            await db.execute(query, tuple(params))
            await db.commit()
        
        return True
    
    async def add_batch_result(
        self,
        batch_id: int,
        player_id: int,
        player_name: str,
        status: str,
        error_message: Optional[str] = None
    ) -> int:
        """Add result to batch."""
        cursor = await db.execute(
            """INSERT INTO gift_redemption_results 
               (batch_id, player_id, player_name, status, error_message) 
               VALUES (?, ?, ?, ?, ?)""",
            (batch_id, player_id, player_name, status, error_message)
        )
        await db.commit()
        return cursor.lastrowid
    
    async def get_batch(self, batch_id: int) -> Optional[GiftRedemptionBatch]:
        """Get a batch by ID."""
        row = await db.fetchone(
            "SELECT * FROM gift_redemption_batches WHERE id = ?",
            (batch_id,)
        )
        return GiftRedemptionBatch.from_row(row) if row else None
    
    async def get_batch_results(self, batch_id: int) -> List[Dict[str, Any]]:
        """Get all results for a batch."""
        rows = await db.fetchall(
            """SELECT grr.*, p.name as player_name_fk 
               FROM gift_redemption_results grr 
               LEFT JOIN players p ON grr.player_id = p.id 
               WHERE grr.batch_id = ?""",
            (batch_id,)
        )
        return [dict(row) for row in rows]
    
    async def get_stats(self) -> Dict[str, int]:
        """Get gift code statistics."""
        stats = {}
        
        for status in GiftCodeStatus:
            row = await db.fetchone(
                "SELECT COUNT(*) as count FROM gift_codes WHERE status = ?",
                (status.value,)
            )
            stats[status.value] = row["count"] if row else 0
        
        redemptions = await db.fetchone(
            "SELECT COUNT(*) as count FROM gift_redemptions WHERE status = ?",
            (GiftCodeStatus.REDEEMED.value,)
        )
        stats["total_redemptions"] = redemptions["count"] if redemptions else 0
        
        return stats


gift_code_service = GiftCodeService()
