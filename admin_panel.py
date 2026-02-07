import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import config
from database import db
from utils import format_size, get_time_ago

class AdminPanel:
    """Professional Admin Panel"""
    
    def __init__(self):
        self.last_backup = None
        self.broadcast_stats = {}
    
    async def show_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin control panel"""
        user_id = update.effective_user.id
        
        # Check if admin
        if user_id not in config.ADMIN_IDS and user_id != config.OWNER_ID:
            await update.message.reply_text("❌ Access denied!")
            return
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
                InlineKeyboardButton("👥 Users", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
                InlineKeyboardButton("💾 Backup", callback_data="admin_backup")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
                InlineKeyboardButton("📈 Analytics", callback_data="admin_analytics")
            ],
            [
                InlineKeyboardButton("🛠 Maintenance", callback_data="admin_maintenance"),
                InlineKeyboardButton("🔐 Security", callback_data="admin_security")
            ]
        ]
        
        if user_id == config.OWNER_ID:
            keyboard.append([
                InlineKeyboardButton("👑 Owner Panel", callback_data="admin_owner")
            ])
        
        await update.message.reply_text(
            f"🛠 <b>ADMIN CONTROL PANEL</b>\n\n"
            f"Welcome back, Admin!\n\n"
            f"👤 Admin ID: <code>{user_id}</code>\n"
            f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Select an option:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message to all users"""
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS and user_id != config.OWNER_ID:
            return
        
        # Check if replying to a message
        if update.message.reply_to_message:
            message = update.message.reply_to_message
            broadcast_type = 'reply'
        else:
            if not context.args:
                await update.message.reply_text(
                    "Usage: /broadcast <message>\n"
                    "Or reply to a message with /broadcast"
                )
                return
            message = ' '.join(context.args)
            broadcast_type = 'text'
        
        # Get all users
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = cursor.fetchall()
        conn.close()
        
        total_users = len(users)
        
        # Confirm broadcast
        confirm_keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Broadcast", callback_data=f"confirm_broadcast_{broadcast_type}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
            ]
        ]
        
        await update.message.reply_text(
            f"📢 <b>BROADCAST CONFIRMATION</b>\n\n"
            f"📝 Type: {broadcast_type.upper()}\n"
            f"👥 Recipients: {total_users} users\n"
            f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"<i>Are you sure you want to send this broadcast?</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(confirm_keyboard)
        )
        
        # Store broadcast data
        context.user_data['broadcast_data'] = {
            'message': message if broadcast_type == 'text' else None,
            'message_object': message if broadcast_type == 'reply' else None,
            'type': broadcast_type,
            'users': [u[0] for u in users],
            'admin_id': user_id
        }
    
    async def create_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create database backup"""
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS and user_id != config.OWNER_ID:
            return
        
        # Get backup format from arguments
        backup_format = 'all'
        if context.args:
            backup_format = context.args[0].lower()
            if backup_format not in ['all', 'db', 'csv', 'json']:
                backup_format = 'all'
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            f"🔄 Creating backup ({backup_format})...\n"
            f"This may take a moment."
        )
        
        # Create backup
        backup_files = db.create_backup(backup_format)
        
        # Update last backup time
        self.last_backup = datetime.now()
        
        if not backup_files:
            await processing_msg.edit_text("❌ Backup failed!")
            return
        
        # Send backup files
        for file_path in backup_files:
            file_name = os.path.basename(file_path)
            file_size = format_size(os.path.getsize(file_path))
            
            try:
                await update.message.reply_document(
                    document=InputFile(file_path),
                    caption=f"📦 Backup File\n\n"
                           f"📁 Name: {file_name}\n"
                           f"📊 Size: {file_size}\n"
                           f"🕐 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                           f"🏆 <b>Developer</b>: {config.UI['developer']}\n"
                           f"⚡ <b>Powered By</b>: {config.UI['powered_by']}",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Error sending {file_name}: {str(e)}")
        
        # Update processing message
        total_size = sum(os.path.getsize(f) for f in backup_files)
        await processing_msg.edit_text(
            f"✅ Backup completed!\n\n"
            f"📁 Files: {len(backup_files)}\n"
            f"📊 Total Size: {format_size(total_size)}\n"
            f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}"
        )
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed statistics"""
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS and user_id != config.OWNER_ID:
            return
        
        # Get statistics
        stats = db.get_admin_stats()
        
        # Format statistics
        stats_text = f"""
📊 <b>ADMIN STATISTICS</b>

<b>👥 Users:</b>
├ Total: {stats['counts'].get('total_users', 0)}
├ New Today: {stats['counts'].get('new_users_today', 0)}
├ Banned: {sum(1 for u in stats.get('top_users', []) if u.get('is_banned'))}
└ Average Credits: {stats['counts'].get('total_credits', 0) / max(stats['counts'].get('total_users', 1), 1):.0f}

<b>🔍 Lookups:</b>
├ Total: {stats['counts'].get('total_lookups', 0)}
├ Today: {stats['counts'].get('lookups_today', 0)}
├ Avg/User: {stats['counts'].get('avg_lookups_per_user', 0):.1f}
└ Success Rate: Calculate from commands...

<b>🏆 Top Users:</b>
"""
        
        for i, user in enumerate(stats.get('top_users', [])[:5], 1):
            stats_text += f"{i}. @{user.get('username', 'N/A')}: {user.get('total_lookups', 0)} lookups\n"
        
        stats_text += f"\n<b>📈 Commands Usage:</b>\n"
        
        for cmd in stats.get('commands', [])[:5]:
            success_rate = (cmd.get('success_count', 0) / max(cmd.get('count', 1), 1)) * 100
            stats_text += f"├ /{cmd['command']}: {cmd['count']} ({success_rate:.1f}%)\n"
        
        stats_text += f"""
        
<b>🌐 API Performance:</b>
"""
        
        for api in stats.get('api_performance', [])[:3]:
            stats_text += f"├ {api['api_name']}: {api['total_calls']} calls, {api['avg_response_time']:.2f}s\n"
        
        stats_text += f"""
        
⏰ <b>Last Updated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🏆 <b>Developer</b>: {config.UI['developer']}
⚡ <b>Powered By</b>: {config.UI['powered_by']}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats"),
                InlineKeyboardButton("📤 Export", callback_data="export_stats")
            ]
        ]
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user management panel"""
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS and user_id != config.OWNER_ID:
            return
        
        # Get page from arguments
        page = 1
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])
        
        # Get users for page
        conn = db.get_connection()
        cursor = conn.cursor()
        
        limit = 10
        offset = (page - 1) * limit
        
        cursor.execute('''
            SELECT user_id, username, first_name, last_name, join_date, is_banned, credits, total_lookups
            FROM users
            ORDER BY join_date DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        users = cursor.fetchall()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        total_pages = (total_users + limit - 1) // limit
        
        conn.close()
        
        # Format users list
        users_text = f"""
👥 <b>USER MANAGEMENT</b>

Page {page} of {total_pages} | Total Users: {total_users}

"""
        
        for i, user in enumerate(users, offset + 1):
            status = "🔴" if user['is_banned'] else "🟢"
            users_text += f"{i}. {status} <code>{user['user_id']}</code> | @{user['username'] or 'N/A'}\n"
            users_text += f"   👤 {user['first_name']} {user['last_name'] or ''}\n"
            users_text += f"   📅 {user['join_date']} | 🔍 {user['total_lookups']} | 💰 {user['credits']}\n\n"
        
        keyboard = []
        
        # Navigation buttons
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"users_page_{page-1}"))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"users_page_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # User action buttons
        action_buttons = [
            InlineKeyboardButton("🔍 Search", callback_data="search_user"),
            InlineKeyboardButton("📊 Stats", callback_data="user_stats_global"),
            InlineKeyboardButton("📤 Export", callback_data="export_users")
        ]
        keyboard.append(action_buttons)
        
        # Admin actions
        admin_buttons = [
            InlineKeyboardButton("🚫 Ban User", callback_data="ban_user"),
            InlineKeyboardButton("🟢 Unban", callback_data="unban_user"),
            InlineKeyboardButton("🗑 Delete", callback_data="delete_user")
        ]
        keyboard.append(admin_buttons)
        
        await update.message.reply_text(
            users_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin panel callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "admin_stats":
            await self.show_stats(update, context)
        
        elif data == "admin_users":
            await self.show_users(update, context)
        
        elif data.startswith("users_page_"):
            page = int(data.replace("users_page_", ""))
            context.args = [str(page)]
            await self.show_users(update, context)
        
        elif data.startswith("confirm_broadcast_"):
            await self.execute_broadcast(update, context)
        
        elif data == "cancel_broadcast":
            await query.edit_message_text("❌ Broadcast cancelled.")
        
        elif data == "refresh_stats":
            await self.show_stats(update, context)
        
        elif data == "admin_backup":
            await self.create_backup(update, context)

    async def execute_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute broadcast to all users"""
        query = update.callback_query
        await query.answer()
        
        broadcast_data = context.user_data.get('broadcast_data')
        if not broadcast_data:
            await query.edit_message_text("❌ Broadcast data not found.")
            return
        
        users = broadcast_data['users']
        total_users = len(users)
        broadcast_type = broadcast_data['type']
        
        # Update message to show progress
        progress_msg = await query.edit_message_text(
            f"📢 Broadcasting to {total_users} users...\n"
            f"✅ Sent: 0 | ❌ Failed: 0\n"
            f"🔄 Progress: 0%"
        )
        
        sent = 0
        failed = 0
        failed_users = []
        
        # Send broadcast
        for i, user_id in enumerate(users, 1):
            try:
                if broadcast_type == 'text':
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=broadcast_data['message'],
                        parse_mode=ParseMode.HTML
                    )
                elif broadcast_type == 'reply':
                    # Forward the replied message
                    await broadcast_data['message_object'].forward(chat_id=user_id)
                
                sent += 1
                
                # Update progress every 20 users or 5%
                if i % 20 == 0 or i == total_users:
                    progress = (i / total_users) * 100
                    await progress_msg.edit_text(
                        f"📢 Broadcasting to {total_users} users...\n"
                        f"✅ Sent: {sent} | ❌ Failed: {failed}\n"
                        f"🔄 Progress: {progress:.1f}%"
                    )
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed += 1
                failed_users.append(str(user_id))
        
        # Broadcast complete
        complete_text = f"""
✅ <b>BROADCAST COMPLETE</b>

📊 <b>Statistics:</b>
├ Total Users: {total_users}
├ ✅ Success: {sent}
├ ❌ Failed: {failed}
└ 📈 Success Rate: {(sent/total_users*100):.1f}%

🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        if failed_users:
            complete_text += f"<b>Failed Users ({min(10, len(failed_users))} shown):</b>\n"
            for user_id in failed_users[:10]:
                complete_text += f"├ <code>{user_id}</code>\n"
            
            if len(failed_users) > 10:
                complete_text += f"└ ... and {len(failed_users) - 10} more\n"
        
        complete_text += f"\n🏆 <b>Developer</b>: {config.UI['developer']}\n"
        complete_text += f"⚡ <b>Powered By</b>: {config.UI['powered_by']}"
        
        await progress_msg.edit_text(complete_text, parse_mode=ParseMode.HTML)
        
        # Store broadcast stats
        self.broadcast_stats[datetime.now()] = {
            'total': total_users,
            'sent': sent,
            'failed': failed,
            'admin': broadcast_data['admin_id'],
            'type': broadcast_type
        }
        
        # Clean up
        if 'broadcast_data' in context.user_data:
            del context.user_data['broadcast_data']
