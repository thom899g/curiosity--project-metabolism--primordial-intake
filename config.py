"""
Configuration and constants for the Predictive Gas Arbitrage Agent.
All sensitive values should be loaded from environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ChainConfig:
    """Configuration for each L2 chain"""
    name: str
    rpc_url: str
    chain_id: int
    native_token: str
    explorer_url: str
    safe_address: Optional[str] = None
    wallet_private_key: Optional[str] = None

@dataclass
class ModelConfig:
    """Machine Learning model configuration"""
    prediction_horizon_minutes: int = 1
    training_window_days: int = 30
    retrain_interval_hours: int = 24
    feature_window_blocks: int = 100

@dataclass
class StrategyConfig:
    """Trading strategy parameters"""
    min_profit_threshold_usd: float = 0.50
    max_slippage_bps: int = 50  # 0.5%
    max_gas_cost_usd: float = 0.10
    position_size_usd: float = 10.0
    cooldown_seconds: int = 60

@dataclass
class RiskConfig:
    """Risk management parameters"""
    daily_loss_limit_usd: float = 2.0
    max_concurrent_positions: int = 1
    circuit_breaker_enabled: bool = True
    max_prediction_error_threshold: float = 0.3  # 30%

@dataclass
class FirebaseConfig:
    """Firebase configuration"""
    service_account_path: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./service-account-key.json")
    project_id: str = os.getenv("FIREBASE_PROJECT_ID", "autonomy-engine-1")
    database_url: str = os.getenv("FIREBASE_DATABASE_URL", "")

# Chain configurations
OPTIMISM = ChainConfig(
    name="optimism",
    rpc_url=os.getenv("OPTIMISM_RPC_URL", "https://mainnet.optimism.io"),
    chain_id=10,
    native_token="ETH",
    explorer_url="https://optimistic.etherscan.io"
)

ARBITRUM = ChainConfig(
    name="arbitrum",
    rpc_url=os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
    chain_id=42161,
    native_token="ETH",
    explorer_url="https://arbiscan.io"
)

# Main configuration
CONFIG = {
    "chains": [OPTIMISM, ARBITRUM],
    "model": ModelConfig(),
    "strategy": StrategyConfig(),
    "risk": RiskConfig(),
    "firebase": FirebaseConfig(),
    "execution_delay_seconds": 2,  # Delay between monitoring cycles
    "health_check_port": 8080,  # Port for health check API
    "log_level": os.getenv("LOG_LEVEL", "INFO")
}

# Validate critical environment variables
def validate_config():
    """Validate that all required environment variables are set"""
    required_vars = [
        "WALLET_PRIVATE_KEY",
        "FIREBASE_SERVICE_ACCOUNT_PATH"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
    
    # Set wallet private keys
    private_key = os.getenv("WALLET_PRIVATE_KEY")
    OPTIMISM.wallet_private_key = private_key
    ARBITRUM.wallet_private_key = private_key
    
    # Set Safe addresses if provided
    if os.getenv("SAFE_ADDRESS_OPTIMISM"):
        OPTIMISM.safe_address = os.getenv("SAFE_ADDRESS_OPTIMISM")
    if os.getenv("SAFE_ADDRESS_ARBITRUM"):
        ARBITRUM.safe_address = os.getenv("SAFE_ADDRESS_ARBITRUM")

# Initialize configuration
validate_config()