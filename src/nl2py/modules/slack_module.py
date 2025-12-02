"""
Slack Module for NL2Py

This module provides integration with Slack for sending messages, notifications,
and interactive blocks to channels and users.

Supported operations:
- Send messages to channels
- Send direct messages
- Send rich block messages
- Upload files
- Update messages
- Delete messages
- React to messages
- Send threaded messages

Configuration (nl2py.conf):
[slack]
# Option 1: Incoming Webhook (Simple)
WEBHOOK_URL = https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX

# Option 2: Bot Token (Advanced - full API access)
BOT_TOKEN = xoxb-your-bot-token-here
DEFAULT_CHANNEL = #general

# Optional settings
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0
PROXY = http://proxy.example.com:8080

Author: NL2Py Team
Version: 1.0
"""

import json
import logging
import threading
import time
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urljoin
from .module_base import NL2PyModuleBase

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlackModule(NL2PyModuleBase):
    """
    Slack integration module.

    Supports both webhook-based and bot token authentication.
    Implements singleton pattern for efficient resource management.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        bot_token: Optional[str] = None,
        default_channel: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        proxy: Optional[str] = None,
    ):
        """
        Initialize Slack module.

        Args:
            webhook_url: Slack incoming webhook URL (for simple messaging)
            bot_token: Slack bot token (for full API access)
            default_channel: Default channel for messages (e.g., #general, @username)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Backoff factor for retries
            proxy: Optional proxy URL
        """
        # Prevent re-initialization
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.default_channel = default_channel
        self.timeout = timeout
        self.api_base_url = "https://slack.com/api"

        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if proxy:
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }

        # Set default headers for bot token
        if self.bot_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.bot_token}',
                'Content-Type': 'application/json'
            })

        self._initialized = True
        logger.info("Slack module initialized")

    def _api_call(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a Slack API call.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request payload
            files: Files to upload

        Returns:
            API response data

        Raises:
            Exception: If API call fails
        """
        url = f"{self.api_base_url}/{endpoint}"

        try:
            if files:
                # For file uploads, don't use JSON content-type
                response = self.session.request(
                    method,
                    url,
                    data=data,
                    files=files,
                    timeout=self.timeout
                )
            else:
                response = self.session.request(
                    method,
                    url,
                    json=data,
                    timeout=self.timeout
                )

            response.raise_for_status()
            result = response.json()

            # Check Slack API response
            if not result.get('ok', False):
                error = result.get('error', 'Unknown error')
                logger.error(f"Slack API error: {error}")
                raise Exception(f"Slack API error: {error}")

            logger.info(f"Slack API call successful: {endpoint}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Slack API request failed: {e}")
            raise Exception(f"Slack API request failed: {e}")

    def send_message(
        self,
        text: str,
        channel: Optional[str] = None,
        username: Optional[str] = None,
        icon_emoji: Optional[str] = None,
        icon_url: Optional[str] = None,
        thread_ts: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.

        Args:
            text: Message text (supports Slack markdown)
            channel: Target channel (uses default if not specified)
            username: Bot username to display
            icon_emoji: Bot icon emoji (e.g., ":robot_face:")
            icon_url: Bot icon URL
            thread_ts: Thread timestamp (for threaded messages)
            attachments: Message attachments (legacy format)

        Returns:
            Response data from Slack API

        Raises:
            Exception: If message sending fails
        """
        if self.webhook_url:
            return self._send_webhook_message(
                text, username, icon_emoji, icon_url, attachments
            )
        else:
            return self._send_api_message(
                text, channel, username, icon_emoji, icon_url, thread_ts, attachments
            )

    def _send_webhook_message(
        self,
        text: str,
        username: Optional[str] = None,
        icon_emoji: Optional[str] = None,
        icon_url: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send message using incoming webhook."""
        payload = {
            "text": text
        }

        if username:
            payload["username"] = username
        if icon_emoji:
            payload["icon_emoji"] = icon_emoji
        if icon_url:
            payload["icon_url"] = icon_url
        if attachments:
            payload["attachments"] = attachments

        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info("Message sent successfully via webhook")
            return {"status": "success", "response": response.text}

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send webhook message: {e}")
            raise Exception(f"Failed to send message: {e}")

    def _send_api_message(
        self,
        text: str,
        channel: Optional[str] = None,
        username: Optional[str] = None,
        icon_emoji: Optional[str] = None,
        icon_url: Optional[str] = None,
        thread_ts: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send message using Slack API."""
        if not self.bot_token:
            raise ValueError("Bot token required for API messaging")

        channel = channel or self.default_channel
        if not channel:
            raise ValueError("Channel is required")

        payload = {
            "channel": channel,
            "text": text
        }

        if username:
            payload["username"] = username
        if icon_emoji:
            payload["icon_emoji"] = icon_emoji
        if icon_url:
            payload["icon_url"] = icon_url
        if thread_ts:
            payload["thread_ts"] = thread_ts
        if attachments:
            payload["attachments"] = attachments

        return self._api_call("POST", "chat.postMessage", payload)

    def send_blocks(
        self,
        blocks: List[Dict[str, Any]],
        channel: Optional[str] = None,
        text: Optional[str] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message with Block Kit blocks.

        Args:
            blocks: List of block elements
            channel: Target channel
            text: Fallback text
            thread_ts: Thread timestamp (for replies)

        Returns:
            API response
        """
        if self.webhook_url:
            return self._send_webhook_blocks(blocks, text)
        else:
            return self._send_api_blocks(blocks, channel, text, thread_ts)

    def _send_webhook_blocks(
        self,
        blocks: List[Dict[str, Any]],
        text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send blocks via webhook."""
        payload = {
            "blocks": blocks,
            "text": text or "New message"
        }

        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info("Blocks sent successfully via webhook")
            return {"status": "success", "response": response.text}

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send blocks: {e}")
            raise Exception(f"Failed to send blocks: {e}")

    def _send_api_blocks(
        self,
        blocks: List[Dict[str, Any]],
        channel: Optional[str] = None,
        text: Optional[str] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send blocks via API."""
        if not self.bot_token:
            raise ValueError("Bot token required for API messaging")

        channel = channel or self.default_channel
        if not channel:
            raise ValueError("Channel is required")

        payload = {
            "channel": channel,
            "blocks": blocks,
            "text": text or "New message"
        }

        if thread_ts:
            payload["thread_ts"] = thread_ts

        return self._api_call("POST", "chat.postMessage", payload)

    def send_alert(
        self,
        message: str,
        severity: str = "warning",
        title: Optional[str] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an alert message with color coding.

        Args:
            message: Alert message
            severity: Alert severity (info, warning, error, success)
            title: Optional alert title
            channel: Target channel

        Returns:
            Response data
        """
        # Map severity to colors
        color_map = {
            "info": "#36a64f",      # Green
            "warning": "#ffcc00",   # Yellow
            "error": "#ff0000",     # Red
            "success": "#36a64f",   # Green
            "danger": "#ff0000"     # Red (alias)
        }

        color = color_map.get(severity.lower(), "#36a64f")
        alert_title = title or f"{severity.upper()} Alert"

        attachment = {
            "color": color,
            "title": alert_title,
            "text": message,
            "footer": "NL2Py",
            "ts": int(time.time())
        }

        return self.send_message(
            text=f"*{alert_title}*\n{message}",
            channel=channel,
            attachments=[attachment]
        )

    def send_status_message(
        self,
        title: str,
        status: str,
        fields: Optional[List[Dict[str, str]]] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a status message with fields.

        Args:
            title: Message title
            status: Status value
            fields: List of field dicts with "title" and "value"
            channel: Target channel

        Returns:
            Response data
        """
        # Determine color based on status
        status_colors = {
            "success": "#36a64f",
            "failed": "#ff0000",
            "error": "#ff0000",
            "running": "#ffcc00",
            "pending": "#0078D4"
        }
        color = status_colors.get(status.lower(), "#36a64f")

        attachment = {
            "color": color,
            "title": title,
            "text": f"Status: *{status}*",
            "footer": "NL2Py",
            "ts": int(time.time())
        }

        if fields:
            attachment["fields"] = [
                {
                    "title": field.get("title", ""),
                    "value": field.get("value", ""),
                    "short": field.get("short", True)
                }
                for field in fields
            ]

        return self.send_message(
            text=f"*{title}* - {status}",
            channel=channel,
            attachments=[attachment]
        )

    def send_rich_message(
        self,
        title: str,
        text: str,
        color: str = "#36a64f",
        fields: Optional[List[Dict[str, str]]] = None,
        footer: Optional[str] = None,
        footer_icon: Optional[str] = None,
        image_url: Optional[str] = None,
        thumb_url: Optional[str] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a rich formatted message with attachment.

        Args:
            title: Message title
            text: Message text
            color: Attachment color (hex)
            fields: List of fields
            footer: Footer text
            footer_icon: Footer icon URL
            image_url: Image URL
            thumb_url: Thumbnail URL
            channel: Target channel

        Returns:
            Response data
        """
        attachment = {
            "color": color,
            "title": title,
            "text": text,
            "ts": int(time.time())
        }

        if fields:
            attachment["fields"] = fields
        if footer:
            attachment["footer"] = footer
        if footer_icon:
            attachment["footer_icon"] = footer_icon
        if image_url:
            attachment["image_url"] = image_url
        if thumb_url:
            attachment["thumb_url"] = thumb_url

        return self.send_message(
            text=f"*{title}*",
            channel=channel,
            attachments=[attachment]
        )

    def upload_file(
        self,
        file_path: str,
        channels: Optional[Union[str, List[str]]] = None,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Slack.

        Args:
            file_path: Path to file to upload
            channels: Target channel(s)
            title: File title
            initial_comment: Initial comment
            thread_ts: Thread timestamp

        Returns:
            API response

        Raises:
            Exception: If file upload fails
        """
        if not self.bot_token:
            raise ValueError("Bot token required for file uploads")

        channels = channels or self.default_channel
        if not channels:
            raise ValueError("Channel is required for file upload")

        if isinstance(channels, list):
            channels = ",".join(channels)

        data = {
            "channels": channels
        }

        if title:
            data["title"] = title
        if initial_comment:
            data["initial_comment"] = initial_comment
        if thread_ts:
            data["thread_ts"] = thread_ts

        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                return self._api_call("POST", "files.upload", data=data, files=files)

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise Exception(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise Exception(f"Failed to upload file: {e}")

    def update_message(
        self,
        channel: str,
        timestamp: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            text: New message text
            blocks: New blocks (optional)

        Returns:
            API response
        """
        if not self.bot_token:
            raise ValueError("Bot token required for message updates")

        payload = {
            "channel": channel,
            "ts": timestamp,
            "text": text
        }

        if blocks:
            payload["blocks"] = blocks

        return self._api_call("POST", "chat.update", payload)

    def delete_message(
        self,
        channel: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """
        Delete a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp

        Returns:
            API response
        """
        if not self.bot_token:
            raise ValueError("Bot token required for message deletion")

        payload = {
            "channel": channel,
            "ts": timestamp
        }

        return self._api_call("POST", "chat.delete", payload)

    def add_reaction(
        self,
        channel: str,
        timestamp: str,
        emoji: str
    ) -> Dict[str, Any]:
        """
        Add a reaction to a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            emoji: Emoji name (without colons, e.g., "thumbsup")

        Returns:
            API response
        """
        if not self.bot_token:
            raise ValueError("Bot token required for reactions")

        payload = {
            "channel": channel,
            "timestamp": timestamp,
            "name": emoji
        }

        return self._api_call("POST", "reactions.add", payload)

    def create_section_block(
        self,
        text: str,
        text_type: str = "mrkdwn"
    ) -> Dict[str, Any]:
        """
        Create a section block.

        Args:
            text: Block text
            text_type: Text type (mrkdwn or plain_text)

        Returns:
            Section block dict
        """
        return {
            "type": "section",
            "text": {
                "type": text_type,
                "text": text
            }
        }

    def create_divider_block(self) -> Dict[str, Any]:
        """Create a divider block."""
        return {"type": "divider"}

    def create_header_block(self, text: str) -> Dict[str, Any]:
        """Create a header block."""
        return {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": text
            }
        }

    def create_fields_block(
        self,
        fields: List[str]
    ) -> Dict[str, Any]:
        """
        Create a section block with fields.

        Args:
            fields: List of field texts

        Returns:
            Section block with fields
        """
        return {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": field
                }
                for field in fields
            ]
        }

    def close(self):
        """Close the Slack module and cleanup resources."""
        if hasattr(self, 'session'):
            self.session.close()
        logger.info("Slack module closed")

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

    # ============================================================================
    # Metadata Methods (for NL2Py compiler prompt generation)
    # ============================================================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Slack",
            task_type="slack",
            description="Slack messaging and notifications with webhooks, Block Kit blocks, alerts, file uploads, and bot API integration",
            version="1.0.0",
            keywords=[
                "slack", "messaging", "notifications", "webhook", "blocks",
                "alerts", "chat", "collaboration", "bot", "api"
            ],
            dependencies=["requests>=2.28.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern - one instance per application",
            "Supports two authentication modes: webhook URL or bot token",
            "Webhook mode is simpler but limited to posting to a single channel",
            "Bot token mode requires Slack app with proper OAuth scopes",
            "Webhook URLs obtained from Slack app incoming webhooks settings",
            "Bot token starts with 'xoxb-' and requires chat:write scope",
            "Channel names start with # for public, @ for direct messages",
            "Automatic retry with exponential backoff for failed requests",
            "Default timeout is 30 seconds, configurable via timeout parameter",
            "Maximum 3 retries by default for transient failures (429, 500, 502, 503, 504)",
            "Proxy support available via proxy parameter",
            "Message text supports Slack markdown formatting",
            "Blocks use Block Kit for rich interactive messages",
            "Attachments are legacy format but still supported",
            "Alert severity levels: info (green), warning (yellow), error (red), success (green)",
            "Status messages automatically color-coded: success (green), failed/error (red), running (yellow), pending (blue)",
            "File uploads require bot token and files:write scope",
            "Thread replies use thread_ts parameter from parent message",
            "Reactions use emoji names without colons (e.g., 'thumbsup')",
            "Message updates and deletions require bot token and message timestamp",
            "Block builder methods help create header, section, divider, and fields blocks",
            "Always call close() to cleanup session resources when done"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="send_message",
                description="Send a text message to Slack channel with optional formatting",
                parameters={
                    "text": "str (required) - Message text (supports Slack markdown)",
                    "channel": "str (optional) - Target channel (#general, @username)",
                    "username": "str (optional) - Bot username to display",
                    "icon_emoji": "str (optional) - Bot icon emoji (e.g., ':robot_face:')",
                    "icon_url": "str (optional) - Bot icon URL",
                    "thread_ts": "str (optional) - Thread timestamp for replies",
                    "attachments": "list[dict] (optional) - Message attachments (legacy)"
                },
                returns="dict - Response with status and message details",
                examples=[
                    {"text": "Send message {{message}} to builds channel", "code": "send_message(text='{{message}}', channel='#builds')"},
                    {"text": "Send message {{message}} to channel {{channel}} with custom emoji icon {{emoji}}", "code": "send_message(text='{{message}}', channel='{{channel}}', icon_emoji='{{emoji}}')"}
                ]
            ),
            MethodInfo(
                name="send_blocks",
                description="Send a message with Block Kit blocks for rich formatting",
                parameters={
                    "blocks": "list[dict] (required) - List of Block Kit block elements",
                    "channel": "str (optional) - Target channel",
                    "text": "str (optional) - Fallback text for notifications",
                    "thread_ts": "str (optional) - Thread timestamp for replies"
                },
                returns="dict - Response from Slack API",
                examples=[
                    {"text": "Send blocks with header {{title}} and section {{message}} to channel {{channel}}", "code": "send_blocks(blocks=[create_header_block('{{title}}'), create_section_block('{{message}}')], channel='{{channel}}')"},
                    {"text": "Send blocks {{blocks}} with fallback text {{fallback_text}} to channel {{channel}}", "code": "send_blocks(blocks={{blocks}}, text='{{fallback_text}}', channel='{{channel}}')"}
                ]
            ),
            MethodInfo(
                name="send_alert",
                description="Send an alert message with automatic severity-based color coding",
                parameters={
                    "message": "str (required) - Alert message text",
                    "severity": "str (optional) - Alert level: info, warning, error, success, danger (default warning)",
                    "title": "str (optional) - Custom alert title (default '{SEVERITY} Alert')",
                    "channel": "str (optional) - Target channel"
                },
                returns="dict - Response data",
                examples=[
                    {"text": "Send warning alert {{alert_message}} to alerts channel", "code": "send_alert(message='{{alert_message}}', severity='warning', channel='#alerts')"},
                    {"text": "Send success alert {{message}} with custom title {{title}}", "code": "send_alert(message='{{message}}', severity='success', title='{{title}}')"},
                    {"text": "Send error alert {{error_message}} to operations channel", "code": "send_alert(message='{{error_message}}', severity='error', channel='#ops')"}
                ]
            ),
            MethodInfo(
                name="send_status_message",
                description="Send a status update message with fields",
                parameters={
                    "title": "str (required) - Status message title",
                    "status": "str (required) - Status value (Success, Failed, Running, Pending)",
                    "fields": "list[dict] (optional) - List of field dicts with 'title' and 'value' keys",
                    "channel": "str (optional) - Target channel"
                },
                returns="dict - Response data",
                examples=[
                    {"text": "Send backup status {{title}} with size field {{size}} to ops channel", "code": "send_status_message(title='{{title}}', status='Success', fields=[{'title': 'Size', 'value': '{{size}}'}], channel='#ops')"},
                    {"text": "Send running pipeline status {{pipeline_name}} with progress {{progress}}", "code": "send_status_message(title='{{pipeline_name}}', status='Running', fields=[{'title': 'Progress', 'value': '{{progress}}'}])"}
                ]
            ),
            MethodInfo(
                name="send_rich_message",
                description="Send a rich formatted message with attachment and optional images",
                parameters={
                    "title": "str (required) - Message title",
                    "text": "str (required) - Message text",
                    "color": "str (optional) - Attachment color in hex (default '#36a64f' green)",
                    "fields": "list[dict] (optional) - List of field dicts",
                    "footer": "str (optional) - Footer text",
                    "footer_icon": "str (optional) - Footer icon URL",
                    "image_url": "str (optional) - Full image URL",
                    "thumb_url": "str (optional) - Thumbnail image URL",
                    "channel": "str (optional) - Target channel"
                },
                returns="dict - Response data",
                examples=[
                    {"text": "Send rich message {{title}} with text {{text}} and revenue field {{revenue}} in custom color", "code": "send_rich_message(title='{{title}}', text='{{text}}', color='#36a64f', fields=[{'title': 'Revenue', 'value': '{{revenue}}'}])"},
                    {"text": "Send rich message {{title}} with text {{text}} and image {{image_url}} to team channel", "code": "send_rich_message(title='{{title}}', text='{{text}}', image_url='{{image_url}}', channel='#team')"}
                ]
            ),
            MethodInfo(
                name="upload_file",
                description="Upload a file to Slack channel(s)",
                parameters={
                    "file_path": "str (required) - Path to file to upload",
                    "channels": "str or list[str] (optional) - Target channel(s)",
                    "title": "str (optional) - File title",
                    "initial_comment": "str (optional) - Comment with file",
                    "thread_ts": "str (optional) - Thread timestamp"
                },
                returns="dict - API response",
                examples=[
                    {"text": "Upload file {{file_path}} with title {{title}} to reports channel", "code": "upload_file(file_path='{{file_path}}', channels='#reports', title='{{title}}')"},
                    {"text": "Upload file {{file_path}} to multiple channels with comment {{comment}}", "code": "upload_file(file_path='{{file_path}}', channels=['#bugs', '#dev'], initial_comment='{{comment}}')"}
                ]
            ),
            MethodInfo(
                name="update_message",
                description="Update an existing message by timestamp",
                parameters={
                    "channel": "str (required) - Channel ID",
                    "timestamp": "str (required) - Message timestamp (ts)",
                    "text": "str (required) - New message text",
                    "blocks": "list[dict] (optional) - New blocks"
                },
                returns="dict - API response",
                examples=[
                    {"text": "Update message in channel {{channel_id}} with timestamp {{timestamp}} to new text {{new_text}}", "code": "update_message(channel='{{channel_id}}', timestamp='{{timestamp}}', text='{{new_text}}')"}
                ]
            ),
            MethodInfo(
                name="delete_message",
                description="Delete a message by timestamp",
                parameters={
                    "channel": "str (required) - Channel ID",
                    "timestamp": "str (required) - Message timestamp (ts)"
                },
                returns="dict - API response",
                examples=[
                    {"text": "Delete message from channel {{channel_id}} with timestamp {{timestamp}}", "code": "delete_message(channel='{{channel_id}}', timestamp='{{timestamp}}')"}
                ]
            ),
            MethodInfo(
                name="add_reaction",
                description="Add an emoji reaction to a message",
                parameters={
                    "channel": "str (required) - Channel ID",
                    "timestamp": "str (required) - Message timestamp (ts)",
                    "emoji": "str (required) - Emoji name without colons (e.g., 'thumbsup', 'rocket')"
                },
                returns="dict - API response",
                examples=[
                    {"text": "Add thumbsup reaction to message in channel {{channel_id}} with timestamp {{timestamp}}", "code": "add_reaction(channel='{{channel_id}}', timestamp='{{timestamp}}', emoji='thumbsup')"},
                    {"text": "Add custom emoji {{emoji_name}} reaction to message in channel {{channel_id}} with timestamp {{timestamp}}", "code": "add_reaction(channel='{{channel_id}}', timestamp='{{timestamp}}', emoji='{{emoji_name}}')"}
                ]
            ),
            MethodInfo(
                name="create_header_block",
                description="Create a Block Kit header block",
                parameters={"text": "str (required) - Header text"},
                returns="dict - Header block",
                examples=[
                    {"text": "Create header block with text {{header_text}}", "code": "create_header_block(text='{{header_text}}')"}
                ]
            ),
            MethodInfo(
                name="create_section_block",
                description="Create a Block Kit section block with text",
                parameters={
                    "text": "str (required) - Block text",
                    "text_type": "str (optional) - Text type: 'mrkdwn' or 'plain_text' (default 'mrkdwn')"
                },
                returns="dict - Section block",
                examples=[
                    {"text": "Create markdown section block with message {{message}}", "code": "create_section_block(text='{{message}}')"},
                    {"text": "Create plain text section block with message {{message}}", "code": "create_section_block(text='{{message}}', text_type='plain_text')"}
                ]
            ),
            MethodInfo(
                name="create_fields_block",
                description="Create a Block Kit section block with multiple fields",
                parameters={"fields": "list[str] (required) - List of field texts"},
                returns="dict - Section block with fields",
                examples=[
                    {"text": "Create fields block with CPU {{cpu}}, memory {{memory}}, and disk {{disk}} metrics", "code": "create_fields_block(fields=['*CPU:* {{cpu}}%', '*Memory:* {{memory}}', '*Disk:* {{disk}}'])"}
                ]
            ),
            MethodInfo(
                name="create_divider_block",
                description="Create a Block Kit divider block",
                parameters={},
                returns="dict - Divider block",
                examples=[
                    {"text": "Create divider block for visual separation", "code": "create_divider_block()"}
                ]
            ),
            MethodInfo(
                name="close",
                description="Close Slack module and cleanup HTTP session resources",
                parameters={},
                returns="None",
                examples=[
                    {"text": "Close Slack connection and cleanup resources", "code": "close()"}
                ]
            )
        ]

# Global instance
_slack_instance = None


def get_slack_module(**config) -> SlackModule:
    """
    Get or create Slack module instance.

    Args:
        **config: Configuration parameters

    Returns:
        SlackModule instance
    """
    global _slack_instance
    if _slack_instance is None:
        _slack_instance = SlackModule(**config)
    return _slack_instance


# Example usage
if __name__ == "__main__":
    # Example with webhook
    slack = SlackModule(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    )

    # Send simple message
    slack.send_message("Hello from NL2Py!")

    # Send alert
    slack.send_alert(
        message="High CPU usage detected on server-01",
        severity="warning",
        title="System Alert"
    )

    # Send status message
    slack.send_status_message(
        title="Database Backup",
        status="Success",
        fields=[
            {"title": "Database", "value": "production_db", "short": True},
            {"title": "Size", "value": "150 GB", "short": True},
            {"title": "Duration", "value": "45 minutes", "short": True}
        ]
    )

    # Send rich message
    slack.send_rich_message(
        title="Sales Report",
        text="Daily sales summary for January 20, 2025",
        color="#36a64f",
        fields=[
            {"title": "Total Sales", "value": "$125,000", "short": True},
            {"title": "Orders", "value": "342", "short": True}
        ]
    )

    # Send blocks
    blocks = [
        slack.create_header_block("Pipeline Status"),
        slack.create_divider_block(),
        slack.create_section_block("*Status:* Success :white_check_mark:"),
        slack.create_fields_block([
            "*Records Processed:* 125,000",
            "*Duration:* 2 hours",
            "*Errors:* 0",
            "*Success Rate:* 100%"
        ])
    ]
    slack.send_blocks(blocks, text="Pipeline completed")
