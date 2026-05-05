from __future__ import annotations

from dataclasses import dataclass

from app.domains.email.application.port.oauth_token_storage_port import OAuthTokenStoragePort
from app.domains.email.application.usecase.start_oauth import OAuthFlowProviderPort
from app.domains.email.domain.value_object.email_source import EmailSource
from app.domains.email.domain.value_object.oauth_token import OAuthToken


@dataclass(slots=True)
class CompleteOAuth:
    flow: OAuthFlowProviderPort
    storage: OAuthTokenStoragePort
    source: EmailSource = EmailSource.GMAIL

    async def execute(self, *, code: str, state: str | None, user_id: int | None) -> OAuthToken:
        exchanged = await self.flow.exchange_code_for_token(code=code, state=state)
        token = OAuthToken(
            source=str(self.source),
            account=exchanged.account_email,
            access_token=exchanged.access_token,
            refresh_token=exchanged.refresh_token,
            expires_at=exchanged.expires_at,  # type: ignore[arg-type]
            scopes=exchanged.scopes,
            user_id=user_id,
        )
        await self.storage.save(token)
        return token
