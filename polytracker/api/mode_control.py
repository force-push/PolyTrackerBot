"""Mode control API for switching execution modes at runtime."""

import os
import json
from pathlib import Path
from loguru import logger
from enum import Enum


class ExecutionMode(str, Enum):
    """Execution modes."""
    DRY_RUN = "DRY_RUN"
    DEMO = "DEMO"
    LIVE = "LIVE"


class ModeController:
    """Controls execution mode via .env file updates."""
    
    def __init__(self, env_path: str = ".env"):
        """Initialize mode controller.
        
        Args:
            env_path: Path to .env file
        """
        self.env_path = Path(env_path)
    
    def get_current_mode(self) -> str:
        """Get current execution mode from .env.
        
        Returns:
            Current execution mode (DRY_RUN, DEMO, LIVE)
        """
        if not self.env_path.exists():
            return ExecutionMode.DRY_RUN.value
        
        with open(self.env_path) as f:
            for line in f:
                if line.strip().startswith("EXECUTION_MODE="):
                    return line.strip().split("=", 1)[1].strip()
        
        return ExecutionMode.DRY_RUN.value
    
    def set_mode(self, mode: str) -> dict:
        """Change execution mode.
        
        Args:
            mode: Target mode (DRY_RUN, DEMO, LIVE)
            
        Returns:
            Status dict with success flag and message
        """
        # Validate mode
        try:
            ExecutionMode(mode)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid mode: {mode}. Valid modes: {[m.value for m in ExecutionMode]}"
            }
        
        current = self.get_current_mode()
        
        # Safety check: require confirmation before switching to LIVE
        if mode == ExecutionMode.LIVE.value and current != ExecutionMode.LIVE.value:
            return {
                "success": False,
                "error": "LIVE mode requires explicit confirmation. Use set_mode_confirmed() instead.",
                "warning": "LIVE mode trades with REAL MONEY. This is irreversible."
            }
        
        # Read current .env
        if not self.env_path.exists():
            lines = []
        else:
            with open(self.env_path) as f:
                lines = f.readlines()
        
        # Update or add EXECUTION_MODE
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("EXECUTION_MODE="):
                new_lines.append(f"EXECUTION_MODE={mode}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"EXECUTION_MODE={mode}\n")
        
        # Write back
        with open(self.env_path, "w") as f:
            f.writelines(new_lines)
        
        logger.info(f"✅ Execution mode changed: {current} → {mode}")
        
        return {
            "success": True,
            "message": f"Mode changed to {mode}. Bot will use new mode on next restart.",
            "previous_mode": current,
            "new_mode": mode,
            "requires_restart": True
        }
    
    def set_mode_confirmed(self, mode: str) -> dict:
        """Change mode with LIVE confirmation.
        
        Args:
            mode: Target mode
            
        Returns:
            Status dict
        """
        if mode == ExecutionMode.LIVE.value:
            logger.warning(f"⚠️ SWITCHING TO LIVE MODE - REAL MONEY TRADING ENABLED")
        
        return self.set_mode(mode)
    
    def get_info(self) -> dict:
        """Get current mode info.
        
        Returns:
            Dict with mode, available modes, and descriptions
        """
        return {
            "current_mode": self.get_current_mode(),
            "available_modes": [
                {
                    "mode": ExecutionMode.DRY_RUN.value,
                    "description": "Logging only, no orders",
                    "money_risk": "None"
                },
                {
                    "mode": ExecutionMode.DEMO.value,
                    "description": "Paper trading on demo account",
                    "money_risk": "None (demo funds)"
                },
                {
                    "mode": ExecutionMode.LIVE.value,
                    "description": "Real money trading",
                    "money_risk": "REAL MONEY ⚠️"
                }
            ]
        }
