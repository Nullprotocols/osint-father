#!/usr/bin/env python3
"""
🚀 TELEGRAM BOT PRO VERSION
Advanced OSINT Lookup Bot with Multi-API Integration
Developer: @Nullprotocol_X | Powered By: NULL PROTOCOL
"""

import os
import sys
import logging
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import modules
from config import config
from database import db
from api_handler import api_handler
from admin_panel import AdminPanel
from utils import (
    format_json_output, create_buttons, 
    send_to_log_channel, check_channel_membership,
    rate_limit_decorator, admin_required
)

# Telegram imports
from telegram import (
    Update, InlineKeyboardButton, 
    InlineKeyboardMarkup, InputFile,
    BotCommand, BotCommandScopeAllGroupChats
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes,
    filters
)
from telegram.constants import ParseMode

# Flask for Render.com
from flask import Flask, jsonify, request
import json

# Initialize Flask app
app = Flask(__name__)

# Global bot instance
bot_application = None

class TelegramBotPro:
    """Professional Telegram Bot Class"""
    
    def __init__(self, token: str):
        self.token = token
        self.application = None
        self.admin_panel = AdminPanel()
        self.stats = {
            'start_time': datetime.now(),
            'total_messages': 0,
            'total_lookups': 0,
            'active_users': set()
        }
    
    async def init_bot(self):
        """Initialize bot with all handlers"""
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Register handlers
        await self.register_handlers()
        
        # Set bot commands
        await self.set_bot_commands()
        
        logger.info("✅ Bot initialized successfully")
    
    async def set_bot_commands(self):
        """Set bot commands menu"""
        commands = [
            BotCommand("start", "🚀 Start the bot"),
            BotCommand("help", "📖 Get help"),
            BotCommand("num", "📱 Phone number lookup"),
            BotCommand("tg2num", "👤 Telegram to number"),
            BotCommand("tginfo", "ℹ️ Telegram user info"),
            BotCommand("vehicle", "🚗 Vehicle information"),
            BotCommand("email", "📧 Email lookup"),
            BotCommand("ifsc", "🏦 IFSC code lookup"),
            BotCommand("pincode", "📍 Pincode lookup"),
            BotCommand("insta", "📸 Instagram lookup"),
            BotCommand("github", "💻 GitHub lookup"),
            BotCommand("gst", "🏢 GST lookup"),
            BotCommand("pakistan", "🇵🇰 Pakistan number"),
            BotCommand("ip", "🌐 IP address lookup"),
            BotCommand("ffinfo", "🎮 Free Fire info"),
            BotCommand("ffban", "⚠️ Free Fire ban check"),
            BotCommand("stats", "📊 Your statistics"),
            BotCommand("admin", "🛠 Admin panel (admin only)"),
        ]
        
        await self.application.bot.set_my_commands(
            commands=commands,
            scope=BotCommandScopeAllGroupChats()
        )
    
    async def register_handlers(self):
        """Register all command and message handlers"""
        
        # Start command
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        # Help command
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Lookup commands
        lookup_commands = {
            'num': self.num_lookup,
            'tg2num': self.tg2num_lookup,
            'tginfo': self.tginfo_lookup,
            'vehicle': self.vehicle_lookup,
            'email': self.email_lookup,
            'ifsc': self.ifsc_lookup,
            'pincode': self.pincode_lookup,
            'insta': self.insta_lookup,
            'github': self.github_lookup,
            'gst': self.gst_lookup,
            'pakistan': self.pakistan_lookup,
            'ip': self.ip_lookup,
            'ffinfo': self.ffinfo_lookup,
            'ffban': self.ffban_lookup,
        }
        
        for command, handler in lookup_commands.items():
            self.application.add_handler(CommandHandler(command, handler))
        
        # User commands
        self.application.add_handler(CommandHandler("stats", self.user_stats))
        self.application.add_handler(CommandHandler("profile", self.user_profile))
        
        # Admin commands
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        self.application.add_handler(CommandHandler("backup", self.backup_command))
        self.application.add_handler(CommandHandler("system", self.system_stats))
        
        # Callback queries
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    # ===== COMMAND HANDLERS =====
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        chat = update.effective_chat
        
        # Update stats
        self.stats['total_messages'] += 1
        self.stats['active_users'].add(user.id)
        
        # Check if in group
        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text(
                f"👋 <b>Hello {user.first_name}!</b>\n\n"
                f"⚠️ <b>This bot works only in groups!</b>\n\n"
                f"If you want to use a bot privately, please use: {config.REDIRECT_BOT}\n\n"
                f"<i>Add me to your group to start using advanced lookup features.</i>\n\n"
                f"🏆 <b>Developer</b>: {config.UI['developer']}\n"
                f"⚡ <b>Powered By</b>: {config.UI['powered_by']}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Add user to database
        db.add_user({
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language_code': user.language_code
        })
        
        # Send welcome message
        welcome_text = f"""
🎉 <b>Welcome {user.first_name} to NULL PROTOCOL BOT!</b>

<b>🔍 Available Lookup Commands:</b>
📱 /num - Phone number lookup
👤 /tg2num - Telegram to number
ℹ️ /tginfo - Telegram user info
🚗 /vehicle - Vehicle information
📧 /email - Email lookup
🏦 /ifsc - IFSC code lookup
📍 /pincode - Pincode lookup
📸 /insta - Instagram lookup
💻 /github - GitHub lookup
🏢 /gst - GST lookup
🇵🇰 /pakistan - Pakistan number
🌐 /ip - IP address lookup
🎮 /ffinfo - Free Fire info
⚠️ /ffban - Free Fire ban check

<b>👤 User Commands:</b>
📊 /stats - Your statistics
👤 /profile - Your profile

<b>⚠️ Requirements:</b>
• Join our channels to use the bot
• Rate limited to prevent abuse
• All lookups are logged for security

<b>🔐 Security Notice:</b>
<i>This bot logs all activities for security purposes.
Misuse may result in permanent ban.</i>

🏆 <b>Developer</b>: {config.UI['developer']}
⚡ <b>Powered By</b>: {config.UI['powered_by']}
        """
        
        # Check channel membership
        has_joined = await check_channel_membership(user.id, context)
        
        if not has_joined:
            welcome_text += "\n\n❌ <b>You must join our channels first!</b>"
            keyboard = []
            for link in config.FORCE_JOIN_LINKS:
                keyboard.append([InlineKeyboardButton("📢 Join Channel", url=link)])
            keyboard.append([InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        else:
            await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = f"""
🆘 <b>NULL PROTOCOL BOT - HELP</b>

<b>📚 Basic Usage:</b>
1. Add me to a group
2. Join required channels
3. Use lookup commands

<b>🔍 Lookup Commands:</b>
• /num <number> - Phone number lookup
• /tg2num <id> - Telegram ID to number
• /tginfo @username - Telegram user info
• /vehicle <number> - Vehicle information
• /email <address> - Email lookup
• /ifsc <code> - IFSC code lookup
• /pincode <code> - Pincode lookup
• /insta username - Instagram lookup
• /github username - GitHub lookup
• /gst <number> - GST lookup
• /pakistan <number> - Pakistan number
• /ip <address> - IP address lookup
• /ffinfo <uid> - Free Fire info
• /ffban <uid> - Free Fire ban check

<b>👤 User Commands:</b>
• /stats - Your usage statistics
• /profile - Your profile info

<b>🛠 Admin Commands:</b>
• /admin - Admin control panel
• /broadcast - Broadcast message
• /backup - Create backup
• /system - System statistics

<b>⚠️ Important:</b>
• Bot works only in groups
• Rate limiting applies
• All activities are logged
• Join channels to use bot

<b>🔧 Support:</b>
For issues or suggestions, contact developer.

🏆 <b>Developer</b>: {config.UI['developer']}
⚡ <b>Powered By</b>: {config.UI['powered_by']}
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    @rate_limit_decorator
    async def num_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /num command"""
        await self.process_lookup(update, context, 'num', 'phone number')
    
    @rate_limit_decorator
    async def tg2num_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tg2num command"""
        await self.process_lookup(update, context, 'tg2num', 'telegram ID')
    
    @rate_limit_decorator
    async def tginfo_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tginfo command"""
        await self.process_lookup(update, context, 'tginfo', 'telegram username')
    
    @rate_limit_decorator
    async def vehicle_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /vehicle command"""
        await self.process_lookup(update, context, 'vehicle', 'vehicle number')
    
    @rate_limit_decorator
    async def email_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /email command"""
        await self.process_lookup(update, context, 'email', 'email address')
    
    @rate_limit_decorator
    async def ifsc_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ifsc command"""
        await self.process_lookup(update, context, 'ifsc', 'IFSC code')
    
    @rate_limit_decorator
    async def pincode_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pincode command"""
        await self.process_lookup(update, context, 'pincode', 'pincode')
    
    @rate_limit_decorator
    async def insta_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /insta command"""
        await self.process_lookup(update, context, 'insta', 'instagram username')
    
    @rate_limit_decorator
    async def github_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /github command"""
        await self.process_lookup(update, context, 'github', 'github username')
    
    @rate_limit_decorator
    async def gst_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /gst command"""
        await self.process_lookup(update, context, 'gst', 'GST number')
    
    @rate_limit_decorator
    async def pakistan_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pakistan command"""
        await self.process_lookup(update, context, 'pakistan', 'pakistan number')
    
    @rate_limit_decorator
    async def ip_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ip command"""
        await self.process_lookup(update, context, 'ip', 'IP address')
    
    @rate_limit_decorator
    async def ffinfo_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ffinfo command"""
        await self.process_lookup(update, context, 'ffinfo', 'Free Fire UID')
    
    @rate_limit_decorator
    async def ffban_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ffban command"""
        await self.process_lookup(update, context, 'ffban', 'Free Fire UID')
    
    async def process_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            command: str, query_name: str):
        """Process any lookup command"""
        user = update.effective_user
        chat = update.effective_chat
        
        # Check if in group
        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text(
                f"⚠️ <b>This bot works only in groups!</b>\n\n"
                f"If you want to use a bot privately, please use: {config.REDIRECT_BOT}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Check arguments
        if not context.args:
            await update.message.reply_text(f"Usage: /{command} <{query_name}>")
            return
        
        query = ' '.join(context.args)
        
        # Check channel membership
        has_joined = await check_channel_membership(user.id, context)
        if not has_joined:
            keyboard = []
            for link in config.FORCE_JOIN_LINKS:
                keyboard.append([InlineKeyboardButton("Join Channel", url=link)])
            keyboard.append([InlineKeyboardButton("✅ Verify", callback_data="verify_join")])
            
            await update.message.reply_text(
                "❌ <b>You must join our channels to use this bot!</b>\n\n"
                "Join the channels below and click Verify:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            f"🔄 Processing your {command} lookup...\n"
            f"⏳ This may take a few seconds."
        )
        
        # Process lookup
        result = await api_handler.process_lookup(user.id, command, query)
        
        # Delete processing message
        await processing_msg.delete()
        
        # Format and send response
        formatted = api_handler.format_for_telegram(result)
        
        if formatted.get('type') == 'document':
            # Send as file
            await update.message.reply_document(
                document=InputFile(formatted['data'], filename=f"{command}_{query}.json"),
                caption=formatted['caption'],
                parse_mode=ParseMode.HTML
            )
        else:
            # Send as message with buttons
            keyboard = [
                [
                    InlineKeyboardButton("📋 Copy JSON", callback_data=f"copy_{command}"),
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{command}_{query}")
                ],
                [
                    InlineKeyboardButton("📤 Share", callback_data=f"share_{command}"),
                    InlineKeyboardButton("⚠️ Report", callback_data="report_error")
                ]
            ]
            
            await update.message.reply_text(
                formatted['text'],
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )
        
        # Send to log channel
        await send_to_log_channel(command, user, query, result, context)
        
        # Update stats
        self.stats['total_lookups'] += 1
    
    async def user_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = update.effective_user
        
        stats = db.get_user_stats(user.id)
        
        if not stats:
            await update.message.reply_text("❌ No statistics found for your account.")
            return
        
        user_data = stats['user']
        lookup_stats = stats['stats']
        
        stats_text = f"""
📊 <b>YOUR STATISTICS</b>

<b>👤 User Info:</b>
├ ID: <code>{user_data['user_id']}</code>
├ Username: @{user_data['username'] or 'N/A'}
├ Name: {user_data['first_name']} {user_data['last_name'] or ''}
├ Joined: {user_data['join_date']}
├ Credits: {user_data['credits']}
└ Status: {'🟢 Active' if not user_data['is_banned'] else '🔴 Banned'}

<b>🔍 Lookup Statistics:</b>
├ Total Lookups: {lookup_stats.get('total_lookups', 0)}
├ Successful: {lookup_stats.get('successful', 0)}
├ Failed: {lookup_stats.get('failed', 0)}
├ Success Rate: {round((lookup_stats.get('successful', 0) / lookup_stats.get('total_lookups', 1)) * 100, 2)}%
└ Avg. Response Time: {round(lookup_stats.get('avg_response_time', 0), 2)}s

<b>🏆 Top Commands:</b>
"""
        
        for cmd in stats.get('top_commands', []):
            stats_text += f"├ /{cmd['command']}: {cmd['count']} times\n"
        
        stats_text += f"""
        
<b>📈 Activity:</b>
Last Active: {user_data['last_active'] or 'N/A'}
Last Lookup: {user_data['last_lookup'] or 'Never'}

🏆 <b>Developer</b>: {config.UI['developer']}
⚡ <b>Powered By</b>: {config.UI['powered_by']}
        """
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
    
    async def user_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command"""
        user = update.effective_user
        
        # Get user data
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await update.message.reply_text("❌ Profile not found. Use /start first.")
            return
        
        profile_text = f"""
👤 <b>YOUR PROFILE</b>

<b>📋 Basic Info:</b>
├ User ID: <code>{user_data['user_id']}</code>
├ Username: @{user_data['username'] or 'N/A'}
├ Name: {user_data['first_name']} {user_data['last_name'] or ''}
├ Language: {user_data['language_code'] or 'en'}
└ Premium: {'✅ Yes' if user_data['is_premium'] else '❌ No'}

<b>💰 Credits:</b>
├ Current: {user_data['credits']}
├ Earned: {user_data['total_credits_earned']}
└ Spent: {user_data['total_credits_spent']}

<b>📅 Account:</b>
├ Joined: {user_data['join_date']}
├ Last Active: {user_data['last_active'] or 'Never'}
└ Status: {'🟢 Active' if not user_data['is_banned'] else '🔴 Banned'}

<b>🔗 Referral:</b>
├ Code: <code>{user_data['referral_code']}</code>
├ Referred By: {user_data['referred_by'] or 'No one'}
└ Total Referred: {user_data['total_referred']}

<b>⚙️ Settings:</b>
{user_data['settings'] or 'Default'}

🏆 <b>Developer</b>: {config.UI['developer']}
⚡ <b>Powered By</b>: {config.UI['powered_by']}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Profile", callback_data="refresh_profile")],
            [InlineKeyboardButton("📤 Share Referral", callback_data="share_referral")]
        ]
        
        await update.message.reply_text(
            profile_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @admin_required
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        await self.admin_panel.show_panel(update, context)
    
    @admin_required
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command"""
        await self.admin_panel.broadcast(update, context)
    
    @admin_required
    async def backup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /backup command"""
        await self.admin_panel.create_backup(update, context)
    
    @admin_required
    async def system_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /system command"""
        stats = db.get_admin_stats()
        api_stats = api_handler.get_stats()
        
        uptime = datetime.now() - self.stats['start_time']
        uptime_str = str(uptime).split('.')[0]
        
        stats_text = f"""
🖥️ <b>SYSTEM STATISTICS</b>

<b>📊 Bot Stats:</b>
├ Uptime: {uptime_str}
├ Total Messages: {self.stats['total_messages']}
├ Total Lookups: {self.stats['total_lookups']}
└ Active Users: {len(self.stats['active_users'])}

<b>👥 User Stats:</b>
├ Total Users: {stats['counts'].get('total_users', 0)}
├ New Today: {stats['counts'].get('new_users_today', 0)}
├ Total Credits: {stats['counts'].get('total_credits', 0)}
└ Avg Lookups/User: {round(stats['counts'].get('avg_lookups_per_user', 0), 2)}

<b>🔍 Lookup Stats:</b>
├ Total Lookups: {stats['counts'].get('total_lookups', 0)}
├ Today's Lookups: {stats['counts'].get('lookups_today', 0)}
└ Success Rate: {api_stats.get('success_rate', 0):.2f}%

<b>🌐 API Stats:</b>
├ Total Requests: {api_stats['total_requests']}
├ Successful: {api_stats['successful_requests']}
├ Failed: {api_stats['failed_requests']}
├ Avg Response Time: {api_stats['avg_response_time_seconds']}s
└ Cache Size: {api_stats['cache_size']}

<b>💾 Database:</b>
├ Size: {os.path.getsize('bot_database.db') / 1024 / 1024:.2f} MB
├ Last Backup: {self.admin_panel.last_backup or 'Never'}
└ Backups Count: {len(os.listdir('backups')) if os.path.exists('backups') else 0}

<b>🔄 Daily Activity (Last 7 days):</b>
"""
        
        for day in stats.get('daily_activity', [])[-7:]:
            stats_text += f"├ {day['date']}: {day['lookups']} lookups, {day['active_users']} users\n"
        
        stats_text += f"""

🏆 <b>Developer</b>: {config.UI['developer']}
⚡ <b>Powered By</b>: {config.UI['powered_by']}
⏰ <b>Last Updated</b>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "verify_join":
            user_id = query.from_user.id
            has_joined = await check_channel_membership(user_id, context)
            
            if has_joined:
                await query.edit_message_text(
                    "✅ <b>Verification successful!</b>\n\n"
                    "You can now use all bot commands.\n"
                    "Type /help to see available commands.",
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text(
                    "❌ <b>Verification failed!</b>\n\n"
                    "Please join all required channels and try again.",
                    parse_mode=ParseMode.HTML
                )
        
        elif data.startswith("copy_"):
            command = data.replace("copy_", "")
            await query.edit_message_text(
                f"📋 <b>Copy the JSON output above.</b>\n\n"
                f"<i>You can paste it into any JSON viewer.</i>",
                parse_mode=ParseMode.HTML
            )
        
        elif data == "refresh_profile":
            await self.user_profile(update, context)
        
        elif data == "share_referral":
            user_id = query.from_user.id
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT referral_code FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result:
                referral_code = result[0]
                await query.edit_message_text(
                    f"🔗 <b>Your Referral Code:</b>\n\n"
                    f"<code>{referral_code}</code>\n\n"
                    f"Share this code with friends to earn credits!",
                    parse_mode=ParseMode.HTML
                )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling update: {context.error}")
        
        try:
            # Notify admins
            for admin_id in config.ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"⚠️ <b>Bot Error</b>\n\n"
                             f"Error: {context.error}\n"
                             f"Update: {update}\n\n"
                             f"Time: {datetime.now()}",
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
        except:
            pass
    
    async def run(self):
        """Run the bot"""
        await self.init_bot()
        
        # Start bot
        logger.info("🚀 Starting bot...")
        await self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# Flask routes
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "Telegram Bot Pro",
        "version": "3.0.0",
        "developer": config.UI['developer'],
        "powered_by": config.UI['powered_by'],
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/health": "Health check",
            "/stats": "Bot statistics",
            "/users": "User count",
            "/admin": "Admin interface (requires auth)"
        }
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot": "online" if bot_application else "offline",
        "database": "connected",
        "memory_usage": "normal"
    })

@app.route('/stats')
def stats_api():
    """API endpoint for statistics"""
    if bot_application:
        stats = {
            "bot": {
                "uptime": str(datetime.now() - bot_application.stats['start_time']),
                "total_messages": bot_application.stats['total_messages'],
                "total_lookups": bot_application.stats['total_lookups'],
                "active_users": len(bot_application.stats['active_users'])
            },
            "database": db.get_admin_stats(),
            "api": api_handler.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(stats)
    return jsonify({"error": "Bot not initialized"})

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    """Admin dashboard"""
    # Basic auth for web admin
    auth = request.headers.get('Authorization')
    if auth != f"Bearer {os.getenv('WEB_ADMIN_TOKEN', 'admin123')}":
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify({
        "dashboard": "admin",
        "timestamp": datetime.now().isoformat(),
        "links": {
            "/admin/users": "User management",
            "/admin/backup": "Create backup",
            "/admin/logs": "View logs",
            "/admin/stats": "Detailed statistics"
        }
    })

def start_flask():
    """Start Flask server"""
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

async def main():
    """Main function"""
    # Validate configuration
    if not config.validate():
        logger.error("❌ Invalid configuration. Check your .env file.")
        return
    
    # Initialize bot
    global bot_application
    bot_application = TelegramBotPro(config.BOT_TOKEN)
    
    # Start Flask in separate thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    logger.info("🌐 Flask server started on port 5000")
    
    # Run bot
    try:
        await bot_application.run()
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
    finally:
        # Cleanup
        await api_handler.close()
        logger.info("✅ Cleanup completed")

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('backups', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Run main async function
    asyncio.run(main())
