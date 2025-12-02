"""
Microsoft Teams Module for NL2Py

This module provides integration with Microsoft Teams for sending messages,
notifications, and adaptive cards to channels and users.

Supported operations:
- Send messages to channels
- Send adaptive cards
- Send notifications with mentions
- Post cards with actions
- Upload files to channels
- Create threaded conversations
- Send direct messages

Configuration (nl2py.conf):
[teams]
WEBHOOK_URL = https://your-org.webhook.office.com/webhookb2/...
# OR use app-based authentication:
TENANT_ID = your-tenant-id
CLIENT_ID = your-client-id
CLIENT_SECRET = your-client-secret
TEAM_ID = your-team-id
CHANNEL_ID = your-channel-id

Author: NL2Py Team
Version: 1.0
"""

import json
import logging
import threading
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urljoin
from .module_base import NL2PyModuleBase

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TeamsModule(NL2PyModuleBase):
    """
    Microsoft Teams integration module.

    Supports both webhook-based and app-based authentication.
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
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        team_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        proxy: Optional[str] = None,
    ):
        """
        Initialize Microsoft Teams module.

        Args:
            webhook_url: Teams incoming webhook URL (for simple messaging)
            tenant_id: Azure AD tenant ID (for app-based auth)
            client_id: Azure AD application client ID
            client_secret: Azure AD application client secret
            team_id: Default team ID
            channel_id: Default channel ID
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Backoff factor for retries
            proxy: Optional proxy URL
        """
        # Prevent re-initialization
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.webhook_url = webhook_url
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.team_id = team_id
        self.channel_id = channel_id
        self.timeout = timeout
        self.access_token = None
        self.token_expiry = None

        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if proxy:
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }

        self._initialized = True
        logger.info("Teams module initialized")

    def _get_access_token(self) -> str:
        """
        Get Microsoft Graph API access token using client credentials flow.

        Returns:
            Access token string

        Raises:
            Exception: If authentication fails
        """
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError(
                "App-based authentication requires tenant_id, client_id, and client_secret"
            )

        # Check if token is still valid
        import time
        if self.access_token and self.token_expiry and time.time() < self.token_expiry:
            return self.access_token

        # Request new token
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }

        try:
            response = self.session.post(token_url, data=data, timeout=self.timeout)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data['access_token']
            # Token expires in 3600 seconds, we refresh 5 minutes earlier
            import time
            self.token_expiry = time.time() + token_data.get('expires_in', 3600) - 300

            logger.info("Successfully obtained access token")
            return self.access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get access token: {e}")
            raise Exception(f"Authentication failed: {e}")

    def send_message(
        self,
        text: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        color: str = "0078D4",
        channel_id: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a simple message to a Teams channel.

        Args:
            text: Message text content
            title: Optional message title
            subtitle: Optional message subtitle
            color: Theme color in hex format (default: Teams blue)
            channel_id: Target channel ID (uses default if not specified)
            team_id: Target team ID (uses default if not specified)

        Returns:
            Response data from Teams API

        Raises:
            Exception: If message sending fails
        """
        if self.webhook_url:
            return self._send_webhook_message(text, title, subtitle, color)
        else:
            return self._send_graph_message(text, title, subtitle, channel_id, team_id)

    def _send_webhook_message(
        self,
        text: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        color: str = "0078D4"
    ) -> Dict[str, Any]:
        """Send message using incoming webhook."""
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": color,
            "summary": title or text[:100],
        }

        sections = []
        if title:
            sections.append({
                "activityTitle": title,
                "activitySubtitle": subtitle if subtitle else "",
            })

        sections.append({
            "text": text
        })

        payload["sections"] = sections

        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info(f"Message sent successfully via webhook")
            return {"status": "success", "response": response.text}

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send webhook message: {e}")
            raise Exception(f"Failed to send message: {e}")

    def _send_graph_message(
        self,
        text: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        channel_id: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message using Microsoft Graph API."""
        token = self._get_access_token()

        team_id = team_id or self.team_id
        channel_id = channel_id or self.channel_id

        if not team_id or not channel_id:
            raise ValueError("team_id and channel_id are required for Graph API messaging")

        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Build message content
        content = ""
        if title:
            content += f"<h3>{title}</h3>"
        if subtitle:
            content += f"<p><em>{subtitle}</em></p>"
        content += f"<p>{text}</p>"

        payload = {
            "body": {
                "contentType": "html",
                "content": content
            }
        }

        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()

            logger.info(f"Message sent successfully via Graph API")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Graph API message: {e}")
            raise Exception(f"Failed to send message: {e}")

    def send_adaptive_card(
        self,
        card: Dict[str, Any],
        channel_id: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an Adaptive Card to a Teams channel.

        Args:
            card: Adaptive Card JSON payload
            channel_id: Target channel ID
            team_id: Target team ID

        Returns:
            Response data from Teams API
        """
        if self.webhook_url:
            return self._send_webhook_card(card)
        else:
            return self._send_graph_card(card, channel_id, team_id)

    def _send_webhook_card(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """Send adaptive card via webhook."""
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card
                }
            ]
        }

        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info("Adaptive card sent successfully via webhook")
            return {"status": "success", "response": response.text}

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send adaptive card: {e}")
            raise Exception(f"Failed to send adaptive card: {e}")

    def _send_graph_card(
        self,
        card: Dict[str, Any],
        channel_id: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send adaptive card via Graph API."""
        token = self._get_access_token()

        team_id = team_id or self.team_id
        channel_id = channel_id or self.channel_id

        if not team_id or not channel_id:
            raise ValueError("team_id and channel_id required")

        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        payload = {
            "body": {
                "contentType": "html",
                "content": "<attachment id=\"1\"></attachment>"
            },
            "attachments": [
                {
                    "id": "1",
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": json.dumps(card)
                }
            ]
        }

        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()

            logger.info("Adaptive card sent successfully via Graph API")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send adaptive card: {e}")
            raise Exception(f"Failed to send adaptive card: {e}")

    def send_notification(
        self,
        title: str,
        text: str,
        facts: Optional[List[Dict[str, str]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        color: str = "0078D4"
    ) -> Dict[str, Any]:
        """
        Send a formatted notification card.

        Args:
            title: Notification title
            text: Notification text
            facts: List of key-value pairs to display
            actions: List of action buttons
            color: Theme color

        Returns:
            Response data
        """
        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "Bolder",
                    "size": "Large"
                },
                {
                    "type": "TextBlock",
                    "text": text,
                    "wrap": True
                }
            ]
        }

        # Add facts if provided
        if facts:
            fact_set = {
                "type": "FactSet",
                "facts": facts
            }
            card["body"].append(fact_set)

        # Add actions if provided
        if actions:
            card["actions"] = actions

        return self.send_adaptive_card(card)

    def send_alert(
        self,
        message: str,
        severity: str = "warning",
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an alert message with appropriate styling.

        Args:
            message: Alert message
            severity: Alert severity (info, warning, error, success)
            title: Optional alert title

        Returns:
            Response data
        """
        # Map severity to colors
        color_map = {
            "info": "0078D4",      # Blue
            "warning": "FFB900",   # Yellow
            "error": "E81123",     # Red
            "success": "107C10"    # Green
        }

        color = color_map.get(severity.lower(), "0078D4")
        alert_title = title or f"{severity.upper()} Alert"

        return self.send_message(
            text=message,
            title=alert_title,
            color=color
        )

    def send_status_card(
        self,
        title: str,
        status: str,
        details: Dict[str, Any],
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a status update card.

        Args:
            title: Status card title
            status: Status value (e.g., "Success", "Failed", "Running")
            details: Dictionary of status details
            timestamp: Optional timestamp string

        Returns:
            Response data
        """
        from datetime import datetime

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Convert details dict to facts list
        facts = [{"name": k, "value": str(v)} for k, v in details.items()]
        facts.append({"name": "Timestamp", "value": timestamp})

        # Determine color based on status
        status_colors = {
            "success": "107C10",
            "failed": "E81123",
            "error": "E81123",
            "running": "FFB900",
            "pending": "0078D4"
        }
        color = status_colors.get(status.lower(), "0078D4")

        return self.send_notification(
            title=f"{title} - {status}",
            text=f"Status: **{status}**",
            facts=facts,
            color=color
        )

    def create_card_with_data_table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[str]],
        max_rows: int = 10
    ) -> Dict[str, Any]:
        """
        Create an adaptive card with a data table.

        Args:
            title: Card title
            headers: Table column headers
            rows: Table data rows
            max_rows: Maximum number of rows to display

        Returns:
            Adaptive card payload
        """
        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "Bolder",
                    "size": "Large"
                }
            ]
        }

        # Add table header
        header_columns = [
            {
                "type": "Column",
                "width": "auto",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": header,
                        "weight": "Bolder"
                    }
                ]
            }
            for header in headers
        ]

        card["body"].append({
            "type": "ColumnSet",
            "columns": header_columns
        })

        # Add table rows (limit to max_rows)
        for row in rows[:max_rows]:
            row_columns = [
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": str(cell)
                        }
                    ]
                }
                for cell in row
            ]

            card["body"].append({
                "type": "ColumnSet",
                "columns": row_columns
            })

        if len(rows) > max_rows:
            card["body"].append({
                "type": "TextBlock",
                "text": f"... and {len(rows) - max_rows} more rows",
                "isSubtle": True
            })

        return card

    def close(self):
        """Close the Teams module and cleanup resources."""
        if hasattr(self, 'session'):
            self.session.close()
        logger.info("Teams module closed")

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
            name="MicrosoftTeams",
            task_type="teams",
            description="Microsoft Teams messaging and notifications with webhooks, adaptive cards, alerts, and Graph API integration",
            version="1.0.0",
            keywords=[
                "teams", "microsoft-teams", "messaging", "notifications", "webhook",
                "adaptive-cards", "alerts", "collaboration", "chat", "graph-api"
            ],
            dependencies=["requests>=2.28.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern - one instance per application",
            "Supports two authentication modes: webhook URL or Graph API (app-based)",
            "Webhook mode is simpler but limited to posting messages to a single channel",
            "Graph API mode requires Azure AD app registration with permissions",
            "Webhook URLs obtained from Teams channel connectors settings",
            "Graph API requires tenant_id, client_id, client_secret, team_id, channel_id",
            "Access tokens automatically refreshed 5 minutes before expiry",
            "Adaptive Cards version 1.4 supported for rich interactive messages",
            "Theme colors specified in hex format without # prefix (e.g., '0078D4')",
            "Automatic retry with exponential backoff for failed requests",
            "Default timeout is 30 seconds, configurable via timeout parameter",
            "Maximum 3 retries by default for transient failures (429, 500, 502, 503, 504)",
            "Proxy support available via proxy parameter",
            "Message titles, subtitles, and colors customizable per message",
            "Facts displayed as key-value pairs in notification cards",
            "Alert severity levels: info (blue), warning (yellow), error (red), success (green)",
            "Status cards automatically include timestamp if not provided",
            "Data tables limited to 10 rows by default to prevent card overflow",
            "Session with connection pooling for efficient HTTP requests",
            "Always call close() to cleanup session resources when done"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="send_message",
                description="Send a simple text message to Teams channel with optional title and styling",
                parameters={
                    "text": "str (required) - Message text content",
                    "title": "str (optional) - Message title",
                    "subtitle": "str (optional) - Message subtitle",
                    "color": "str (optional) - Theme color in hex (default '0078D4' Teams blue)",
                    "channel_id": "str (optional) - Target channel ID (Graph API mode)",
                    "team_id": "str (optional) - Target team ID (Graph API mode)"
                },
                returns="dict - Response with status and message details",
                examples=[
                    {"text": "Send message {{message}} with title {{title}}", "code": "send_message(text='{{message}}', title='{{title}}')"},
                    {"text": "Send message {{message}} with title {{title}} and color {{hex_color}}", "code": "send_message(text='{{message}}', title='{{title}}', color='{{hex_color}}')"}
                ]
            ),
            MethodInfo(
                name="send_adaptive_card",
                description="Send an Adaptive Card with rich interactive content",
                parameters={
                    "card": "dict (required) - Adaptive Card JSON payload",
                    "channel_id": "str (optional) - Target channel ID",
                    "team_id": "str (optional) - Target team ID"
                },
                returns="dict - Response from Teams API",
                examples=[
                    {"text": "Send adaptive card {{card_payload}}", "code": "send_adaptive_card(card={{card_payload}})"},
                    {"text": "Send card {{card_payload}} to channel {{channel_id}} in team {{team_id}}", "code": "send_adaptive_card(card={{card_payload}}, channel_id='{{channel_id}}', team_id='{{team_id}}')"}
                ]
            ),
            MethodInfo(
                name="send_notification",
                description="Send a formatted notification card with facts and action buttons",
                parameters={
                    "title": "str (required) - Notification title",
                    "text": "str (required) - Notification text",
                    "facts": "list[dict] (optional) - List of key-value pairs [{'name': 'Key', 'value': 'Value'}]",
                    "actions": "list[dict] (optional) - List of action button definitions",
                    "color": "str (optional) - Theme color in hex"
                },
                returns="dict - Response data",
                examples=[
                    {"text": "Send notification with title {{title}}, text {{text}}, and facts {{facts_list}}", "code": "send_notification(title='{{title}}', text='{{text}}', facts={{facts_list}})"},
                    {"text": "Send notification with title {{title}}, text {{text}}, facts {{facts_list}}, actions {{actions_list}}, and color {{hex_color}}", "code": "send_notification(title='{{title}}', text='{{text}}', facts={{facts_list}}, actions={{actions_list}}, color='{{hex_color}}')"}
                ]
            ),
            MethodInfo(
                name="send_alert",
                description="Send an alert message with automatic severity-based styling",
                parameters={
                    "message": "str (required) - Alert message text",
                    "severity": "str (optional) - Alert level: info, warning, error, success (default warning)",
                    "title": "str (optional) - Custom alert title (default '{SEVERITY} Alert')"
                },
                returns="dict - Response data",
                examples=[
                    {"text": "Send warning alert {{message}}", "code": "send_alert(message='{{message}}', severity='warning')"},
                    {"text": "Send alert {{message}} with severity {{severity}} and title {{title}}", "code": "send_alert(message='{{message}}', severity='{{severity}}', title='{{title}}')"},
                    {"text": "Send error alert {{message}}", "code": "send_alert(message='{{message}}', severity='error')"}
                ]
            ),
            MethodInfo(
                name="send_status_card",
                description="Send a status update card with details and timestamp",
                parameters={
                    "title": "str (required) - Status card title",
                    "status": "str (required) - Status value (Success, Failed, Running, Pending)",
                    "details": "dict (required) - Dictionary of status details",
                    "timestamp": "str (optional) - Custom timestamp (default current time)"
                },
                returns="dict - Response data",
                examples=[
                    {"text": "Send status card with title {{title}}, status {{status}}, and details {{details_dict}}", "code": "send_status_card(title='{{title}}', status='{{status}}', details={{details_dict}})"},
                    {"text": "Send status card with title {{title}}, status {{status}}, details {{details_dict}}, and timestamp {{timestamp}}", "code": "send_status_card(title='{{title}}', status='{{status}}', details={{details_dict}}, timestamp='{{timestamp}}')"}
                ]
            ),
            MethodInfo(
                name="create_card_with_data_table",
                description="Create an adaptive card with a formatted data table",
                parameters={
                    "title": "str (required) - Card title",
                    "headers": "list[str] (required) - Table column headers",
                    "rows": "list[list[str]] (required) - Table data rows",
                    "max_rows": "int (optional) - Maximum rows to display (default 10)"
                },
                returns="dict - Adaptive card payload (use with send_adaptive_card)",
                examples=[
                    {"text": "Create data table card with title {{title}}, headers {{headers_list}}, and rows {{rows_list}}", "code": "create_card_with_data_table(title='{{title}}', headers={{headers_list}}, rows={{rows_list}})"},
                    {"text": "Create data table card with title {{title}}, headers {{headers_list}}, rows {{rows_list}}, and max_rows {{max_rows}}", "code": "create_card_with_data_table(title='{{title}}', headers={{headers_list}}, rows={{rows_list}}, max_rows={{max_rows}})"}
                ]
            ),
            MethodInfo(
                name="close",
                description="Close Teams module and cleanup HTTP session resources",
                parameters={},
                returns="None",
                examples=[
                    {"text": "Close Teams module", "code": "close()"}
                ]
            )
        ]

# Global instance
_teams_instance = None


def get_teams_module(**config) -> TeamsModule:
    """
    Get or create Teams module instance.

    Args:
        **config: Configuration parameters

    Returns:
        TeamsModule instance
    """
    global _teams_instance
    if _teams_instance is None:
        _teams_instance = TeamsModule(**config)
    return _teams_instance


# Example usage
if __name__ == "__main__":
    # Example with webhook
    teams = TeamsModule(
        webhook_url="https://your-webhook-url.webhook.office.com/..."
    )

    # Send simple message
    teams.send_message(
        title="Pipeline Completed",
        text="The daily ETL pipeline has completed successfully.",
        color="107C10"
    )

    # Send alert
    teams.send_alert(
        message="High CPU usage detected on server-01",
        severity="warning",
        title="System Alert"
    )

    # Send status card
    teams.send_status_card(
        title="Database Backup",
        status="Success",
        details={
            "Database": "production_db",
            "Size": "150 GB",
            "Duration": "45 minutes",
            "Location": "s3://backups/2025-01-20/"
        }
    )

    # Send notification with facts
    teams.send_notification(
        title="Sales Report",
        text="Daily sales summary",
        facts=[
            {"name": "Total Sales", "value": "$125,000"},
            {"name": "Orders", "value": "342"},
            {"name": "Average Order", "value": "$365"}
        ]
    )
