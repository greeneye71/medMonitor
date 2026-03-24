"""IMAP service — monitors inbox for operator responses to alerts."""

import asyncio
import email
import imaplib
import logging
import re
from functools import partial
from typing import Any

from backend.services.config_service import config_service

logger = logging.getLogger(__name__)

# Command patterns operators can send by replying to alert emails
COMMANDS = {
    r"^ACK\b": "ack",
    r"^MUTE\s+(\d+)h?\b": "mute",
    r"^ESCALATE\b": "escalate",
    r"^STATUS\b": "status",
}


class ImapService:
    """Polls IMAP inbox for operator responses to alert emails."""

    def __init__(self) -> None:
        self._callbacks: dict[str, Any] = {}

    def on_command(self, command: str, callback) -> None:
        """Register a callback for a specific command (ack, mute, escalate, status)."""
        self._callbacks[command] = callback

    async def check_inbox(self) -> list[dict[str, Any]]:
        """Check IMAP inbox for new responses. Returns parsed commands."""
        config = config_service.get_config()
        imap_config = config.email.imap

        if not imap_config.host or not imap_config.user:
            return []

        # Run blocking IMAP operations in a thread to avoid blocking the event loop
        raw_commands = await asyncio.to_thread(
            self._fetch_commands_sync, imap_config
        )

        # Execute async callbacks in the event loop
        results = []
        for command in raw_commands:
            results.append(command)
            cb = self._callbacks.get(command["type"])
            if cb:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(command)
                    else:
                        cb(command)
                except Exception as e:
                    logger.error("Command callback failed: %s", e)

        return results

    def _fetch_commands_sync(self, imap_config) -> list[dict[str, Any]]:
        """Synchronous IMAP fetch — runs in a thread."""
        results = []
        try:
            if imap_config.use_ssl:
                conn = imaplib.IMAP4_SSL(imap_config.host, imap_config.port)
            else:
                conn = imaplib.IMAP4(imap_config.host, imap_config.port)

            conn.login(imap_config.user, imap_config.password)
            conn.select(imap_config.folder)

            status, message_ids = conn.search(None, '(UNSEEN SUBJECT "medMonitor")')
            if status != "OK" or not message_ids[0]:
                conn.logout()
                return []

            for msg_id in message_ids[0].split():
                status, msg_data = conn.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                body = self._extract_body(msg)
                if not body:
                    continue

                first_line = body.strip().split("\n")[0].strip().upper()
                command = self._parse_command(first_line)

                if command:
                    command["from"] = msg.get("From", "")
                    command["subject"] = msg.get("Subject", "")
                    results.append(command)
                    logger.info("IMAP command: %s from %s", command["type"], command["from"])
                    conn.store(msg_id, "+FLAGS", "\\Seen")

            conn.logout()

        except Exception as e:
            logger.error("IMAP check failed: %s", e)

        return results

    @staticmethod
    def _extract_body(msg) -> str:
        """Extract plain text body from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    return part.get_payload(decode=True).decode(charset, errors="replace")
        else:
            charset = msg.get_content_charset() or "utf-8"
            return msg.get_payload(decode=True).decode(charset, errors="replace")
        return ""

    @staticmethod
    def _parse_command(text: str) -> dict[str, Any] | None:
        """Parse operator command from text."""
        for pattern, cmd_type in COMMANDS.items():
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                result = {"type": cmd_type}
                if cmd_type == "mute" and match.groups():
                    result["hours"] = int(match.group(1))
                return result
        return None


# Singleton
imap_service = ImapService()
