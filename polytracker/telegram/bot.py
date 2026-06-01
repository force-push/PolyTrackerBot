"""Telegram bot for PolyTracker alerts."""

from loguru import logger
from telegram import Bot
from telegram.error import TelegramError

from polytracker.telegram.alerts import format_standard_alert, format_high_conviction_alert


class TelegramBot:
    """Telegram bot for sending trade alerts."""
    
    def __init__(self, telegram_config):
        """Initialize Telegram bot.
        
        Args:
            telegram_config: TelegramConfig object with bot_token and channel_id
        """
        self.config = telegram_config
        self.bot = Bot(token=telegram_config.bot_token)
        self.channel_id = telegram_config.channel_id
    
    async def send_message(
        self,
        channel_id: str | None = None,
        message: str = "",
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a message to a Telegram channel.
        
        Args:
            channel_id: Channel ID (uses self.channel_id if not provided)
            message: Message text (HTML format)
            parse_mode: Parse mode ('HTML', 'Markdown', 'MarkdownV2')
        
        Returns:
            True if sent successfully, False on error
        """
        target_channel = channel_id or self.channel_id
        
        if not message:
            logger.warning("Empty message, skipping send")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=target_channel,
                text=message,
                parse_mode=parse_mode,
            )
            logger.debug(f"✅ Message sent to {target_channel}")
            return True
        
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
        
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def send_alert(self, alert_type: str, data: dict) -> bool:
        """Send a trade signal alert.
        
        Args:
            alert_type: 'standard' or 'high_conviction'
            data: Dict with keys:
                - wallet: Wallet dict
                - position: Position dict
                - market: Market dict (may be empty)
        
        Returns:
            True if sent successfully
        """
        try:
            if alert_type == 'high_conviction':
                message = format_high_conviction_alert(data)
            else:
                message = format_standard_alert(data)
            
            if not message:
                logger.warning("Alert format returned empty message")
                return False
            
            return await self.send_message(message=message)
        
        except Exception as e:
            logger.error(f"Failed to format/send alert: {e}")
            return False
