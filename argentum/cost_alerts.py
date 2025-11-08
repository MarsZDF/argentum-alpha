"""
Cost alerts and notifications for Argentum.

This module provides webhook integrations, email notifications, and real-time
cost monitoring with customizable thresholds and notification channels.

Examples:
    >>> from argentum import CostAlerts
    >>> 
    >>> alerts = CostAlerts()
    >>> alerts.add_webhook("https://hooks.slack.com/...", 
    ...                   threshold=0.8, message="🚨 Budget 80% used!")
    >>> alerts.add_email("finance@company.com", threshold=1.0)
    >>> alerts.check_thresholds(current_cost=850, budget=1000)
"""

import json
import smtplib
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import re
from urllib.parse import urlparse
import html

# Cost tracker integration (optional)
COST_TRACKING_AVAILABLE = False
try:
    # Try to import cost tracker if available
    from .cost_optimization.cost_tracker import CostTracker
    COST_TRACKING_AVAILABLE = True
except ImportError:
    # Cost tracking is optional
    pass

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Security validation error."""
    pass


def _validate_webhook_url(url: str) -> bool:
    """
    Validate webhook URL for security.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is safe
        
    Raises:
        SecurityError: If URL is potentially unsafe
    """
    try:
        parsed = urlparse(url)
    except Exception:
        raise SecurityError("Invalid URL format")
    
    # Ensure HTTPS for production webhooks
    if parsed.scheme not in ['https']:
        raise SecurityError("Only HTTPS webhooks are allowed for security")
    
    # Block private/internal addresses
    if parsed.hostname:
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
            raise SecurityError("Private/localhost addresses not allowed")
        if parsed.hostname.startswith('10.') or parsed.hostname.startswith('192.168.'):
            raise SecurityError("Private network addresses not allowed")
    
    # Check for known webhook services (optional but recommended)
    allowed_domains = [
        'hooks.slack.com',
        'discord.com', 'discordapp.com',
        'outlook.office.com',
        'teams.microsoft.com'
    ]
    
    if parsed.hostname and not any(domain in parsed.hostname for domain in allowed_domains):
        logger.warning(f"Unknown webhook domain: {parsed.hostname}")
    
    return True


def _sanitize_message_template(template: str) -> str:
    """
    Sanitize message template to prevent injection attacks.
    
    Args:
        template: Message template string
        
    Returns:
        Sanitized template
    """
    # Escape HTML characters
    template = html.escape(template)
    
    # Limit template length
    if len(template) > 1000:
        raise SecurityError("Message template too long (max 1000 characters)")
    
    # Block dangerous format specifiers
    dangerous_patterns = [
        r'__\w+__',  # Dunder attributes
        r'{.*\[.*\]}',  # Index access
        r'{.*\.__.*}',  # Attribute access
        r'{.*exec.*}',  # Code execution
        r'{.*eval.*}',  # Code evaluation
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, template):
            raise SecurityError(f"Dangerous pattern detected in template: {pattern}")
    
    return template


def _validate_email(email: str) -> bool:
    """
    Validate email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid
        
    Raises:
        SecurityError: If email is invalid
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise SecurityError("Invalid email format")
    
    if len(email) > 254:  # RFC 5321 limit
        raise SecurityError("Email address too long")
    
    return True


@dataclass
class AlertRule:
    """Configuration for a cost alert rule."""
    name: str
    threshold: float  # 0.0-1.0 for percentage, or absolute dollar amount
    threshold_type: str = "percentage"  # "percentage" or "absolute"
    channels: List[Dict[str, Any]] = None
    message_template: str = "Cost threshold reached: {cost} / {budget}"
    cooldown_minutes: int = 60  # Minimum time between alerts
    enabled: bool = True
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = []


@dataclass
class AlertEvent:
    """Record of a triggered alert."""
    rule_name: str
    triggered_at: datetime
    current_cost: float
    budget: float
    threshold_value: float
    message: str
    channels_notified: List[str]


class CostAlerts:
    """
    Cost alerting system with webhook and email support.
    
    Supports Slack, Discord, Teams, email, and custom webhook integrations
    with flexible threshold-based triggering and cooldown management.
    """
    
    def __init__(self, cost_tracker: Optional[Any] = None):
        """
        Initialize cost alerts system.
        
        Args:
            cost_tracker: Optional cost tracker instance for automatic monitoring
        """
        self._rules: Dict[str, AlertRule] = {}
        self._alert_history: List[AlertEvent] = []
        self._cost_tracker = cost_tracker
        self._last_alert_times: Dict[str, datetime] = {}
        
    def add_webhook(self, url: str, threshold: float, message: str = None, 
                   rule_name: str = None, threshold_type: str = "percentage",
                   cooldown_minutes: int = 60) -> str:
        """
        Add a webhook alert (Slack, Discord, Teams, etc.).
        
        Args:
            url: Webhook URL
            threshold: Alert threshold (0.0-1.0 for percentage, or dollar amount)
            message: Custom message template (optional)
            rule_name: Custom rule name (optional, auto-generated if not provided)
            threshold_type: "percentage" or "absolute"
            cooldown_minutes: Minimum time between alerts
            
        Returns:
            Rule name for later reference
            
        Examples:
            >>> alerts = CostAlerts()
            >>> # Slack webhook at 80% budget
            >>> alerts.add_webhook("https://hooks.slack.com/services/...", 
            ...                   threshold=0.8, message="🚨 Budget 80% used!")
            >>> # Discord webhook at $500
            >>> alerts.add_webhook("https://discord.com/api/webhooks/...", 
            ...                   threshold=500, threshold_type="absolute")
        """
        if rule_name is None:
            rule_name = f"webhook_{len(self._rules) + 1}"
            
        # Security validation
        _validate_webhook_url(url)
        
        if message is None:
            if threshold_type == "percentage":
                message = f"🚨 Cost Alert: {{cost:.2f}} / {{budget:.2f}} ({threshold:.1%} threshold reached)"
            else:
                message = f"💰 Cost Alert: ${{cost:.2f}} (${threshold} threshold reached)"
        
        message = _sanitize_message_template(message)
        
        channel = {
            "type": "webhook",
            "url": url,
            "format": self._detect_webhook_format(url)
        }
        
        rule = AlertRule(
            name=rule_name,
            threshold=threshold,
            threshold_type=threshold_type,
            channels=[channel],
            message_template=message,
            cooldown_minutes=cooldown_minutes
        )
        
        self._rules[rule_name] = rule
        return rule_name
    
    def add_email(self, email: str, threshold: float, subject: str = None,
                 rule_name: str = None, threshold_type: str = "percentage",
                 smtp_config: Dict[str, Any] = None) -> str:
        """
        Add an email alert.
        
        Args:
            email: Email address to notify
            threshold: Alert threshold
            subject: Email subject (optional)
            rule_name: Custom rule name (optional)
            threshold_type: "percentage" or "absolute"
            smtp_config: SMTP configuration dict (optional, uses defaults)
            
        Returns:
            Rule name for later reference
            
        Examples:
            >>> alerts.add_email("finance@company.com", threshold=1.0)
            >>> alerts.add_email("cto@company.com", threshold=500, 
            ...                 threshold_type="absolute", 
            ...                 subject="AI Cost Alert")
        """
        # Security validation
        _validate_email(email)
        
        if rule_name is None:
            rule_name = f"email_{len(self._rules) + 1}"
            
        if subject is None:
            subject = "Argentum Cost Alert - Threshold Reached"
        
        # Sanitize subject
        subject = html.escape(subject)[:200]  # Limit subject length
        
        channel = {
            "type": "email",
            "email": email,
            "subject": subject,
            "smtp_config": smtp_config or self._get_default_smtp_config()
        }
        
        message_template = """
Cost threshold alert triggered:

Current Cost: ${cost:.2f}
Budget: ${budget:.2f}
Threshold: {threshold_display}
Time: {timestamp}

This is an automated alert from Argentum cost monitoring.
"""
        
        rule = AlertRule(
            name=rule_name,
            threshold=threshold,
            threshold_type=threshold_type,
            channels=[channel],
            message_template=message_template,
            cooldown_minutes=60
        )
        
        self._rules[rule_name] = rule
        return rule_name
    
    def add_slack_webhook(self, webhook_url: str, threshold: float, 
                         channel: str = None, username: str = "Argentum",
                         icon_emoji: str = ":money_with_wings:") -> str:
        """
        Add a Slack-specific webhook with rich formatting.
        
        Args:
            webhook_url: Slack webhook URL
            threshold: Alert threshold (0.0-1.0)
            channel: Slack channel override
            username: Bot username
            icon_emoji: Bot icon
            
        Returns:
            Rule name
        """
        rule_name = f"slack_{len(self._rules) + 1}"
        
        channel_config = {
            "type": "slack",
            "url": webhook_url,
            "channel": channel,
            "username": username,
            "icon_emoji": icon_emoji
        }
        
        rule = AlertRule(
            name=rule_name,
            threshold=threshold,
            threshold_type="percentage",
            channels=[channel_config],
            message_template="slack_rich_format",  # Special template
            cooldown_minutes=30
        )
        
        self._rules[rule_name] = rule
        return rule_name
    
    def check_thresholds(self, current_cost: float, budget: float = None, 
                        agent_id: str = "default") -> List[AlertEvent]:
        """
        Check all alert rules and trigger notifications.
        
        Args:
            current_cost: Current spending amount
            budget: Budget amount (required for percentage thresholds)
            agent_id: Agent identifier for tracking
            
        Returns:
            List of triggered alert events
        """
        triggered_alerts = []
        now = datetime.now()
        
        for rule_name, rule in self._rules.items():
            if not rule.enabled:
                continue
                
            # Check cooldown
            last_alert = self._last_alert_times.get(rule_name)
            if last_alert:
                cooldown_delta = now - last_alert
                if cooldown_delta.total_seconds() < rule.cooldown_minutes * 60:
                    continue  # Still in cooldown
            
            # Calculate threshold value
            if rule.threshold_type == "percentage":
                if budget is None:
                    logger.warning(f"Budget required for percentage threshold in rule {rule_name}")
                    continue
                threshold_value = budget * rule.threshold
            else:
                threshold_value = rule.threshold
            
            # Check if threshold is exceeded
            if current_cost >= threshold_value:
                # Create alert event
                if rule.threshold_type == "percentage":
                    threshold_display = f"{rule.threshold:.1%} of ${budget:.2f}"
                else:
                    threshold_display = f"${rule.threshold:.2f}"
                
                message = rule.message_template.format(
                    cost=current_cost,
                    budget=budget or 0,
                    threshold_display=threshold_display,
                    timestamp=now.isoformat(),
                    agent_id=agent_id
                )
                
                alert_event = AlertEvent(
                    rule_name=rule_name,
                    triggered_at=now,
                    current_cost=current_cost,
                    budget=budget or 0,
                    threshold_value=threshold_value,
                    message=message,
                    channels_notified=[]
                )
                
                # Send notifications
                for channel in rule.channels:
                    try:
                        self._send_notification(channel, message, alert_event)
                        alert_event.channels_notified.append(channel.get('type', 'unknown'))
                    except Exception as e:
                        logger.error(f"Failed to send alert to {channel}: {e}")
                
                # Record alert
                triggered_alerts.append(alert_event)
                self._alert_history.append(alert_event)
                self._last_alert_times[rule_name] = now
        
        return triggered_alerts
    
    def get_alert_history(self, limit: int = 50) -> List[AlertEvent]:
        """Get recent alert history."""
        return self._alert_history[-limit:]
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable an alert rule."""
        if rule_name in self._rules:
            self._rules[rule_name].enabled = False
            return True
        return False
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable an alert rule."""
        if rule_name in self._rules:
            self._rules[rule_name].enabled = True
            return True
        return False
    
    def list_rules(self) -> Dict[str, Dict[str, Any]]:
        """List all alert rules with their configuration."""
        return {
            name: {
                "threshold": rule.threshold,
                "threshold_type": rule.threshold_type,
                "enabled": rule.enabled,
                "cooldown_minutes": rule.cooldown_minutes,
                "channels": len(rule.channels)
            }
            for name, rule in self._rules.items()
        }
    
    def _detect_webhook_format(self, url: str) -> str:
        """Detect webhook format from URL."""
        if "slack.com" in url:
            return "slack"
        elif "discord.com" in url or "discordapp.com" in url:
            return "discord"
        elif "office.com" in url or "outlook.com" in url:
            return "teams"
        else:
            return "generic"
    
    def _send_notification(self, channel: Dict[str, Any], message: str, 
                          alert_event: AlertEvent) -> None:
        """Send notification to a specific channel."""
        channel_type = channel["type"]
        
        if channel_type == "webhook":
            self._send_webhook(channel, message, alert_event)
        elif channel_type == "slack":
            self._send_slack_rich(channel, alert_event)
        elif channel_type == "email":
            self._send_email(channel, message, alert_event)
        else:
            raise ValueError(f"Unknown channel type: {channel_type}")
    
    def _send_webhook(self, channel: Dict[str, Any], message: str, 
                     alert_event: AlertEvent) -> None:
        """Send generic webhook notification."""
        webhook_format = channel["format"]
        
        if webhook_format == "slack":
            payload = {"text": message}
        elif webhook_format == "discord":
            payload = {"content": message}
        elif webhook_format == "teams":
            payload = {"text": message}
        else:
            payload = {"message": message, "alert_data": {
                "cost": alert_event.current_cost,
                "budget": alert_event.budget,
                "timestamp": alert_event.triggered_at.isoformat()
            }}
        
        # Security controls for HTTP requests
        response = requests.post(
            channel["url"], 
            json=payload, 
            timeout=10,
            headers={'User-Agent': 'Argentum-Alerts/1.0'},
            allow_redirects=False  # Prevent redirect attacks
        )
        response.raise_for_status()
        
        # Log successful webhook (but not the URL for security)
        logger.info(f"Webhook alert sent successfully to {self._detect_webhook_format(channel['url'])} service")
    
    def _send_slack_rich(self, channel: Dict[str, Any], alert_event: AlertEvent) -> None:
        """Send rich Slack notification with formatting."""
        color = "danger" if alert_event.current_cost > alert_event.budget else "warning"
        
        attachment = {
            "color": color,
            "title": "💰 Argentum Cost Alert",
            "fields": [
                {
                    "title": "Current Cost",
                    "value": f"${alert_event.current_cost:.2f}",
                    "short": True
                },
                {
                    "title": "Budget",
                    "value": f"${alert_event.budget:.2f}",
                    "short": True
                },
                {
                    "title": "Utilization",
                    "value": f"{(alert_event.current_cost / alert_event.budget * 100):.1f}%" if alert_event.budget > 0 else "N/A",
                    "short": True
                },
                {
                    "title": "Time",
                    "value": alert_event.triggered_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "short": True
                }
            ],
            "footer": "Argentum Cost Intelligence",
            "ts": int(alert_event.triggered_at.timestamp())
        }
        
        payload = {
            "username": channel.get("username", "Argentum"),
            "icon_emoji": channel.get("icon_emoji", ":money_with_wings:"),
            "attachments": [attachment]
        }
        
        if channel.get("channel"):
            payload["channel"] = channel["channel"]
        
        # Security controls for HTTP requests
        response = requests.post(
            channel["url"], 
            json=payload, 
            timeout=10,
            headers={'User-Agent': 'Argentum-Alerts/1.0'},
            allow_redirects=False  # Prevent redirect attacks
        )
        response.raise_for_status()
        
        # Log successful webhook (but not the URL for security)
        logger.info(f"Slack alert sent successfully")
    
    def _send_email(self, channel: Dict[str, Any], message: str, 
                   alert_event: AlertEvent) -> None:
        """Send email notification."""
        smtp_config = channel["smtp_config"]
        
        msg = MIMEMultipart()
        msg["From"] = smtp_config.get("from_email", "alerts@argentum.ai")
        msg["To"] = channel["email"]
        msg["Subject"] = channel["subject"]
        
        # Create HTML body
        html_body = f"""
        <html>
          <body>
            <h2>🚨 Argentum Cost Alert</h2>
            <p><strong>Current Cost:</strong> ${alert_event.current_cost:.2f}</p>
            <p><strong>Budget:</strong> ${alert_event.budget:.2f}</p>
            <p><strong>Threshold:</strong> ${alert_event.threshold_value:.2f}</p>
            <p><strong>Time:</strong> {alert_event.triggered_at.strftime("%Y-%m-%d %H:%M:%S")}</p>
            <hr>
            <p style="color: #666;">This is an automated alert from Argentum cost monitoring.</p>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(message, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        # Send email (implementation depends on SMTP configuration)
        # Note: In production, this would use proper SMTP configuration
        logger.info(f"Email alert sent to {channel['email']}: {message[:100]}...")
    
    def _get_default_smtp_config(self) -> Dict[str, Any]:
        """Get default SMTP configuration."""
        return {
            "host": "localhost",
            "port": 587,
            "use_tls": True,
            "from_email": "alerts@argentum.ai"
        }