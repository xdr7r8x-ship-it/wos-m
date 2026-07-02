"""
Gift Code Integration for WOS-M
© MANSOUR — WOS-M. All rights reserved.

Components:
- onnx_captcha_solver: ONNX-based CAPTCHA solver
- redemption_engine: Core redemption logic
- distribution_api: Code sharing with other servers
- gift_service: Main service integration
"""
from integrations.gift_codes.onnx_captcha_solver import GiftCaptchaSolver
from integrations.gift_codes.redemption_engine import GiftRedemptionEngine
from integrations.gift_codes.distribution_api import GiftDistributionAPI
from integrations.gift_codes.gift_service import GiftCodeService

__all__ = [
    'GiftCaptchaSolver',
    'GiftRedemptionEngine',
    'GiftDistributionAPI',
    'GiftCodeService'
]
