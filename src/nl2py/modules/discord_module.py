"""
Discord Module for NL2Py
Provides comprehensive Discord integration via webhooks and bot API.

Module Type: (discord)
Primary Use Cases: Notifications, alerts, chat integration, bot automation

Author: NL2Py Development Team
Version: 1.0.0
"""

import os
import json
import threading
from typing import Dict, Any, List, Optional, Union
import requests
from .module_base import NL2PyModuleBase


class DiscordModule(NL2PyModuleBase):
    """
    Discord module for sending messages, embeds, and managing webhooks.

    Features:
    - Webhook Integration: Send messages via Discord webhooks
    - Rich Embeds: Create formatted embed messages
    - File Attachments: Send files and images
    - Message Formatting: Markdown support, mentions, emojis
    - Webhook Management: Create, edit, delete webhooks
    - Rate Limiting: Automatic retry with exponential backoff
    - Error Handling: Comprehensive error messages

    Configuration (nl2py.conf):
        [discord]
        WEBHOOK_URL = https://discord.com/api/webhooks/...
        BOT_TOKEN =
        DEFAULT_USERNAME = NL2Py Bot
        DEFAULT_AVATAR_URL =
        RATE_LIMIT_RETRY = true
        MAX_RETRIES = 3
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Discord module."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    # Configuration
                    self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
                    self.bot_token = os.getenv('DISCORD_BOT_TOKEN', '')
                    self.default_username = os.getenv('DISCORD_DEFAULT_USERNAME', 'NL2Py Bot')
                    self.default_avatar_url = os.getenv('DISCORD_DEFAULT_AVATAR_URL', '')
                    self.rate_limit_retry = os.getenv('DISCORD_RATE_LIMIT_RETRY', 'true').lower() == 'true'
                    self.max_retries = int(os.getenv('DISCORD_MAX_RETRIES', '3'))

                    # API base URL
                    self.api_base = 'https://discord.com/api/v10'

                    self._initialized = True

    def send_message(self, content: str, webhook_url: Optional[str] = None,
                    username: Optional[str] = None, avatar_url: Optional[str] = None,
                    tts: bool = False) -> Dict[str, Any]:
        """
        Send a simple text message via webhook.

        Args:
            content: Message content (up to 2000 characters)
            webhook_url: Optional webhook URL (uses default if not provided)
            username: Optional custom username
            avatar_url: Optional custom avatar URL
            tts: Text-to-speech flag

        Returns:
            Response dictionary with status and message ID
        """
        url = webhook_url or self.webhook_url
        if not url:
            raise ValueError("No webhook URL provided")

        payload = {
            'content': content[:2000],  # Discord limit
            'tts': tts
        }

        if username:
            payload['username'] = username
        elif self.default_username:
            payload['username'] = self.default_username

        if avatar_url:
            payload['avatar_url'] = avatar_url
        elif self.default_avatar_url:
            payload['avatar_url'] = self.default_avatar_url

        response = self._make_request('POST', url, json=payload)
        return response

    def send_embed(self, embed: Dict[str, Any], webhook_url: Optional[str] = None,
                   username: Optional[str] = None, avatar_url: Optional[str] = None,
                   content: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an embed message via webhook.

        Args:
            embed: Embed dictionary (title, description, color, fields, etc.)
            webhook_url: Optional webhook URL
            username: Optional custom username
            avatar_url: Optional custom avatar URL
            content: Optional message content alongside embed

        Returns:
            Response dictionary
        """
        url = webhook_url or self.webhook_url
        if not url:
            raise ValueError("No webhook URL provided")

        payload = {
            'embeds': [embed]
        }

        if content:
            payload['content'] = content[:2000]

        if username:
            payload['username'] = username
        elif self.default_username:
            payload['username'] = self.default_username

        if avatar_url:
            payload['avatar_url'] = avatar_url
        elif self.default_avatar_url:
            payload['avatar_url'] = self.default_avatar_url

        response = self._make_request('POST', url, json=payload)
        return response

    def create_embed(self, title: Optional[str] = None, description: Optional[str] = None,
                    color: Optional[int] = None, url: Optional[str] = None,
                    timestamp: Optional[str] = None, footer: Optional[Dict[str, str]] = None,
                    image: Optional[str] = None, thumbnail: Optional[str] = None,
                    author: Optional[Dict[str, str]] = None,
                    fields: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Create an embed object.

        Args:
            title: Embed title
            description: Embed description
            color: Embed color (integer, e.g., 0xFF0000 for red)
            url: URL for the title
            timestamp: ISO8601 timestamp
            footer: Footer dict with 'text' and optional 'icon_url'
            image: Image URL
            thumbnail: Thumbnail URL
            author: Author dict with 'name' and optional 'url', 'icon_url'
            fields: List of field dicts with 'name', 'value', optional 'inline'

        Returns:
            Embed dictionary
        """
        embed = {}

        if title:
            embed['title'] = title[:256]  # Discord limit
        if description:
            embed['description'] = description[:4096]  # Discord limit
        if color is not None:
            embed['color'] = color
        if url:
            embed['url'] = url
        if timestamp:
            embed['timestamp'] = timestamp

        if footer:
            embed['footer'] = {
                'text': footer.get('text', '')[:2048]
            }
            if 'icon_url' in footer:
                embed['footer']['icon_url'] = footer['icon_url']

        if image:
            embed['image'] = {'url': image}
        if thumbnail:
            embed['thumbnail'] = {'url': thumbnail}

        if author:
            embed['author'] = {
                'name': author.get('name', '')[:256]
            }
            if 'url' in author:
                embed['author']['url'] = author['url']
            if 'icon_url' in author:
                embed['author']['icon_url'] = author['icon_url']

        if fields:
            embed['fields'] = []
            for field in fields[:25]:  # Discord limit: 25 fields
                embed['fields'].append({
                    'name': field.get('name', '')[:256],
                    'value': field.get('value', '')[:1024],
                    'inline': field.get('inline', False)
                })

        return embed

    def send_file(self, file_path: str, filename: Optional[str] = None,
                 content: Optional[str] = None, webhook_url: Optional[str] = None,
                 username: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a file via webhook.

        Args:
            file_path: Path to the file to send
            filename: Optional custom filename
            content: Optional message content
            webhook_url: Optional webhook URL
            username: Optional custom username

        Returns:
            Response dictionary
        """
        url = webhook_url or self.webhook_url
        if not url:
            raise ValueError("No webhook URL provided")

        # Prepare multipart form data
        files = {
            'file': (filename or os.path.basename(file_path), open(file_path, 'rb'))
        }

        payload = {}
        if content:
            payload['content'] = content[:2000]
        if username:
            payload['username'] = username
        elif self.default_username:
            payload['username'] = self.default_username

        # Send as multipart/form-data
        response = self._make_request('POST', url, data=payload, files=files)

        # Close file
        files['file'][1].close()

        return response

    def edit_webhook_message(self, message_id: str, content: Optional[str] = None,
                            embeds: Optional[List[Dict[str, Any]]] = None,
                            webhook_url: Optional[str] = None,
                            webhook_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Edit a webhook message.

        Args:
            message_id: ID of the message to edit
            content: New message content
            embeds: New embeds
            webhook_url: Webhook URL
            webhook_token: Webhook token (extracted from URL if not provided)

        Returns:
            Response dictionary
        """
        url = webhook_url or self.webhook_url
        if not url:
            raise ValueError("No webhook URL provided")

        # Extract webhook token from URL if needed
        if not webhook_token:
            webhook_token = url.split('/')[-1]

        # Build edit URL
        webhook_id = url.split('/')[-2]
        edit_url = f"{self.api_base}/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}"

        payload = {}
        if content is not None:
            payload['content'] = content[:2000]
        if embeds is not None:
            payload['embeds'] = embeds

        response = self._make_request('PATCH', edit_url, json=payload)
        return response

    def delete_webhook_message(self, message_id: str, webhook_url: Optional[str] = None,
                               webhook_token: Optional[str] = None) -> bool:
        """
        Delete a webhook message.

        Args:
            message_id: ID of the message to delete
            webhook_url: Webhook URL
            webhook_token: Webhook token

        Returns:
            True if successful
        """
        url = webhook_url or self.webhook_url
        if not url:
            raise ValueError("No webhook URL provided")

        if not webhook_token:
            webhook_token = url.split('/')[-1]

        webhook_id = url.split('/')[-2]
        delete_url = f"{self.api_base}/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}"

        self._make_request('DELETE', delete_url)
        return True

    def send_notification(self, title: str, message: str, color: int = 0x00FF00,
                         level: str = 'info', webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a formatted notification embed.

        Args:
            title: Notification title
            message: Notification message
            color: Embed color (default: green)
            level: Notification level (info, warning, error, success)
            webhook_url: Optional webhook URL

        Returns:
            Response dictionary
        """
        # Color mapping
        colors = {
            'info': 0x3498DB,      # Blue
            'success': 0x2ECC71,   # Green
            'warning': 0xF39C12,   # Orange
            'error': 0xE74C3C      # Red
        }

        embed_color = colors.get(level.lower(), color)

        # Emoji mapping
        emojis = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }

        emoji = emojis.get(level.lower(), '📢')

        embed = self.create_embed(
            title=f"{emoji} {title}",
            description=message,
            color=embed_color,
            timestamp=self._get_iso_timestamp()
        )

        return self.send_embed(embed, webhook_url=webhook_url)

    def send_alert(self, message: str, webhook_url: Optional[str] = None,
                  mention_everyone: bool = False, mention_users: Optional[List[str]] = None,
                  mention_roles: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send an alert with optional mentions.

        Args:
            message: Alert message
            webhook_url: Optional webhook URL
            mention_everyone: Mention @everyone
            mention_users: List of user IDs to mention
            mention_roles: List of role IDs to mention

        Returns:
            Response dictionary
        """
        content = message

        # Add mentions
        if mention_everyone:
            content = "@everyone " + content
        if mention_users:
            for user_id in mention_users:
                content = f"<@{user_id}> " + content
        if mention_roles:
            for role_id in mention_roles:
                content = f"<@&{role_id}> " + content

        embed = self.create_embed(
            title="🚨 Alert",
            description=message,
            color=0xFF0000,  # Red
            timestamp=self._get_iso_timestamp()
        )

        return self.send_embed(embed, webhook_url=webhook_url, content=content if mention_everyone or mention_users or mention_roles else None)

    def send_status_update(self, service: str, status: str, details: Optional[str] = None,
                          webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a service status update.

        Args:
            service: Service name
            status: Status (online, degraded, offline)
            details: Optional status details
            webhook_url: Optional webhook URL

        Returns:
            Response dictionary
        """
        # Status colors and emojis
        status_info = {
            'online': {'color': 0x2ECC71, 'emoji': '🟢', 'text': 'Online'},
            'degraded': {'color': 0xF39C12, 'emoji': '🟡', 'text': 'Degraded'},
            'offline': {'color': 0xE74C3C, 'emoji': '🔴', 'text': 'Offline'}
        }

        info = status_info.get(status.lower(), {'color': 0x95A5A6, 'emoji': '⚪', 'text': status.title()})

        fields = [
            {'name': 'Service', 'value': service, 'inline': True},
            {'name': 'Status', 'value': f"{info['emoji']} {info['text']}", 'inline': True}
        ]

        if details:
            fields.append({'name': 'Details', 'value': details, 'inline': False})

        embed = self.create_embed(
            title="Service Status Update",
            color=info['color'],
            fields=fields,
            timestamp=self._get_iso_timestamp()
        )

        return self.send_embed(embed, webhook_url=webhook_url)

    def send_log(self, level: str, message: str, source: Optional[str] = None,
                webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a log message.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            source: Optional log source
            webhook_url: Optional webhook URL

        Returns:
            Response dictionary
        """
        level_info = {
            'DEBUG': {'color': 0x95A5A6, 'emoji': '🔍'},
            'INFO': {'color': 0x3498DB, 'emoji': 'ℹ️'},
            'WARNING': {'color': 0xF39C12, 'emoji': '⚠️'},
            'ERROR': {'color': 0xE74C3C, 'emoji': '❌'},
            'CRITICAL': {'color': 0x992D22, 'emoji': '🔥'}
        }

        info = level_info.get(level.upper(), {'color': 0x95A5A6, 'emoji': '📝'})

        fields = [
            {'name': 'Level', 'value': f"{info['emoji']} {level.upper()}", 'inline': True}
        ]

        if source:
            fields.append({'name': 'Source', 'value': source, 'inline': True})

        fields.append({'name': 'Message', 'value': message, 'inline': False})

        embed = self.create_embed(
            title="Log Entry",
            color=info['color'],
            fields=fields,
            timestamp=self._get_iso_timestamp()
        )

        return self.send_embed(embed, webhook_url=webhook_url)

    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments

        Returns:
            Response dictionary
        """
        import time

        retries = 0
        while retries <= self.max_retries:
            try:
                response = requests.request(method, url, **kwargs)

                # Handle rate limiting
                if response.status_code == 429 and self.rate_limit_retry:
                    retry_after = int(response.headers.get('Retry-After', 1))
                    time.sleep(retry_after)
                    retries += 1
                    continue

                # Raise for other errors
                response.raise_for_status()

                # Return response data
                if response.status_code == 204:
                    return {'status': 'success'}

                return response.json() if response.content else {'status': 'success'}

            except requests.exceptions.RequestException as e:
                if retries >= self.max_retries:
                    raise Exception(f"Discord API request failed: {str(e)}")
                retries += 1
                time.sleep(2 ** retries)  # Exponential backoff

        raise Exception("Max retries exceeded")

    def _get_iso_timestamp(self) -> str:
        """Get current timestamp in ISO8601 format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    @classmethod
    def get_metadata(cls):
        """Get module metadata."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Discord",
            task_type="discord",
            description="Discord integration via webhooks for notifications, alerts, and team communication",
            version="1.0.0",
            keywords=["discord", "webhook", "notification", "alert", "embed", "chat", "message"],
            dependencies=["requests>=2.31.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes."""
        return [
            "Webhook URL required - get from Discord Server Settings → Integrations → Webhooks",
            "Use send_message() for simple text messages (2000 chars max)",
            "Use send_embed() for rich formatted messages with colors, fields, images",
            "Use send_notification() for pre-formatted info/success/warning/error messages",
            "Use send_alert() for urgent messages with optional @mentions",
            "Use send_status_update() for service monitoring (online/degraded/offline)",
            "Use send_log() for structured log messages with severity levels",
            "Embed limits: title 256 chars, description 4096 chars, 25 fields max",
            "Colors specified as hex integers (e.g., 0x2ECC71 for green, 0xE74C3C for red)",
            "Rate limit: 30 requests/minute per webhook - module handles retries automatically",
            "Markdown formatting supported: **bold**, *italic*, `code`, ```code block```",
            "Module uses singleton pattern - one instance shared across all operations"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about module methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="send_message",
                description="Send a simple text message to Discord",
                parameters={
                    "content": "Message text (max 2000 characters)",
                    "webhook_url": "Optional webhook URL (uses default if not provided)",
                    "username": "Optional custom username for the message",
                    "avatar_url": "Optional custom avatar URL",
                    "tts": "Text-to-speech flag (default: False)"
                },
                returns="Dict with message ID and status",
                examples=[
                    {"text": "Send message {{message}} to Discord", "code": "send_message(content='{{message}}')"},
                    {"text": "Send message {{message}} with username {{bot_name}}", "code": "send_message(content='{{message}}', username='{{bot_name}}')"}
                ]
            ),
            MethodInfo(
                name="send_embed",
                description="Send a rich embed message with formatting",
                parameters={
                    "embed": "Embed dictionary (use create_embed() to build)",
                    "webhook_url": "Optional webhook URL",
                    "username": "Optional custom username",
                    "content": "Optional text content alongside embed"
                },
                returns="Dict with message ID and status",
                examples=[
                    {"text": "Send rich embed {{embed_object}}", "code": "send_embed(embed={{embed_object}})"},
                    {"text": "Send embed {{embed_object}} with content {{message}}", "code": "send_embed(embed={{embed_object}}, content='{{message}}')"}
                ]
            ),
            MethodInfo(
                name="create_embed",
                description="Create an embed object with title, description, fields, colors",
                parameters={
                    "title": "Embed title (max 256 chars)",
                    "description": "Embed description (max 4096 chars)",
                    "color": "Color as hex integer (e.g., 0xFF0000)",
                    "fields": "List of field dicts with name, value, inline",
                    "footer": "Footer dict with text and optional icon_url",
                    "image": "Image URL for full-size image",
                    "thumbnail": "Thumbnail URL",
                    "author": "Author dict with name, url, icon_url",
                    "timestamp": "ISO8601 timestamp"
                },
                returns="Embed dictionary ready to send",
                examples=[
                    {"text": "Create embed with title {{title}} and description {{description}} and color {{color_hex}}", "code": "create_embed(title='{{title}}', description='{{description}}', color={{color_hex}})"},
                    {"text": "Create embed with title {{title}} and fields {{fields_list}}", "code": "create_embed(title='{{title}}', fields={{fields_list}})"},
                    {"text": "Create embed with title {{title}}, description {{description}}, image {{image_url}}, and footer {{footer_dict}}", "code": "create_embed(title='{{title}}', description='{{description}}', image='{{image_url}}', footer={{footer_dict}})"}
                ]
            ),
            MethodInfo(
                name="send_notification",
                description="Send a pre-formatted notification (info, success, warning, error)",
                parameters={
                    "title": "Notification title",
                    "message": "Notification message",
                    "level": "Severity level: info, success, warning, error",
                    "color": "Optional custom color (overrides level default)",
                    "webhook_url": "Optional webhook URL"
                },
                returns="Dict with message ID and status",
                examples=[
                    {"text": "Send success notification with title {{title}} and message {{message}}", "code": "send_notification(title='{{title}}', message='{{message}}', level='success')"},
                    {"text": "Send warning notification with title {{title}} and message {{message}}", "code": "send_notification(title='{{title}}', message='{{message}}', level='warning')"},
                    {"text": "Send error notification with title {{title}}, message {{message}}, and color {{color_hex}}", "code": "send_notification(title='{{title}}', message='{{message}}', level='error', color={{color_hex}})"}
                ]
            ),
            MethodInfo(
                name="send_alert",
                description="Send an urgent alert with optional mentions",
                parameters={
                    "message": "Alert message",
                    "webhook_url": "Optional webhook URL",
                    "mention_everyone": "Mention @everyone (default: False)",
                    "mention_users": "List of user IDs to mention",
                    "mention_roles": "List of role IDs to mention"
                },
                returns="Dict with message ID and status",
                examples=[
                    {"text": "Send alert {{alert_message}}", "code": "send_alert(message='{{alert_message}}')"},
                    {"text": "Send alert {{alert_message}} mentioning everyone", "code": "send_alert(message='{{alert_message}}', mention_everyone=True)"},
                    {"text": "Send alert {{alert_message}} mentioning users {{user_ids_list}}", "code": "send_alert(message='{{alert_message}}', mention_users={{user_ids_list}})"}
                ]
            ),
            MethodInfo(
                name="send_status_update",
                description="Send a service status update (online, degraded, offline)",
                parameters={
                    "service": "Service name",
                    "status": "Status: online (green), degraded (orange), offline (red)",
                    "details": "Optional status details",
                    "webhook_url": "Optional webhook URL"
                },
                returns="Dict with message ID and status",
                examples=[
                    {"text": "Send status update for service {{service_name}} with status online", "code": "send_status_update(service='{{service_name}}', status='online')"},
                    {"text": "Send status update for service {{service_name}} with status degraded and details {{status_details}}", "code": "send_status_update(service='{{service_name}}', status='degraded', details='{{status_details}}')"},
                    {"text": "Send status update for service {{service_name}} with status offline and details {{status_details}}", "code": "send_status_update(service='{{service_name}}', status='offline', details='{{status_details}}')"}
                ]
            ),
            MethodInfo(
                name="send_log",
                description="Send a structured log message with severity level",
                parameters={
                    "level": "Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
                    "message": "Log message",
                    "source": "Optional source/module name",
                    "webhook_url": "Optional webhook URL"
                },
                returns="Dict with message ID and status",
                examples=[
                    {"text": "Send ERROR log {{log_message}} from source {{source_module}}", "code": "send_log(level='ERROR', message='{{log_message}}', source='{{source_module}}')"},
                    {"text": "Send INFO log {{log_message}} from source {{source_module}}", "code": "send_log(level='INFO', message='{{log_message}}', source='{{source_module}}')"},
                    {"text": "Send CRITICAL log {{log_message}}", "code": "send_log(level='CRITICAL', message='{{log_message}}')"}
                ]
            ),
            MethodInfo(
                name="send_file",
                description="Send a file attachment",
                parameters={
                    "file_path": "Path to file to send",
                    "filename": "Optional custom filename",
                    "content": "Optional message content",
                    "webhook_url": "Optional webhook URL"
                },
                returns="Dict with message ID and status",
                examples=[
                    {"text": "Send file {{file_path}} with message {{message}}", "code": "send_file(file_path='{{file_path}}', content='{{message}}')"},
                    {"text": "Send file {{file_path}} with filename {{custom_filename}}", "code": "send_file(file_path='{{file_path}}', filename='{{custom_filename}}')"},
                    {"text": "Send file {{file_path}}", "code": "send_file(file_path='{{file_path}}')"}
                ]
            ),
            MethodInfo(
                name="edit_webhook_message",
                description="Edit a previously sent webhook message",
                parameters={
                    "message_id": "ID of the message to edit",
                    "content": "New message content (optional)",
                    "embeds": "New embeds list (optional)",
                    "webhook_url": "Webhook URL (optional if using default)",
                    "webhook_token": "Webhook token (optional if using URL)"
                },
                returns="Dict with edited message data",
                examples=[
                    {"text": "Edit message {{message_id}} with new content {{new_content}}", "code": "edit_webhook_message(message_id='{{message_id}}', content='{{new_content}}')"},
                    {"text": "Edit message {{message_id}} with embeds {{new_embeds_list}}", "code": "edit_webhook_message(message_id='{{message_id}}', embeds={{new_embeds_list}})"},
                    {"text": "Edit message {{message_id}} with content {{new_content}} and embeds {{new_embeds_list}}", "code": "edit_webhook_message(message_id='{{message_id}}', content='{{new_content}}', embeds={{new_embeds_list}})"}
                ]
            ),
            MethodInfo(
                name="delete_webhook_message",
                description="Delete a previously sent webhook message",
                parameters={
                    "message_id": "ID of the message to delete",
                    "webhook_url": "Webhook URL (optional if using default)",
                    "webhook_token": "Webhook token (optional if using URL)"
                },
                returns="bool - True if message was deleted",
                examples=[
                    {"text": "Delete message {{message_id}}", "code": "delete_webhook_message(message_id='{{message_id}}')"},
                    {"text": "Delete message {{message_id}} using webhook {{webhook_url}}", "code": "delete_webhook_message(message_id='{{message_id}}', webhook_url='{{webhook_url}}')"}
                ]
            )
        ]

def execute(task_hint: str, params: Dict[str, Any]) -> Any:
    """
    Execute Discord module tasks.

    Args:
        task_hint: The task type hint (discord)
        params: Task parameters

    Returns:
        Task result
    """
    module = DiscordModule()

    # Parse the command
    action = params.get('action', '').lower()

    # Simple messages
    if action in ['send', 'send_message', 'message']:
        return module.send_message(
            params['content'],
            params.get('webhook_url'),
            params.get('username'),
            params.get('avatar_url'),
            params.get('tts', False)
        )

    # Embeds
    elif action in ['send_embed', 'embed']:
        return module.send_embed(
            params['embed'],
            params.get('webhook_url'),
            params.get('username'),
            params.get('avatar_url'),
            params.get('content')
        )

    elif action in ['create_embed']:
        return module.create_embed(
            params.get('title'),
            params.get('description'),
            params.get('color'),
            params.get('url'),
            params.get('timestamp'),
            params.get('footer'),
            params.get('image'),
            params.get('thumbnail'),
            params.get('author'),
            params.get('fields')
        )

    # Files
    elif action in ['send_file', 'upload']:
        return module.send_file(
            params['file_path'],
            params.get('filename'),
            params.get('content'),
            params.get('webhook_url'),
            params.get('username')
        )

    # Message management
    elif action in ['edit_message', 'edit']:
        return module.edit_webhook_message(
            params['message_id'],
            params.get('content'),
            params.get('embeds'),
            params.get('webhook_url'),
            params.get('webhook_token')
        )

    elif action in ['delete_message', 'delete']:
        return module.delete_webhook_message(
            params['message_id'],
            params.get('webhook_url'),
            params.get('webhook_token')
        )

    # Notifications and alerts
    elif action in ['notify', 'notification']:
        return module.send_notification(
            params['title'],
            params['message'],
            params.get('color', 0x00FF00),
            params.get('level', 'info'),
            params.get('webhook_url')
        )

    elif action in ['alert']:
        return module.send_alert(
            params['message'],
            params.get('webhook_url'),
            params.get('mention_everyone', False),
            params.get('mention_users'),
            params.get('mention_roles')
        )

    elif action in ['status', 'status_update']:
        return module.send_status_update(
            params['service'],
            params['status'],
            params.get('details'),
            params.get('webhook_url')
        )

    elif action in ['log']:
        return module.send_log(
            params['level'],
            params['message'],
            params.get('source'),
            params.get('webhook_url')
        )

    else:
        raise ValueError(f"Unknown action: {action}")
