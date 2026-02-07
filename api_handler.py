import aiohttp
import asyncio
import json
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time
from .config import config
from .database import db

class APIResponse:
    """Standardized API Response"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None, 
                 response_time: float = None, cached: bool = False):
        self.success = success
        self.data = data
        self.error = error
        self.response_time = response_time
        self.cached = cached
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'response_time': self.response_time,
            'cached': self.cached,
            'timestamp': self.timestamp.isoformat(),
            'developer': config.UI['developer'],
            'powered_by': config.UI['powered_by']
        }

class APIHandler:
    """Advanced API Handler with Caching and Retry Logic"""
    
    def __init__(self):
        self.session = None
        self.cache = {}
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0
        }
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def generate_cache_key(self, api_name: str, query: str) -> str:
        """Generate cache key"""
        key_str = f"{api_name}:{query}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def make_request(self, api_name: str, query: str, 
                          retries: int = 3, use_cache: bool = True) -> APIResponse:
        """Make API request with caching and retry logic"""
        
        # Check cache first
        cache_key = self.generate_cache_key(api_name, query)
        
        if use_cache and cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() < cached_data['expires']:
                return APIResponse(
                    success=True,
                    data=cached_data['data'],
                    response_time=0,
                    cached=True
                )
            else:
                # Remove expired cache
                del self.cache[cache_key]
        
        # Get API configuration
        api_config = config.APIS.get(api_name)
        if not api_config:
            return APIResponse(success=False, error=f"API '{api_name}' not configured")
        
        # Build URL
        url = f"{api_config.url}{query}"
        
        # Make request with retries
        start_time = time.time()
        last_error = None
        
        for attempt in range(retries):
            try:
                session = await self.get_session()
                
                async with session.get(url, timeout=api_config.timeout) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        
                        if 'application/json' in content_type:
                            data = await response.json()
                        elif 'text/html' in content_type:
                            text = await response.text()
                            # Try to parse as JSON
                            try:
                                data = json.loads(text)
                            except:
                                data = {'raw_response': text}
                        else:
                            text = await response.text()
                            data = {'raw_response': text}
                        
                        # Cache the response
                        self.cache[cache_key] = {
                            'data': data,
                            'expires': datetime.now() + timedelta(seconds=config.CACHE_TTL['api_responses'])
                        }
                        
                        # Update stats
                        self.stats['total_requests'] += 1
                        self.stats['successful_requests'] += 1
                        self.stats['total_response_time'] += response_time
                        
                        return APIResponse(
                            success=True,
                            data=data,
                            response_time=response_time,
                            cached=False
                        )
                    else:
                        last_error = f"HTTP {response.status}: {await response.text()}"
                        
            except asyncio.TimeoutError:
                last_error = f"Timeout after {api_config.timeout}s"
            except aiohttp.ClientError as e:
                last_error = f"Client error: {str(e)}"
            except json.JSONDecodeError as e:
                last_error = f"JSON decode error: {str(e)}"
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
            
            # Wait before retry (exponential backoff)
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        # Update stats for failed request
        self.stats['total_requests'] += 1
        self.stats['failed_requests'] += 1
        
        return APIResponse(
            success=False,
            error=last_error,
            response_time=time.time() - start_time
        )
    
    def format_response(self, api_response: APIResponse, command: str, query: str) -> Dict:
        """Format API response for output"""
        if not api_response.success:
            return {
                'error': True,
                'message': api_response.error,
                'command': command,
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'developer': config.UI['developer'],
                'powered_by': config.UI['powered_by']
            }
        
        # Add metadata to response
        response_data = api_response.data
        
        if isinstance(response_data, dict):
            # Ensure required fields
            response_data.setdefault('success', True)
            response_data.setdefault('query', query)
            response_data.setdefault('command', command)
            response_data.setdefault('timestamp', datetime.now().isoformat())
            response_data.setdefault('response_time_ms', round(api_response.response_time * 1000, 2))
            response_data.setdefault('cached', api_response.cached)
            response_data.setdefault('developer', config.UI['developer'])
            response_data.setdefault('powered_by', config.UI['powered_by'])
            
            # Add formatting hints for Telegram
            response_data['_format'] = {
                'type': 'json',
                'pretty': True,
                'max_length': 4000,
                'truncate_long': True
            }
        
        return response_data
    
    def format_for_telegram(self, data: Dict, max_length: int = 4000) -> Dict:
        """Format data for Telegram message"""
        if not isinstance(data, dict):
            return {'text': str(data), 'parse_mode': 'HTML'}
        
        # Create pretty JSON
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            
            # Truncate if too long
            if len(json_str) > max_length:
                # Save to file instead
                return {
                    'type': 'document',
                    'caption': f"📁 <b>{data.get('command', 'Data')} Lookup Result</b>\n\n"
                              f"🔍 Query: <code>{data.get('query', 'N/A')}</code>\n\n"
                              f"🏆 <b>Developer</b>: {config.UI['developer']}\n"
                              f"⚡ <b>Powered By</b>: {config.UI['powered_by']}\n"
                              f"📊 Response Time: {data.get('response_time_ms', 0)}ms",
                    'parse_mode': 'HTML',
                    'data': json_str.encode()
                }
            
            # Format as code block
            formatted = f"<pre><code class=\"language-json\">{html.escape(json_str)}</code></pre>"
            
            # Add footer
            formatted += f"\n\n🏆 <b>Developer</b>: {config.UI['developer']}\n"
            formatted += f"⚡ <b>Powered By</b>: {config.UI['powered_by']}\n"
            
            if data.get('response_time_ms'):
                formatted += f"⏱ <b>Response Time</b>: {data['response_time_ms']}ms\n"
            
            if data.get('cached'):
                formatted += f"💾 <b>Cached Response</b>\n"
            
            return {
                'text': formatted,
                'parse_mode': 'HTML'
            }
            
        except Exception as e:
            return {
                'text': f"❌ Error formatting response: {str(e)}\n\n"
                       f"🏆 <b>Developer</b>: {config.UI['developer']}\n"
                       f"⚡ <b>Powered By</b>: {config.UI['powered_by']}",
                'parse_mode': 'HTML'
            }
    
    async def process_lookup(self, user_id: int, command: str, query: str) -> Dict:
        """Complete lookup processing"""
        
        # Check rate limit
        if not db.check_rate_limit(user_id, command, config.RATE_LIMIT['user_per_minute']):
            return {
                'error': True,
                'message': f'Rate limit exceeded. Please wait before using /{command} again.',
                'developer': config.UI['developer'],
                'powered_by': config.UI['powered_by']
            }
        
        # Make API request
        start_time = time.time()
        api_response = await self.make_request(command, query)
        response_time = time.time() - start_time
        
        # Format response
        formatted_data = self.format_response(api_response, command, query)
        
        # Record in database
        db.record_lookup(
            user_id=user_id,
            command=command,
            query=query,
            result=formatted_data,
            status='success' if api_response.success else 'error',
            error=api_response.error if not api_response.success else None,
            response_time=response_time
        )
        
        return formatted_data
    
    def get_stats(self) -> Dict:
        """Get API handler statistics"""
        avg_response_time = 0
        if self.stats['successful_requests'] > 0:
            avg_response_time = self.stats['total_response_time'] / self.stats['successful_requests']
        
        return {
            'total_requests': self.stats['total_requests'],
            'successful_requests': self.stats['successful_requests'],
            'failed_requests': self.stats['failed_requests'],
            'success_rate': (self.stats['successful_requests'] / self.stats['total_requests'] * 100) 
                           if self.stats['total_requests'] > 0 else 0,
            'avg_response_time_seconds': round(avg_response_time, 3),
            'cache_size': len(self.cache),
            'developer': config.UI['developer'],
            'powered_by': config.UI['powered_by']
        }

# Global API handler instance
api_handler = APIHandler()
