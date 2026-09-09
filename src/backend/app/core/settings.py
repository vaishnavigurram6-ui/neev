"""Application settings, and the fence that keeps this build from spending money.

NEEV_MODE selects which PipelineRunner the factory returns. It defaults to
"fixture" and falls back to "fixture" for any unrecognized value, so a typo
cannot select the live path. Live mode additionally requires an explicit
NEEV_ALLOW_BILLED_CALLS=1; without it, constructing the live runner raises.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Mode = Literal["fixture", "live"]


class BilledCallsNotPermitted(RuntimeError):
    """Raised when something tries to use the live, billed pipeline path."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    neev_mode: Mode = "fixture"
    neev_allow_billed_calls: bool = False
    database_url: str = "sqlite:///./neev.db"
    artifact_dir: str = "./artifacts"
    # Explicit sandbox opt-in. No identity provider is implemented yet.
    neev_demo_auth: bool = False
    # Signs the sandbox session cookie. Empty means "a fresh random key per
    # process", which is the safe default for local work but signs everyone out
    # on restart — and on Cloud Run at --min-instances 0 the instance is
    # recycled after about fifteen idle minutes, so a visitor who reads a page,
    # steps away and comes back is bounced to /login through no fault of their
    # own. Set it on a deployment and sessions survive a cold start.
    neev_session_secret: str = ""
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("neev_mode", mode="before")
    @classmethod
    def _unknown_mode_is_fixture(cls, value: object) -> object:
        if value is None:
            return "fixture"
        if isinstance(value, str) and value.strip().lower() not in ("fixture", "live"):
            return "fixture"
        return value.strip().lower() if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()


def assert_billed_calls_permitted(settings: Settings | None = None) -> None:
    """Gate every billed code path through this.

    Raises BilledCallsNotPermitted unless NEEV_ALLOW_BILLED_CALLS is set. The
    message names the variable so the failure is self-explanatory.
    """
    settings = settings or get_settings()
    if not settings.neev_allow_billed_calls:
        raise BilledCallsNotPermitted(
            "Live mode requires NEEV_ALLOW_BILLED_CALLS=1. It is deliberately "
            "unset: this build must consume no Google credits. See CLAUDE.md."
        )
