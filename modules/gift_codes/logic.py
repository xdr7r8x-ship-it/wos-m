"""
WOS-M Gift Codes Logic Layer
Provides high-level redemption functions for gift codes.
© MANSOUR — WOS-M. All rights reserved.
"""
from typing import Tuple, Optional, Dict, Any
from modules.gift_codes.redemption_engine import redemption_engine
from modules.gift_codes.service import gift_code_service
from modules.gift_codes.models import GiftCodeStatus
from core.database import db
from core.audit_log import audit_log, AuditCategory


async def redeem_gift_code(
    code: str,
    alliance_id: int,
    player_fid: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Redeem a gift code for an alliance.
    
    Args:
        code: The gift code to redeem
        alliance_id: The alliance database ID
        player_fid: Optional player FID for logging
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    code = code.upper().strip()
    
    # Get alliance info
    alliance = await db.fetchone(
        "SELECT * FROM alliances WHERE id = ?",
        (alliance_id,)
    )
    
    if not alliance:
        return False, "التحالف غير موجود"
    
    # Get player_id from alliance - use players table
    player = await db.fetchone(
        "SELECT id, fid FROM players WHERE alliance_id = ? AND is_active = 1 LIMIT 1",
        (alliance_id,)
    )
    
    if not player:
        return False, "لا يوجد لاعبين مرتبطين بهذا التحالف"
    
    player_id = player["id"]
    player_fid = player["fid"]
    
    # Redeem via redemption engine
    result = await redemption_engine.redeem_code(
        code=code,
        player_id=player_id,
        player_fid=player_fid
    )
    
    # Log the redemption attempt
    await audit_log.log(
        user_id=str(player_id),
        user_name=f"Alliance:{alliance_id}",
        action=f"redeem_gift_code:{code}",
        category=AuditCategory.GIFT_CODES,
        details={
            "code": code,
            "alliance_id": alliance_id,
            "success": result.get("success", False),
            "error": result.get("error"),
            "message": result.get("message")
        }
    )
    
    if result.get("success"):
        return True, result.get("message", "تم استرداد الكود بنجاح")
    else:
        return False, result.get("message", result.get("error", "فشل استرداد الكود"))


async def validate_gift_code(code: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate a gift code before redemption.
    
    Args:
        code: The gift code to validate
        
    Returns:
        Tuple of (valid: bool, message: str, details: dict)
    """
    code = code.upper().strip()
    
    # Check format
    if not redemption_engine._validate_code_format(code):
        return False, "صيغة الكود غير صحيحة", {}
    
    # Check if exists
    gift_code = await gift_code_service.get_code_by_code(code)
    
    if not gift_code:
        return False, "الكود غير موجود", {}
    
    # Check status
    if gift_code.status == GiftCodeStatus.REDEEMED:
        return False, "الكود مستخدم مسبقاً", {"status": "redeemed"}
    
    if gift_code.status == GiftCodeStatus.EXPIRED:
        return False, "الكود منتهي الصلاحية", {"status": "expired"}
    
    if gift_code.status == GiftCodeStatus.ALREADY_REDEEMED:
        return False, "الكود مستخدم مسبقاً", {"status": "already_redeemed"}
    
    if gift_code.status == GiftCodeStatus.PENDING:
        return False, "الكود غير مفعل بعد", {"status": "pending"}
    
    # Return valid
    return True, "الكود صالح للاستخدام", {
        "status": gift_code.status.value
    }


async def get_alliance_gift_history(
    alliance_id: int,
    limit: int = 50
) -> list:
    """
    Get gift code redemption history for an alliance.
    
    Args:
        alliance_id: The alliance database ID
        limit: Maximum number of records to return
        
    Returns:
        List of redemption records
    """
    # Get player_id from alliance
    alliance = await db.fetchone(
        "SELECT * FROM alliances WHERE id = ?",
        (alliance_id,)
    )
    
    if not alliance:
        return []
    
    # Get player from players table
    player = await db.fetchone(
        "SELECT id, fid FROM players WHERE alliance_id = ? AND is_active = 1 LIMIT 1",
        (alliance_id,)
    )

    if not player:
        return []

    player_id = player["id"]

    # Get redemptions
    redemptions = await db.fetchall("""
        SELECT gr.*, gc.code, gc.code_type, gc.value, gc.created_at as code_created
        FROM gift_redemptions gr
        JOIN gift_codes gc ON gr.code_id = gc.id
        WHERE gr.player_id = ?
        ORDER BY gr.redeemed_at DESC
        LIMIT ?
    """, (player_id, limit))
    
    return redemptions
