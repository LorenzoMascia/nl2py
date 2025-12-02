"""
Telegram Module for NL2Py
Provides comprehensive Telegram bot integration via Bot API.

Module Type: (telegram)
Primary Use Cases: Notifications, alerts, bot automation, chat integration

Author: NL2Py Development Team
Version: 1.0.0
"""

import os
import json
import threading
from typing import Dict, Any, List, Optional, Union
import requests
from .module_base import NL2PyModuleBase


class TelegramModule(NL2PyModuleBase):
    """
    Telegram module for sending messages, media, and managing bot interactions.

    Features:
    - Message Sending: Text, Markdown, HTML formatting
    - Media Support: Photos, videos, documents, audio
    - Interactive Elements: Inline keyboards, reply keyboards
    - Message Management: Edit, delete, pin messages
    - Chat Operations: Get chat info, member management
    - File Handling: Send and receive files
    - Notifications: Silent messages, disable preview
    - Formatting: Markdown, HTML, mentions, emojis
    - Error Handling: Comprehensive error messages

    Configuration (nl2py.conf):
        [telegram]
        BOT_TOKEN = 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
        CHAT_ID =
        PARSE_MODE = Markdown
        DISABLE_NOTIFICATION = false
        DISABLE_WEB_PAGE_PREVIEW = false
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
        """Initialize the Telegram module."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    # Configuration
                    self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
                    self.default_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
                    self.parse_mode = os.getenv('TELEGRAM_PARSE_MODE', 'Markdown')
                    self.disable_notification = os.getenv('TELEGRAM_DISABLE_NOTIFICATION', 'false').lower() == 'true'
                    self.disable_web_page_preview = os.getenv('TELEGRAM_DISABLE_WEB_PAGE_PREVIEW', 'false').lower() == 'true'

                    # API base URL
                    self.api_base = f'https://api.telegram.org/bot{self.bot_token}'

                    self._initialized = True

    def send_message(self, text: str, chat_id: Optional[str] = None,
                    parse_mode: Optional[str] = None, disable_notification: Optional[bool] = None,
                    disable_web_page_preview: Optional[bool] = None,
                    reply_to_message_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Send a text message.

        Args:
            text: Message text (up to 4096 characters)
            chat_id: Chat ID to send to (uses default if not provided)
            parse_mode: Parse mode (Markdown, MarkdownV2, HTML)
            disable_notification: Send silently
            disable_web_page_preview: Disable link previews
            reply_to_message_id: Reply to specific message

        Returns:
            Response dictionary with message info
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        payload = {
            'chat_id': chat,
            'text': text[:4096],  # Telegram limit
            'parse_mode': parse_mode or self.parse_mode
        }

        if disable_notification is not None:
            payload['disable_notification'] = disable_notification
        elif self.disable_notification:
            payload['disable_notification'] = True

        if disable_web_page_preview is not None:
            payload['disable_web_page_preview'] = disable_web_page_preview
        elif self.disable_web_page_preview:
            payload['disable_web_page_preview'] = True

        if reply_to_message_id:
            payload['reply_to_message_id'] = reply_to_message_id

        response = self._make_request('sendMessage', payload)
        return response

    def send_photo(self, photo: str, chat_id: Optional[str] = None,
                  caption: Optional[str] = None, parse_mode: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a photo.

        Args:
            photo: Photo file path or URL
            chat_id: Chat ID to send to
            caption: Photo caption (up to 1024 characters)
            parse_mode: Parse mode for caption

        Returns:
            Response dictionary
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        # Check if it's a URL or file path
        if photo.startswith('http://') or photo.startswith('https://'):
            # Send by URL
            payload = {
                'chat_id': chat,
                'photo': photo
            }
            if caption:
                payload['caption'] = caption[:1024]
                payload['parse_mode'] = parse_mode or self.parse_mode

            response = self._make_request('sendPhoto', payload)
        else:
            # Send as file
            payload = {'chat_id': chat}
            if caption:
                payload['caption'] = caption[:1024]
                payload['parse_mode'] = parse_mode or self.parse_mode

            files = {'photo': open(photo, 'rb')}
            response = self._make_request('sendPhoto', payload, files=files)
            files['photo'].close()

        return response

    def send_document(self, document: str, chat_id: Optional[str] = None,
                     caption: Optional[str] = None, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a document/file.

        Args:
            document: Document file path or URL
            chat_id: Chat ID to send to
            caption: Document caption
            filename: Custom filename

        Returns:
            Response dictionary
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        if document.startswith('http://') or document.startswith('https://'):
            # Send by URL
            payload = {
                'chat_id': chat,
                'document': document
            }
            if caption:
                payload['caption'] = caption[:1024]

            response = self._make_request('sendDocument', payload)
        else:
            # Send as file
            payload = {'chat_id': chat}
            if caption:
                payload['caption'] = caption[:1024]

            file_to_send = open(document, 'rb')
            files = {
                'document': (filename or os.path.basename(document), file_to_send)
            }
            response = self._make_request('sendDocument', payload, files=files)
            file_to_send.close()

        return response

    def send_video(self, video: str, chat_id: Optional[str] = None,
                  caption: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a video.

        Args:
            video: Video file path or URL
            chat_id: Chat ID to send to
            caption: Video caption

        Returns:
            Response dictionary
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        if video.startswith('http://') or video.startswith('https://'):
            payload = {
                'chat_id': chat,
                'video': video
            }
            if caption:
                payload['caption'] = caption[:1024]

            response = self._make_request('sendVideo', payload)
        else:
            payload = {'chat_id': chat}
            if caption:
                payload['caption'] = caption[:1024]

            files = {'video': open(video, 'rb')}
            response = self._make_request('sendVideo', payload, files=files)
            files['video'].close()

        return response

    def send_location(self, latitude: float, longitude: float,
                     chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a location.

        Args:
            latitude: Latitude
            longitude: Longitude
            chat_id: Chat ID to send to

        Returns:
            Response dictionary
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        payload = {
            'chat_id': chat,
            'latitude': latitude,
            'longitude': longitude
        }

        response = self._make_request('sendLocation', payload)
        return response

    def edit_message(self, message_id: int, text: str, chat_id: Optional[str] = None,
                    parse_mode: Optional[str] = None) -> Dict[str, Any]:
        """
        Edit a message.

        Args:
            message_id: ID of message to edit
            text: New message text
            chat_id: Chat ID
            parse_mode: Parse mode

        Returns:
            Response dictionary
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        payload = {
            'chat_id': chat,
            'message_id': message_id,
            'text': text[:4096],
            'parse_mode': parse_mode or self.parse_mode
        }

        response = self._make_request('editMessageText', payload)
        return response

    def delete_message(self, message_id: int, chat_id: Optional[str] = None) -> bool:
        """
        Delete a message.

        Args:
            message_id: ID of message to delete
            chat_id: Chat ID

        Returns:
            True if successful
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        payload = {
            'chat_id': chat,
            'message_id': message_id
        }

        self._make_request('deleteMessage', payload)
        return True

    def pin_message(self, message_id: int, chat_id: Optional[str] = None,
                   disable_notification: bool = False) -> bool:
        """
        Pin a message.

        Args:
            message_id: ID of message to pin
            chat_id: Chat ID
            disable_notification: Pin silently

        Returns:
            True if successful
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        payload = {
            'chat_id': chat,
            'message_id': message_id,
            'disable_notification': disable_notification
        }

        self._make_request('pinChatMessage', payload)
        return True

    def unpin_message(self, message_id: Optional[int] = None,
                     chat_id: Optional[str] = None) -> bool:
        """
        Unpin a message.

        Args:
            message_id: ID of message to unpin (unpins all if not provided)
            chat_id: Chat ID

        Returns:
            True if successful
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        payload = {'chat_id': chat}
        if message_id:
            payload['message_id'] = message_id

        self._make_request('unpinChatMessage', payload)
        return True

    def send_notification(self, title: str, message: str, level: str = 'info',
                         chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a formatted notification.

        Args:
            title: Notification title
            message: Notification message
            level: Notification level (info, success, warning, error)
            chat_id: Chat ID to send to

        Returns:
            Response dictionary
        """
        # Emoji mapping
        emojis = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }

        emoji = emojis.get(level.lower(), '📢')

        text = f"{emoji} *{title}*\n\n{message}"

        return self.send_message(text, chat_id, parse_mode='Markdown')

    def send_alert(self, message: str, chat_id: Optional[str] = None,
                  mention_users: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send an alert message.

        Args:
            message: Alert message
            chat_id: Chat ID to send to
            mention_users: List of usernames to mention (without @)

        Returns:
            Response dictionary
        """
        text = f"🚨 *ALERT*\n\n{message}"

        if mention_users:
            mentions = ' '.join([f"@{user}" for user in mention_users])
            text = f"{mentions}\n\n{text}"

        return self.send_message(text, chat_id, parse_mode='Markdown')

    def send_status_update(self, service: str, status: str, details: Optional[str] = None,
                          chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a service status update.

        Args:
            service: Service name
            status: Status (online, degraded, offline)
            details: Optional status details
            chat_id: Chat ID to send to

        Returns:
            Response dictionary
        """
        # Status emojis
        status_info = {
            'online': {'emoji': '🟢', 'text': 'Online'},
            'degraded': {'emoji': '🟡', 'text': 'Degraded'},
            'offline': {'emoji': '🔴', 'text': 'Offline'}
        }

        info = status_info.get(status.lower(), {'emoji': '⚪', 'text': status.title()})

        text = f"*Service Status Update*\n\n"
        text += f"*Service:* {service}\n"
        text += f"*Status:* {info['emoji']} {info['text']}"

        if details:
            text += f"\n*Details:* {details}"

        return self.send_message(text, chat_id, parse_mode='Markdown')

    def send_log(self, level: str, message: str, source: Optional[str] = None,
                chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a log message.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            source: Optional log source
            chat_id: Chat ID to send to

        Returns:
            Response dictionary
        """
        level_info = {
            'DEBUG': {'emoji': '🔍'},
            'INFO': {'emoji': 'ℹ️'},
            'WARNING': {'emoji': '⚠️'},
            'ERROR': {'emoji': '❌'},
            'CRITICAL': {'emoji': '🔥'}
        }

        info = level_info.get(level.upper(), {'emoji': '📝'})

        text = f"{info['emoji']} *{level.upper()}*"
        if source:
            text += f" - `{source}`"
        text += f"\n\n{message}"

        return self.send_message(text, chat_id, parse_mode='Markdown')

    def get_updates(self, offset: Optional[int] = None, limit: int = 100,
                   timeout: int = 0) -> List[Dict[str, Any]]:
        """
        Get updates (incoming messages, etc.).

        Args:
            offset: Identifier of the first update to return
            limit: Number of updates to retrieve (1-100)
            timeout: Timeout for long polling

        Returns:
            List of updates
        """
        payload = {
            'limit': min(limit, 100),
            'timeout': timeout
        }

        if offset is not None:
            payload['offset'] = offset

        response = self._make_request('getUpdates', payload)
        return response.get('result', [])

    def get_me(self) -> Dict[str, Any]:
        """
        Get bot information.

        Returns:
            Bot information dictionary
        """
        response = self._make_request('getMe', {})
        return response.get('result', {})

    def get_chat(self, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get chat information.

        Args:
            chat_id: Chat ID (uses default if not provided)

        Returns:
            Chat information dictionary
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        payload = {'chat_id': chat}
        response = self._make_request('getChat', payload)
        return response.get('result', {})

    def send_chat_action(self, action: str, chat_id: Optional[str] = None) -> bool:
        """
        Send chat action (typing, uploading, etc.).

        Args:
            action: Action type (typing, upload_photo, upload_video, upload_document, etc.)
            chat_id: Chat ID

        Returns:
            True if successful
        """
        chat = chat_id or self.default_chat_id
        if not chat:
            raise ValueError("No chat ID provided")

        payload = {
            'chat_id': chat,
            'action': action
        }

        self._make_request('sendChatAction', payload)
        return True

    def _make_request(self, method: str, payload: Dict[str, Any],
                     files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to Telegram Bot API.

        Args:
            method: API method name
            payload: Request payload
            files: Optional files to upload

        Returns:
            Response dictionary
        """
        url = f"{self.api_base}/{method}"

        try:
            if files:
                response = requests.post(url, data=payload, files=files)
            else:
                response = requests.post(url, json=payload)

            response.raise_for_status()
            result = response.json()

            if not result.get('ok'):
                error_desc = result.get('description', 'Unknown error')
                raise Exception(f"Telegram API error: {error_desc}")

            return result

        except requests.exceptions.RequestException as e:
            raise Exception(f"Telegram API request failed: {str(e)}")

    @classmethod
    def get_metadata(cls):
        """Get module metadata."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Telegram",
            task_type="telegram",
            description="Telegram Bot API integration for notifications, alerts, and bot automation",
            version="1.0.0",
            keywords=["telegram", "bot", "notification", "alert", "message", "chat", "media"],
            dependencies=["requests>=2.31.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes."""
        return [
            "Bot token required - get from @BotFather on Telegram (/newbot command)",
            "Chat ID required - send message to bot, then call getUpdates API to find it",
            "Use send_message() for text messages with Markdown/HTML formatting (4096 chars max)",
            "Use send_photo() for images (10 MB max for photos)",
            "Use send_document() for files (50 MB max)",
            "Use send_video() for videos",
            "Use send_location() for GPS coordinates",
            "Use edit_message() to modify sent messages",
            "Use pin_message() to pin important messages in chats",
            "Use send_notification() for pre-formatted info/success/warning/error messages",
            "Use send_alert() for urgent messages with mentions",
            "Use send_status_update() for service monitoring",
            "Markdown formatting: *bold* _italic_ `code` ```code block``` [link](url)",
            "HTML formatting: <b>bold</b> <i>italic</i> <code>code</code> <a href='url'>link</a>",
            "Rate limits: 30 messages/second per chat, 20 messages/minute to different chats",
            "Module uses singleton pattern - one instance shared across all operations"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about module methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="send_message",
                description="Send a text message with optional formatting",
                parameters={
                    "text": "Message text (max 4096 characters)",
                    "chat_id": "Optional chat ID (uses default if not provided)",
                    "parse_mode": "Optional: 'Markdown', 'MarkdownV2', or 'HTML'",
                    "disable_notification": "Send silently (default: False)",
                    "disable_web_page_preview": "Disable link previews (default: False)",
                    "reply_to_message_id": "Optional message ID to reply to"
                },
                returns="Dict with message details including message_id",
                examples=[
                    {"text": "Send message {{message}}", "code": "send_message(text='{{message}}')"},
                    {"text": "Send message {{formatted_text}} with Markdown", "code": "send_message(text='{{formatted_text}}', parse_mode='Markdown')"},
                    {"text": "Send silent message {{message}}", "code": "send_message(text='{{message}}', disable_notification=True)"}
                ]
            ),
            MethodInfo(
                name="send_photo",
                description="Send a photo from URL or file path",
                parameters={
                    "photo": "Photo URL or file path",
                    "chat_id": "Optional chat ID",
                    "caption": "Optional photo caption (max 1024 chars)",
                    "parse_mode": "Optional caption formatting"
                },
                returns="Dict with message details",
                examples=[
                    {"text": "Send photo {{url}} with caption {{caption}}", "code": "send_photo(photo='{{url}}', caption='{{caption}}')"},
                    {"text": "Send photo {{file_path}} with caption {{caption}}", "code": "send_photo(photo='{{file_path}}', caption='{{caption}}')"}
                ]
            ),
            MethodInfo(
                name="send_document",
                description="Send a document/file",
                parameters={
                    "document": "File path or URL",
                    "chat_id": "Optional chat ID",
                    "caption": "Optional file caption",
                    "filename": "Optional custom filename"
                },
                returns="Dict with message details",
                examples=[
                    {"text": "Send document {{file_path}} with caption {{caption}}", "code": "send_document(document='{{file_path}}', caption='{{caption}}')"},
                    {"text": "Send document {{file_path}} with filename {{custom_name}}", "code": "send_document(document='{{file_path}}', filename='{{custom_name}}')"}
                ]
            ),
            MethodInfo(
                name="send_video",
                description="Send a video file",
                parameters={
                    "video": "Video file path or URL",
                    "chat_id": "Optional chat ID",
                    "caption": "Optional video caption",
                    "duration": "Optional video duration in seconds"
                },
                returns="Dict with message details",
                examples=[
                    {"text": "Send video {{file_path}} with caption {{caption}}", "code": "send_video(video='{{file_path}}', caption='{{caption}}')"}
                ]
            ),
            MethodInfo(
                name="send_location",
                description="Send a GPS location",
                parameters={
                    "latitude": "Latitude coordinate",
                    "longitude": "Longitude coordinate",
                    "chat_id": "Optional chat ID"
                },
                returns="Dict with message details",
                examples=[
                    {"text": "Send location at coordinates {{latitude}}, {{longitude}}", "code": "send_location(latitude={{latitude}}, longitude={{longitude}})"}
                ]
            ),
            MethodInfo(
                name="edit_message",
                description="Edit a previously sent message",
                parameters={
                    "message_id": "ID of message to edit",
                    "text": "New message text",
                    "chat_id": "Optional chat ID",
                    "parse_mode": "Optional text formatting"
                },
                returns="Dict with edited message details",
                examples=[
                    {"text": "Edit message {{message_id}} with text {{new_text}}", "code": "edit_message(message_id={{message_id}}, text='{{new_text}}')"}
                ]
            ),
            MethodInfo(
                name="delete_message",
                description="Delete a message",
                parameters={
                    "message_id": "ID of message to delete",
                    "chat_id": "Optional chat ID"
                },
                returns="Boolean indicating success",
                examples=[
                    {"text": "Delete message {{message_id}}", "code": "delete_message(message_id={{message_id}})"}
                ]
            ),
            MethodInfo(
                name="pin_message",
                description="Pin a message in the chat",
                parameters={
                    "message_id": "ID of message to pin",
                    "chat_id": "Optional chat ID",
                    "disable_notification": "Pin silently (default: False)"
                },
                returns="Boolean indicating success",
                examples=[
                    {"text": "Pin message {{message_id}}", "code": "pin_message(message_id={{message_id}})"},
                    {"text": "Pin message {{message_id}} silently", "code": "pin_message(message_id={{message_id}}, disable_notification=True)"}
                ]
            ),
            MethodInfo(
                name="unpin_message",
                description="Unpin a message or all messages",
                parameters={
                    "message_id": "Optional message ID (unpins all if not provided)",
                    "chat_id": "Optional chat ID"
                },
                returns="Boolean indicating success",
                examples=[
                    {"text": "Unpin message {{message_id}}", "code": "unpin_message(message_id={{message_id}})"},
                    {"text": "Unpin all pinned messages", "code": "unpin_message()"}
                ]
            ),
            MethodInfo(
                name="send_notification",
                description="Send a pre-formatted notification (info, success, warning, error)",
                parameters={
                    "title": "Notification title",
                    "message": "Notification message",
                    "level": "Severity: 'info', 'success', 'warning', 'error'",
                    "chat_id": "Optional chat ID"
                },
                returns="Dict with message details",
                examples=[
                    {"text": "Send success notification {{title}}: {{message}}", "code": "send_notification(title='{{title}}', message='{{message}}', level='success')"},
                    {"text": "Send warning notification {{title}}: {{message}}", "code": "send_notification(title='{{title}}', message='{{message}}', level='warning')"}
                ]
            ),
            MethodInfo(
                name="send_alert",
                description="Send an urgent alert with optional mentions",
                parameters={
                    "message": "Alert message",
                    "chat_id": "Optional chat ID",
                    "mention_users": "Optional list of usernames to mention"
                },
                returns="Dict with message details",
                examples=[
                    {"text": "Send alert {{alert_message}}", "code": "send_alert(message='{{alert_message}}')"},
                    {"text": "Send alert {{alert_message}} mentioning users {{user_list}}", "code": "send_alert(message='{{alert_message}}', mention_users={{user_list}})"}
                ]
            ),
            MethodInfo(
                name="send_status_update",
                description="Send a service status update",
                parameters={
                    "service": "Service name",
                    "status": "Status: 'online', 'degraded', 'offline'",
                    "details": "Optional status details",
                    "chat_id": "Optional chat ID"
                },
                returns="Dict with message details",
                examples=[
                    {"text": "Send status update for service {{service_name}} with status online", "code": "send_status_update(service='{{service_name}}', status='online')"},
                    {"text": "Send status update for service {{service_name}} with status degraded and details {{details}}", "code": "send_status_update(service='{{service_name}}', status='degraded', details='{{details}}')"}
                ]
            ),
            MethodInfo(
                name="send_log",
                description="Send a structured log message",
                parameters={
                    "level": "Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
                    "message": "Log message",
                    "source": "Optional source/module name",
                    "chat_id": "Optional chat ID"
                },
                returns="Dict with message details",
                examples=[
                    {"text": "Send ERROR log {{log_message}} from source {{source}}", "code": "send_log(level='ERROR', message='{{log_message}}', source='{{source}}')"},
                    {"text": "Send INFO log {{log_message}}", "code": "send_log(level='INFO', message='{{log_message}}')"}
                ]
            ),
            MethodInfo(
                name="get_me",
                description="Get information about the bot",
                parameters={},
                returns="Dict with bot information (username, first_name, etc.)",
                examples=[
                    {"text": "Get bot information", "code": "get_me()"}
                ]
            ),
            MethodInfo(
                name="get_chat",
                description="Get information about a chat",
                parameters={
                    "chat_id": "Optional chat ID (uses default if not provided)"
                },
                returns="Dict with chat information",
                examples=[
                    {"text": "Get default chat information", "code": "get_chat()"},
                    {"text": "Get chat information for {{chat_id}}", "code": "get_chat(chat_id='{{chat_id}}')"}
                ]
            ),
            MethodInfo(
                name="send_chat_action",
                description="Send a chat action (typing indicator, etc.)",
                parameters={
                    "action": "Action: typing, upload_photo, upload_video, upload_document, etc.",
                    "chat_id": "Optional chat ID"
                },
                returns="Boolean indicating success",
                examples=[
                    {"text": "Send chat action typing", "code": "send_chat_action(action='typing')"},
                    {"text": "Send chat action upload_photo", "code": "send_chat_action(action='upload_photo')"}
                ]
            ),
            MethodInfo(
                name="get_updates",
                description="Get incoming updates (messages, commands, callbacks) using long polling",
                parameters={
                    "offset": "int (optional) - Identifier of first update to return",
                    "limit": "int (optional) - Max number of updates (1-100, default 100)",
                    "timeout": "int (optional) - Long polling timeout in seconds (default 0)"
                },
                returns="list[dict] - List of update objects with messages, callback queries, etc.",
                examples=[
                    {"text": "Get all pending updates", "code": "get_updates()"},
                    {"text": "Get updates with timeout {{timeout_seconds}}", "code": "get_updates(timeout={{timeout_seconds}})"},
                    {"text": "Get updates from offset {{update_id}}", "code": "get_updates(offset={{update_id}})"}
                ]
            )
        ]

def execute(task_hint: str, params: Dict[str, Any]) -> Any:
    """
    Execute Telegram module tasks.

    Args:
        task_hint: The task type hint (telegram)
        params: Task parameters

    Returns:
        Task result
    """
    module = TelegramModule()

    # Parse the command
    action = params.get('action', '').lower()

    # Messages
    if action in ['send', 'send_message', 'message']:
        return module.send_message(
            params['text'],
            params.get('chat_id'),
            params.get('parse_mode'),
            params.get('disable_notification'),
            params.get('disable_web_page_preview'),
            params.get('reply_to_message_id')
        )

    # Media
    elif action in ['send_photo', 'photo']:
        return module.send_photo(
            params['photo'],
            params.get('chat_id'),
            params.get('caption'),
            params.get('parse_mode')
        )

    elif action in ['send_document', 'document', 'file']:
        return module.send_document(
            params['document'],
            params.get('chat_id'),
            params.get('caption'),
            params.get('filename')
        )

    elif action in ['send_video', 'video']:
        return module.send_video(
            params['video'],
            params.get('chat_id'),
            params.get('caption')
        )

    elif action in ['send_location', 'location']:
        return module.send_location(
            params['latitude'],
            params['longitude'],
            params.get('chat_id')
        )

    # Message management
    elif action in ['edit_message', 'edit']:
        return module.edit_message(
            params['message_id'],
            params['text'],
            params.get('chat_id'),
            params.get('parse_mode')
        )

    elif action in ['delete_message', 'delete']:
        return module.delete_message(
            params['message_id'],
            params.get('chat_id')
        )

    elif action in ['pin_message', 'pin']:
        return module.pin_message(
            params['message_id'],
            params.get('chat_id'),
            params.get('disable_notification', False)
        )

    elif action in ['unpin_message', 'unpin']:
        return module.unpin_message(
            params.get('message_id'),
            params.get('chat_id')
        )

    # Notifications and alerts
    elif action in ['notify', 'notification']:
        return module.send_notification(
            params['title'],
            params['message'],
            params.get('level', 'info'),
            params.get('chat_id')
        )

    elif action in ['alert']:
        return module.send_alert(
            params['message'],
            params.get('chat_id'),
            params.get('mention_users')
        )

    elif action in ['status', 'status_update']:
        return module.send_status_update(
            params['service'],
            params['status'],
            params.get('details'),
            params.get('chat_id')
        )

    elif action in ['log']:
        return module.send_log(
            params['level'],
            params['message'],
            params.get('source'),
            params.get('chat_id')
        )

    # Bot operations
    elif action in ['get_updates', 'updates']:
        return module.get_updates(
            params.get('offset'),
            params.get('limit', 100),
            params.get('timeout', 0)
        )

    elif action in ['get_me', 'me']:
        return module.get_me()

    elif action in ['get_chat', 'chat']:
        return module.get_chat(params.get('chat_id'))

    elif action in ['chat_action', 'action']:
        return module.send_chat_action(
            params['action'],
            params.get('chat_id')
        )

    else:
        raise ValueError(f"Unknown action: {action}")
