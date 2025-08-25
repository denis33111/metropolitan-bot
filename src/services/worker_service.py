#!/usr/bin/env python3
"""
👥 WORKER SERVICE
Handles worker registration and verification
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class WorkerService:
    """Service for managing worker data and registration"""
    
    def __init__(self, sheets_service):
        self.sheets_service = sheets_service
    
    async def check_worker_exists(self, telegram_id: int) -> bool:
        """Check if a worker exists by Telegram ID"""
        worker = await self.sheets_service.find_worker_by_telegram_id(telegram_id)
        return worker is not None
    
    async def register_worker(self, telegram_id: int, name: str, phone: str) -> bool:
        """Register a new worker"""
        return await self.sheets_service.add_worker(telegram_id, name, phone)
    
    async def get_worker_status(self, telegram_id: int) -> str:
        """Get current status of a worker"""
        worker = await self.sheets_service.find_worker_by_telegram_id(telegram_id)
        if worker:
            return worker.get('status', 'UNKNOWN')
        return 'NOT_FOUND'
    
    async def get_worker_data(self, telegram_id: int) -> Optional[Dict]:
        """Get complete worker data"""
        return await self.sheets_service.find_worker_by_telegram_id(telegram_id)
