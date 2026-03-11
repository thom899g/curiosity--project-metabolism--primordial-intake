"""
Robust data collection module for historical and real-time gas fee data.
Handles multiple RPC endpoints for redundancy and includes error recovery.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from web3 import Web3
from web3.exceptions import BlockNotFound
from firebase_admin import firestore

from config import CONFIG, OPTIMISM, ARBITRUM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCollector:
    """Collects and processes gas fee data from multiple chains"""
    
    def __init__(self):
        self.web3_clients = {}
        self.db = firestore.client()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize Web3 clients for each chain with multiple RPC endpoints
        self._init_web3_clients()
        
    def _init_web3_clients(self):
        """Initialize Web3 clients with fallback RPC endpoints"""
        rpc_endpoints = {
            "optimism": [
                OPTIMISM.rpc_url,
                "https://opt-mainnet.g.alchemy.com/v2/demo",
                "https://optimism.publicnode.com"
            ],
            "arbitrum": [
                ARBITRUM.rpc_url,
                "https://arb-mainnet.g.alchemy.com/v2/demo",
                "https://arbitrum.publicnode.com"
            ]
        }
        
        for chain_name, endpoints in rpc_endpoints.items():
            for endpoint in endpoints:
                try:
                    w3 = Web3(Web3.HTTPProvider(endpoint, request_kwargs={'timeout': 30}))
                    if w3.is_connected():
                        self.web3_clients[chain_name] = w3
                        logger.info(f"Connected to {chain_name} via {endpoint[:50]}...")
                        break
                except Exception as e:
                    logger.warning(f"Failed to connect to {chain_name} via {endpoint}: {e}")
                    continue
        
        if len(self.web3_clients) != 2:
            raise ConnectionError("Failed to connect to at least one RPC endpoint for each chain")
    
    def _get_median_fee(self, chain_name: str, block_number: int) -> Dict:
        """
        Get median gas fee data from the latest blocks for robustness
        Handles priority fee estimation and failed blocks
        """
        w3 = self.web3_clients[chain_name]
        fee_data = []
        
        try:
            # Get current block
            current_block = w3.eth.get_block(block_number)
            base_fee = current_block.get('baseFeePerGas', 0)
            
            if base_fee == 0:
                # For L2s without EIP-1559, estimate base fee
                base_fee = w3.eth.gas_price
            
            # Estimate priority fee by looking at pending transactions
            pending_tx_count = w3.eth.get_block_transaction_count('pending')
            
            # Get recent blocks for median calculation
            recent_blocks = []
            for i in range(5):
                try:
                    block = w3.eth.get_block(block_number - i)
                    recent_blocks.append(block)
                except (BlockNotFound, ValueError):
                    continue
            
            # Calculate median base fee from recent blocks
            if recent_blocks:
                base_fees = [b.get('baseFeePerGas', w3.eth.gas_price) for b in recent_blocks]
                base_fee = sorted(base_fees)[len(base_fees) // 2]
            
            return {
                'timestamp': datetime.utcnow(),
                'block_number': block_number,
                'base_fee_gwei': float(Web3.from_wei(base_fee, 'gwei')),
                'pending_tx_count': pending_tx_count,
                'chain': chain_name
            }
            
        except Exception as e:
            logger.error(f"Error getting fee data for {chain_name}: {e}")
            raise
    
    def collect_real_time_data(self) -> List[Dict]:
        """Collect real-time gas fee data from all chains"""
        fee_data = []
        
        for chain_name in