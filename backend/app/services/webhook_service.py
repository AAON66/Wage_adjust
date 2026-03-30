from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.webhook_delivery_log import WebhookDeliveryLog
from backend.app.models.webhook_endpoint import WebhookEndpoint

logger = logging.getLogger(__name__)

# Retry delays in seconds (exponential backoff)
_RETRY_DELAYS = [1, 5, 30]
_MAX_ATTEMPTS = 3
_DELIVERY_TIMEOUT = 10.0


class WebhookService:
    """Webhook registration, delivery, retry, and logging (per D-13, D-14)."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        *,
        url: str,
        description: str | None = None,
        events: list[str],
        created_by: str,
    ) -> WebhookEndpoint:
        """Register a webhook endpoint. Auto-generates HMAC signing secret."""
        endpoint = WebhookEndpoint(
            url=url,
            secret=secrets.token_hex(32),
            is_active=True,
            description=description,
            events=events,
            created_by=created_by,
        )
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        return endpoint

    def unregister(self, webhook_id: str) -> None:
        """Deactivate a webhook (is_active = False)."""
        endpoint = self.db.get(WebhookEndpoint, webhook_id)
        if endpoint is None:
            raise ValueError(f'Webhook not found: {webhook_id}')
        endpoint.is_active = False
        self.db.commit()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_endpoints(self, *, active_only: bool = True) -> list[WebhookEndpoint]:
        """List webhook endpoints."""
        query = select(WebhookEndpoint).order_by(WebhookEndpoint.created_at.desc())
        if active_only:
            query = query.where(WebhookEndpoint.is_active.is_(True))
        return list(self.db.scalars(query))

    def get_endpoint(self, webhook_id: str) -> WebhookEndpoint | None:
        """Get single webhook endpoint."""
        return self.db.get(WebhookEndpoint, webhook_id)

    def get_delivery_logs(self, webhook_id: str, *, limit: int = 50) -> list[WebhookDeliveryLog]:
        """Get delivery logs for a webhook."""
        return list(
            self.db.scalars(
                select(WebhookDeliveryLog)
                .where(WebhookDeliveryLog.webhook_id == webhook_id)
                .order_by(WebhookDeliveryLog.created_at.desc())
                .limit(limit)
            )
        )

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    def deliver(self, *, event_type: str, payload: dict) -> list[WebhookDeliveryLog]:
        """Deliver event to all active endpoints subscribing to this event_type.

        Signing: HMAC-SHA256(secret, json_body) -> X-Signature-256 header.
        Retry: up to 3 attempts with exponential backoff (1s / 5s / 30s).
        Each attempt creates a WebhookDeliveryLog entry.
        """
        endpoints = list(
            self.db.scalars(
                select(WebhookEndpoint).where(WebhookEndpoint.is_active.is_(True))
            )
        )
        # Filter endpoints that subscribe to this event type
        matching = [ep for ep in endpoints if event_type in (ep.events or [])]

        all_logs: list[WebhookDeliveryLog] = []
        body = json.dumps(payload, default=str, ensure_ascii=False)

        for endpoint in matching:
            log = self._deliver_to_endpoint(endpoint, event_type=event_type, body=body, payload=payload)
            all_logs.append(log)

        return all_logs

    def _deliver_to_endpoint(
        self,
        endpoint: WebhookEndpoint,
        *,
        event_type: str,
        body: str,
        payload: dict,
    ) -> WebhookDeliveryLog:
        """Deliver to a single endpoint with retries. Returns the final delivery log."""
        signature = hmac.new(
            endpoint.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            'Content-Type': 'application/json',
            'X-Signature-256': f'sha256={signature}',
            'X-Webhook-Event': event_type,
        }

        last_log: WebhookDeliveryLog | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            log = WebhookDeliveryLog(
                webhook_id=endpoint.id,
                event_type=event_type,
                payload=payload,
                attempt=attempt,
                success=False,
            )

            try:
                with httpx.Client(timeout=_DELIVERY_TIMEOUT) as client:
                    response = client.post(endpoint.url, content=body, headers=headers)
                log.response_status = response.status_code
                log.response_body = response.text[:2000] if response.text else None

                if 200 <= response.status_code < 300:
                    log.success = True
                    self.db.add(log)
                    self.db.commit()
                    self.db.refresh(log)
                    return log

                log.error_message = f'HTTP {response.status_code}'
            except Exception as exc:
                log.error_message = str(exc)[:500]
                logger.warning(
                    'Webhook delivery failed (attempt %d/%d) to %s: %s',
                    attempt, _MAX_ATTEMPTS, endpoint.url, exc,
                )

            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            last_log = log

            # Wait before retry (skip wait after last attempt)
            if attempt < _MAX_ATTEMPTS:
                delay = _RETRY_DELAYS[attempt - 1] if attempt - 1 < len(_RETRY_DELAYS) else _RETRY_DELAYS[-1]
                time.sleep(delay)

        return last_log  # type: ignore[return-value]
