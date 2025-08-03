"""
Handler functions for the Telegram Time Control Bot.
Contains all message handlers and time validation logic.
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from bot.config import (
    WELCOME_MESSAGE, 
    OUTSIDE_HOURS_MESSAGE, 
    GENERAL_RESPONSE_MESSAGE,
    ALLOWED_START_HOUR,
    ALLOWED_END_HOUR
)

logger = logging.getLogger(__name__)

def is_within_allowed_hours() -> bool:
    """
    Check if current time is within allowed hours.
    
    Returns:
        bool: True if current time is within allowed hours, False otherwise
    """
    current_time = datetime.now()
    current_hour = current_time.hour
    
    return ALLOWED_START_HOUR <= current_hour < ALLOWED_END_HOUR

def get_current_time_string() -> str:
    """
    Get current time as formatted string.
    
    Returns:
        str: Current time in HH:MM format
    """
    return datetime.now().strftime("%H:%M")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    logger.info(f"Start command received from user {user.id} (@{user.username}) in chat {chat_id}")
    
    try:
        await update.message.reply_text(
            WELCOME_MESSAGE,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Welcome message sent to user {user.id}")
    except Exception as e:
        logger.error(f"Error sending welcome message to user {user.id}: {e}")
        await update.message.reply_text("Sorry, there was an error processing your request.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle regular text messages with time validation.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    message_text = update.message.text
    current_time = get_current_time_string()
    
    logger.info(f"Message received from user {user.id} (@{user.username}) at {current_time}: {message_text}")
    
    try:
        if is_within_allowed_hours():
            # Within allowed hours - process the message
            response = GENERAL_RESPONSE_MESSAGE.format(
                message=message_text,
                current_time=current_time
            )
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Response sent to user {user.id} during allowed hours")
        else:
            # Outside allowed hours - send rejection message
            response = OUTSIDE_HOURS_MESSAGE.format(current_time=current_time)
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Outside hours message sent to user {user.id} at {current_time}")
            
    except Exception as e:
        logger.error(f"Error handling message from user {user.id}: {e}")
        await update.message.reply_text(
            "Sorry, there was an error processing your message. Please try again later."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle errors that occur during bot operation.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    logger.error(f"Update {update} caused error {context.error}")
    
    # If we have an update and it has a message, try to send an error response
    if update and update.message:
        try:
            await update.message.reply_text(
                "🚫 An unexpected error occurred. Please try again later or contact support."
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
