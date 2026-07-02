"""
Gift Code Distribution API Client for WOS-M
Based on Whiteout Project's gift_operationsapi module
© MANSOUR — WOS-M. All rights reserved.

This module handles:
- Syncing gift codes with the shared distribution server
- Broadcasting codes to all connected servers
- Receiving codes from other servers in the network
"""
import asyncio
import json
import logging
import random
import os
import re
import sqlite3
import ssl
from datetime import datetime
from typing import List, Tuple, Optional

import aiohttp
import discord as discord_module

logger = logging.getLogger(__name__)


class GiftDistributionAPI:
    """
    Gift code distribution API client.
    Syncs codes with shared gift-code-api service.
    """
    
    def __init__(self, bot, db: sqlite3.Connection):
        self.bot = bot
        self.db = db
        self.cursor = db.cursor()
        
        # API Configuration
        self.api_url = "http://gift-code-api.whiteout-bot.com/giftcode_api.php"
        self.api_key = os.environ.get("GIFT_API_KEY", "")
        
        # Rate limiting
        self.min_check_interval = 300  # 5 minutes
        self.max_check_interval = 600  # 10 minutes
        self.check_interval = random.randint(self.min_check_interval, self.max_check_interval)
        
        # Backoff configuration
        self.last_api_call = 0
        self.min_api_call_interval = 3
        self.error_backoff_time = 30
        self.cloudflare_backoff_time = 15
        self.max_backoff_time = 300
        self.current_backoff = self.error_backoff_time
        
        # SSL context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self.logger = logging.getLogger('gift.distribution')
        
        # Start API check task
        self._api_check_task = None
    
    async def start(self):
        """Start the distribution API sync task."""
        if self._api_check_task is None or self._api_check_task.done():
            self._api_check_task = asyncio.create_task(self._api_check_loop())
            self.logger.info("Distribution API sync started")
    
    async def stop(self):
        """Stop the distribution API sync task."""
        if self._api_check_task and not self._api_check_task.done():
            self._api_check_task.cancel()
            try:
                await self._api_check_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Distribution API sync stopped")
    
    async def _api_check_loop(self):
        """Main API check loop with exponential backoff."""
        try:
            await asyncio.sleep(60)  # Initial delay
            
            while True:
                try:
                    success = await self.sync_with_api()
                    
                    if success:
                        self.current_backoff = self.error_backoff_time
                        self.check_interval = random.randint(
                            self.min_check_interval, 
                            self.max_check_interval
                        )
                        await asyncio.sleep(self.check_interval)
                    else:
                        jitter = random.uniform(0.75, 1.25)
                        backoff_time = min(self.current_backoff * jitter, self.max_backoff_time)
                        self.logger.warning(f"API sync failed, backing off for {backoff_time:.1f}s")
                        await asyncio.sleep(backoff_time)
                        self.current_backoff = min(self.current_backoff * 2, self.max_backoff_time)
                        
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    self.logger.exception(f"Error in API check loop: {e}")
                    await asyncio.sleep(self.current_backoff)
                    self.current_backoff = min(self.current_backoff * 2, self.max_backoff_time)
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.exception(f"Fatal error in API check loop: {e}")
    
    async def _wait_for_rate_limit(self):
        """Enforce rate limiting between API calls."""
        now = datetime.now().timestamp()
        time_since_last_call = now - self.last_api_call
        
        if time_since_last_call < self.min_api_call_interval:
            sleep_time = self.min_api_call_interval - time_since_last_call
            sleep_time += random.uniform(0, 0.5)
            await asyncio.sleep(sleep_time)
        
        self.last_api_call = datetime.now().timestamp()
    
    async def _handle_api_error(self, response: aiohttp.ClientResponse, response_text: str) -> float:
        """Handle API errors and return backoff time."""
        if response.status == 429 or response.status == 1015:
            self.logger.warning(f"Rate limit triggered: {response.status}")
            backoff = max(self.cloudflare_backoff_time, self.current_backoff)
            backoff *= random.uniform(1.0, 1.5)
            self.current_backoff = min(self.current_backoff * 2, self.max_backoff_time)
            return backoff
        elif response.status in [502, 503, 504]:
            self.logger.warning(f"Server error: {response.status}")
            backoff = self.current_backoff * random.uniform(0.75, 1.25)
            self.current_backoff = min(self.current_backoff * 2, self.max_backoff_time)
            return backoff
        else:
            self.logger.error(f"API error: {response.status}, {response_text[:200]}")
            return self.current_backoff * random.uniform(0.75, 1.25)
    
    async def sync_with_api(self) -> bool:
        """
        Synchronize gift codes with the distribution API.
        
        - Fetches new codes from API
        - Pushes our valid codes to API
        - Removes invalid codes
        """
        try:
            self.logger.info("Starting API synchronization")
            
            # Get our codes from database
            self.cursor.execute(
                "SELECT code, created_at, status FROM gift_codes WHERE status != 'invalid'"
            )
            db_codes = {row[0]: (row[1], row[2]) for row in self.cursor.fetchall()}
            
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
                headers = {
                    'Content-Type': 'application/json',
                    'X-API-Key': self.api_key,
                    'User-Agent': 'WOS-M/1.0'
                }
                
                await self._wait_for_rate_limit()
                
                try:
                    async with session.get(self.api_url, headers=headers, timeout=60) as response:
                        response_text = await response.text()
                        
                        if response.status != 200:
                            backoff_time = await self._handle_api_error(response, response_text)
                            await asyncio.sleep(backoff_time)
                            return False
                        
                        try:
                            result = json.loads(response_text)
                            
                            if 'error' in result or 'detail' in result:
                                error_msg = result.get('error', result.get('detail', 'Unknown error'))
                                self.logger.error(f"API returned error: {error_msg}")
                                return False
                            
                            api_giftcodes = result.get('codes', [])
                            self.logger.info(f"Received {len(api_giftcodes)} codes from API")
                            
                            # Parse and validate codes from API
                            new_codes = []
                            for code_line in api_giftcodes:
                                parts = code_line.strip().split()
                                if len(parts) != 2:
                                    continue
                                
                                code, date_str = parts
                                if not re.match("^[a-zA-Z0-9]+$", code):
                                    continue
                                
                                try:
                                    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                                    if code not in db_codes:
                                        new_codes.append((code, date_obj.strftime("%Y-%m-%d")))
                                except ValueError:
                                    continue
                            
                            # Add new codes to our database
                            for code, date_str in new_codes:
                                try:
                                    self.cursor.execute("""
                                        INSERT OR IGNORE INTO gift_codes 
                                        (code, created_at, status, validation_status)
                                        VALUES (?, ?, 'active', 'pending')
                                    """, (code, date_str))
                                    
                                    # Notify about new code
                                    await self._notify_new_code(code, date_str)
                                    
                                except Exception as e:
                                    self.logger.exception(f"Error inserting new code {code}: {e}")
                            
                            self.db.commit()
                            
                            # Push our valid codes to API
                            valid_codes = [
                                (code, date) for code, (date, status) in db_codes.items()
                                if status not in ['invalid', 'pending']
                            ]
                            
                            if valid_codes:
                                await self._push_codes_to_api(valid_codes, session, headers)
                            
                            self.logger.info("API synchronization completed successfully")
                            return True
                            
                        except json.JSONDecodeError as e:
                            self.logger.exception(f"JSON decode error: {e}")
                            return False
                            
                except aiohttp.ClientError as e:
                    self.logger.warning(f"Connection error: {type(e).__name__}")
                    return False
                    
        except Exception as e:
            self.logger.exception(f"Unexpected error in sync_with_api: {e}")
            return False
    
    async def _push_codes_to_api(
        self, 
        codes: List[Tuple[str, str]], 
        session: aiohttp.ClientSession,
        headers: dict
    ):
        """Push validated codes to the distribution API."""
        for code, date in codes:
            try:
                # Check if code already exists in API
                exists = await self._check_code_exists(code, session, headers)
                if exists:
                    continue
                
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%d.%m.%Y")
                
                data = {
                    'code': code,
                    'date': formatted_date
                }
                
                await self._wait_for_rate_limit()
                
                async with session.post(self.api_url, json=data, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        self.logger.info(f"Successfully pushed code {code} to API")
                    elif response.status == 409:
                        self.logger.info(f"Code {code} already exists in API")
                    else:
                        response_text = await response.text()
                        if "invalid" in response_text.lower():
                            self.cursor.execute(
                                "UPDATE gift_codes SET status = 'invalid' WHERE code = ?",
                                (code,)
                            )
                            self.db.commit()
                        self.logger.warning(f"Failed to push code {code}: {response.status}")
                        
            except Exception as e:
                self.logger.exception(f"Error pushing code {code} to API: {e}")
                await asyncio.sleep(self.error_backoff_time)
    
    async def _check_code_exists(
        self, 
        code: str, 
        session: aiohttp.ClientSession,
        headers: dict
    ) -> bool:
        """Check if a code exists in the API."""
        try:
            await self._wait_for_rate_limit()
            
            async with session.get(
                f"{self.api_url}?action=check&giftcode={code}",
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('exists', False)
                return False
                
        except Exception as e:
            self.logger.warning(f"Error checking code {code}: {e}")
            return False
    
    async def _notify_new_code(self, code: str, date: str):
        """
        Notify about a new code from the API.
        This can be extended to post to Discord channels.
        """
        self.logger.info(f"New code from distribution API: {code} ({date})")
        
        # Get configured notification channels
        try:
            self.cursor.execute("""
                SELECT channel_id FROM gift_channels WHERE notify_enabled = 1
            """)
            channels = self.cursor.fetchall()
            
            for (channel_id,) in channels:
                channel = self.bot.get_channel(channel_id)
                if channel and isinstance(channel, discord_module.TextChannel):
                    try:
                        embed = discord_module.Embed(
                            title="🎁 كود هدية جديد",
                            description=f"**الكود:** `{code}`\n**التاريخ:** {date}",
                            color=0x00ff00
                        )
                        await channel.send(embed=embed)
                    except Exception as e:
                        self.logger.warning(f"Failed to notify channel {channel_id}: {e}")
                        
        except Exception as e:
            self.logger.warning(f"Error sending new code notification: {e}")
    
    async def add_code_to_api(self, code: str) -> bool:
        """
        Add a code to the distribution API.
        Called when a user submits a new code.
        """
        try:
            # Check if already in our database
            self.cursor.execute(
                "SELECT status FROM gift_codes WHERE code = ?",
                (code,)
            )
            result = self.cursor.fetchone()
            
            if result and result[0] in ['invalid', 'pending']:
                return False
            
            # Check if exists in API
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
                headers = {
                    'Content-Type': 'application/json',
                    'X-API-Key': self.api_key,
                    'User-Agent': 'WOS-M/1.0'
                }
                
                date_str = datetime.now().strftime("%d.%m.%Y")
                data = {
                    'code': code,
                    'date': date_str
                }
                
                await self._wait_for_rate_limit()
                
                async with session.post(self.api_url, json=data, headers=headers, timeout=30) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        result_data = json.loads(response_text)
                        if result_data.get('success'):
                            self.logger.info(f"Successfully added code {code} to API")
                            # Update local database
                            self.cursor.execute("""
                                INSERT OR REPLACE INTO gift_codes 
                                (code, created_at, status, validation_status)
                                VALUES (?, ?, 'active', 'validated')
                            """, (code, datetime.now().strftime("%Y-%m-%d")))
                            self.db.commit()
                            return True
                    elif response.status == 409:
                        self.logger.info(f"Code {code} already exists in API")
                        return True
                    else:
                        if "invalid" in response_text.lower():
                            self.cursor.execute(
                                "UPDATE gift_codes SET status = 'invalid' WHERE code = ?",
                                (code,)
                            )
                            self.db.commit()
                        return False
                        
        except Exception as e:
            self.logger.exception(f"Error adding code {code} to API: {e}")
            return False
    
    async def remove_code_from_api(self, code: str) -> bool:
        """
        Remove a code from the distribution API.
        Called when a code becomes invalid.
        """
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
                headers = {
                    'Content-Type': 'application/json',
                    'X-API-Key': self.api_key,
                    'User-Agent': 'WOS-M/1.0'
                }
                
                data = {'code': code}
                
                await self._wait_for_rate_limit()
                
                async with session.delete(self.api_url, json=data, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        self.logger.info(f"Successfully removed code {code} from API")
                        return True
                    else:
                        self.logger.warning(f"Failed to remove code {code}: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.exception(f"Error removing code {code} from API: {e}")
            return False
