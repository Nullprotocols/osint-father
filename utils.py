import html
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from functools import wraps
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from config import config
from database import db

def format_json_output(data: Dict, max_length: int = 4000) -> str:
    """Format JSON for display with syntax highlighting"""
    try:
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        # HTML formatting for Telegram
        formatted = f"<pre><code class=\"language-json\">{html.escape(json_str)}</code></pre>"
        
        # Add footer
        formatted += f"\n\n🏆 <b>Developer</b>: {config.UI['developer']}\n"
        formatted += f"⚡ <b>Powered By</b>: {config.UI['powered_by']}"
        
        return formatted
    except Exception as e:
        return f"❌ Error formatting output: {str(e)}"

def create_buttons(buttons_data: List[List[Dict]]) -> InlineKeyboardMarkup:
    """Create inline keyboard markup from button data"""
    keyboard = []
    for row in buttons_data:
        keyboard_row = []
        for button in row:
            if button.get('url'):
                keyboard_row.append(
                    InlineKeyboardButton(
                        text=button['text'],
                        url=button['url']
                    )
                )
            else:
                keyboard_row.append(
                    InlineKeyboardButton(
                        text=button['text'],
                        callback_data=button.get('callback_data', button['text'])
                    )
                )
        keyboard.append(keyboard_row)
    return InlineKeyboardMarkup(keyboard)

async def send_to_log_channel(command: str, user, query: str, result: Dict, context):
    """Send lookup result to appropriate log channel"""
    try:
        log_channel = config.LOG_CHANNELS.get(command)
        if not log_channel:
            return
        
        # Format message
        message = f"""
🔍 <b>NEW LOOKUP - {command.upper()}</b>

👤 <b>User Information:</b>
├ ID: <code>{user.id}</code>
├ Username: @{user.username or 'N/A'}
├ Name: {user.first_name} {user.last_name or ''}

🔎 <b>Lookup Details:</b>
├ Type: {command}
├ Query: <code>{html.escape(query)}</code>
├ Status: {'✅ Success' if result.get('success', False) else '❌ Failed'}
└ Response Time: {result.get('response_time_ms', 'N/A')}ms

📊 <b>Result Summary:</b>
{str(result)[:200]}...

⏰ <b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🏆 <b>Developer</b>: {config.UI['developer']}
⚡ <b>Powered By</b>: {config.UI['powered_by']}
        """
        
        await context.bot.send_message(
            chat_id=log_channel.channel_id,
            text=message,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        print(f"Error sending to log channel: {e}")

async def check_channel_membership(user_id: int, context) -> bool:
    """Check if user has joined all required channels"""
    try:
        for channel_id in config.FORCE_JOIN_CHANNELS:
            try:
                member = await context.bot.get_chat_member(channel_id, user_id)
                if member.status in ['left', 'kicked']:
                    return False
            except Exception as e:
                print(f"Error checking channel {channel_id}: {e}")
                continue
        
        return True
    except Exception as e:
        print(f"Error in channel membership check: {e}")
        return True  # Allow if error

def rate_limit_decorator(func: Callable):
    """Decorator for rate limiting commands"""
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Admins bypass rate limit
        if user_id in config.ADMIN_IDS or user_id == config.OWNER_ID:
            return await func(update, context, *args, **kwargs)
        
        # Check rate limit
        command = func.__name__.replace('_lookup', '')
        if not db.check_rate_limit(user_id, command, config.RATE_LIMIT['user_per_minute']):
            await update.message.reply_text(
                f"⚠️ <b>Rate Limit Exceeded</b>\n\n"
                f"You've used /{command} too many times. Please wait 1 minute.",
                parse_mode=ParseMode.HTML
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def admin_required(func: Callable):
    """Decorator for admin-only commands"""
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS and user_id != config.OWNER_ID:
            await update.message.reply_text(
                "❌ <b>Access Denied</b>\n\n"
                "This command is for administrators only.",
                parse_mode=ParseMode.HTML
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def format_size(bytes_size: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def get_time_ago(timestamp: datetime) -> str:
    """Get human readable time difference"""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"

def validate_input(input_str: str, input_type: str) -> bool:
    """Validate user input based on type"""
    if not input_str:
        return False
    
    if input_type == 'phone':
        # Basic phone validation
        return input_str.replace('+', '').replace(' ', '').isdigit() and len(input_str) >= 10
    
    elif input_type == 'email':
        # Basic email validation
        return '@' in input_str and '.' in input_str
    
    elif input_type == 'vehicle':
        # Basic vehicle number validation
        return len(input_str) >= 6 and any(c.isalpha() for c in input_str) and any(c.isdigit() for c in input_str)
    
    elif input_type == 'ip':
        # Basic IP validation
        parts = input_str.split('.')
        if len(parts) != 4:
            return False
        return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)
    
    return True
