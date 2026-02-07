import os
from typing import List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class APIConfig:
    """API Configuration"""
    url: str
    method: str = "GET"
    headers: Dict = None
    timeout: int = 10
    retry: int = 3

@dataclass
class LogChannel:
    """Log Channel Configuration"""
    name: str
    channel_id: int
    log_type: str

class BotConfig:
    """Bot Configuration Manager"""
    
    def __init__(self):
        # Core Bot Settings
        self.BOT_TOKEN = os.getenv('BOT_TOKEN')
        self.OWNER_ID = int(os.getenv('OWNER_ID', '8104850843'))
        self.ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '8104850843,5987905091').split(',') if id.strip()]
        
        # Channels Configuration
        self.FORCE_JOIN_CHANNELS = [int(ch.strip()) for ch in os.getenv('FORCE_JOIN_CHANNELS', '-1003090922367,-1003698567122').split(',') if ch.strip()]
        self.FORCE_JOIN_LINKS = [link.strip() for link in os.getenv('FORCE_JOIN_LINKS', 'https://t.me/all_data_here,https://t.me/osint_lookup').split(',') if link.strip()]
        self.REDIRECT_BOT = os.getenv('REDIRECT_BOT', '@Dark_osintlookupBot')
        
        # API Configurations
        self.APIS = {
            'num': APIConfig(url=os.getenv('API_NUM', 'https://openosintx.vippanel.in/num.php?key=OpenOSINTX-FREE&number=')),
            'tg2num': APIConfig(url=os.getenv('API_TG2NUM', 'https://openosintx.vippanel.in/tginfo.php?key=OpenOSINTX-FREE&number=')),
            'tginfo': APIConfig(url=os.getenv('API_TG_INFO', 'https://openosintx.vippanel.in/tgusrinfo.php?key=OpenOSINTX-FREE&user=')),
            'vehicle': APIConfig(url=os.getenv('API_VEHICLE', 'https://vehicle-info-aco-api.vercel.app/info?vehicle=')),
            'email': APIConfig(url=os.getenv('API_EMAIL', 'https://abbas-apis.vercel.app/api/email?mail=')),
            'ifsc': APIConfig(url=os.getenv('API_IFSC', 'https://abbas-apis.vercel.app/api/ifsc?ifsc=')),
            'pincode': APIConfig(url=os.getenv('API_PINCODE', 'https://api.postalpincode.in/pincode/')),
            'insta': APIConfig(url=os.getenv('API_INSTAGRAM', 'https://mkhossain.alwaysdata.net/instanum.php?username=')),
            'github': APIConfig(url=os.getenv('API_GITHUB', 'https://abbas-apis.vercel.app/api/github?username=')),
            'gst': APIConfig(url=os.getenv('API_GST', 'https://veerulookup.onrender.com/search_gst?gst=')),
            'pakistan': APIConfig(url=os.getenv('API_PAKISTAN', 'https://abbas-apis.vercel.app/api/pakistan?number=')),
            'ip': APIConfig(url=os.getenv('API_IP', 'https://abbas-apis.vercel.app/api/ip?ip=')),
            'ffinfo': APIConfig(url=os.getenv('API_FF_INFO', 'https://abbas-apis.vercel.app/api/ff-info?uid=')),
            'ffban': APIConfig(url=os.getenv('API_FF_BAN', 'https://abbas-apis.vercel.app/api/ff-ban?uid=')),
        }
        
        # Log Channels Configuration
        self.LOG_CHANNELS = {
            'num': LogChannel(name='Number Lookup', channel_id=int(os.getenv('LOG_CHANNEL_NUM', '-1003482423742')), log_type='NUMBER'),
            'ifsc': LogChannel(name='IFSC Lookup', channel_id=int(os.getenv('LOG_CHANNEL_IFSC', '-1003624886596')), log_type='BANKING'),
            'email': LogChannel(name='Email Lookup', channel_id=int(os.getenv('LOG_CHANNEL_EMAIL', '-1003431549612')), log_type='EMAIL'),
            'gst': LogChannel(name='GST Lookup', channel_id=int(os.getenv('LOG_CHANNEL_GST', '-1003634866992')), log_type='BUSINESS'),
            'tg2num': LogChannel(name='Telegram to Number', channel_id=int(os.getenv('LOG_CHANNEL_TG2NUM', '-1003643170105')), log_type='TELEGRAM'),
            'tginfo': LogChannel(name='Telegram Info', channel_id=int(os.getenv('LOG_CHANNEL_TGINFO', '-1003642820243')), log_type='TELEGRAM'),
            'vehicle': LogChannel(name='Vehicle Info', channel_id=int(os.getenv('LOG_CHANNEL_VEHICLE', '-1003237155636')), log_type='VEHICLE'),
            'pincode': LogChannel(name='Pincode Lookup', channel_id=int(os.getenv('LOG_CHANNEL_PINCODE', '-1003677285823')), log_type='LOCATION'),
            'insta': LogChannel(name='Instagram Lookup', channel_id=int(os.getenv('LOG_CHANNEL_INSTAGRAM', '-1003498414978')), log_type='SOCIAL'),
            'github': LogChannel(name='GitHub Lookup', channel_id=int(os.getenv('LOG_CHANNEL_GITHUB', '-1003576017442')), log_type='DEVELOPER'),
            'pakistan': LogChannel(name='Pakistan Number', channel_id=int(os.getenv('LOG_CHANNEL_PAKISTAN', '-1003663672738')), log_type='NUMBER'),
            'ip': LogChannel(name='IP Lookup', channel_id=int(os.getenv('LOG_CHANNEL_IP', '-1003665811220')), log_type='NETWORK'),
            'ffinfo': LogChannel(name='Free Fire Info', channel_id=int(os.getenv('LOG_CHANNEL_FF_INFO', '-1003588577282')), log_type='GAMING'),
            'ffban': LogChannel(name='Free Fire Ban', channel_id=int(os.getenv('LOG_CHANNEL_FF_BAN', '-1003521974255')), log_type='GAMING'),
        }
        
        # Database Configuration
        self.DB_CONFIG = {
            'sqlite_path': 'bot_database.db',
            'backup_dir': 'backups/',
            'auto_backup_hours': 24,
            'max_backup_files': 30
        }
        
        # Rate Limiting
        self.RATE_LIMIT = {
            'user_per_minute': 10,
            'global_per_second': 5,
            'admin_bypass': True
        }
        
        # Cache Configuration
        self.CACHE_TTL = {
            'api_responses': 300,  # 5 minutes
            'user_data': 600,      # 10 minutes
            'channel_status': 300  # 5 minutes
        }
        
        # UI Configuration
        self.UI = {
            'developer': '@Nullprotocol_X',
            'powered_by': 'NULL PROTOCOL',
            'theme_color': '#5865F2',
            'footer_text': '🔐 Secured by NULL PROTOCOL | 🚀 Powered by Advanced AI',
            'show_watermark': True
        }
    
    def validate(self) -> bool:
        """Validate configuration"""
        required = ['BOT_TOKEN']
        for var in required:
            if not getattr(self, var, None):
                return False
        return True

# Global configuration instance
config = BotConfig()
