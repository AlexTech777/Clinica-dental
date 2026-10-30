import logging
from datetime import datetime

log = logging.getLogger(__name__)


class WhatsAppService:
    """Adaptador reemplazable: Twilio ahora, posible Meta Cloud API después."""
    def __init__(self, account_sid=None, auth_token=None, from_number=None, dry_run=True):
        self.account_sid, self.auth_token = account_sid, auth_token
        self.from_number, self.dry_run = from_number, dry_run

    @property
    def configured(self):
        return bool(self.account_sid and self.auth_token and self.from_number)

    def send(self, to: str, body: str, idempotency_key: str | None = None):
        if self.dry_run or not self.configured:
            log.info("[DRY_RUN] WhatsApp hacia %s | clave=%s | mensaje=%s", to, idempotency_key, body)
            return {"sid": f"dry-{idempotency_key or datetime.now().timestamp()}", "dry_run": True}
        from twilio.rest import Client
        message = Client(self.account_sid, self.auth_token).messages.create(
            from_=f"whatsapp:{self.from_number.removeprefix('whatsapp:')}",
            to=f"whatsapp:{to.removeprefix('whatsapp:')}", body=body,
        )
        return {"sid": message.sid, "dry_run": False}

    @staticmethod
    def validate_request(auth_token: str, signature: str, url: str, params: dict) -> bool:
        from twilio.request_validator import RequestValidator
        return RequestValidator(auth_token).validate(url, params, signature)
