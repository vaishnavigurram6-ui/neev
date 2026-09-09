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
    # The one password every demo account shares. A gate, not a secret: it is
    # printed in the runbook so a judge can sign in. It exists because the
    # deployed URL is public and sign-in used to accept any ten-digit number,
    # which meant anyone who found the link could start analyses that cost
    # money. Override it on a deployment to keep it out of a public repo.
    neev_demo_password: str = "neev-demo"
    # How many analyses one loan may start in a rolling 24 hours, and how many
    # the whole service may. A live analysis costs real money — about Rs 3.81 —
    # and the deployed demo is a public URL whose sign-in accepts any ten-digit
    # number. On the Gemini free tier Google's own 20-requests-a-day cap is the
    # backstop; on the paid tier there is none, so this is it. Generous enough
    # that a judge working through the flow never meets it.
    neev_max_analyses_per_loan_per_day: int = 12
    neev_max_analyses_per_day: int = 60
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
            "Live mode requires NEEV_ALLOW_BILLED_CALLS=1. Setting NEEV_MODE=live "
            "alone is not enough, on purpose: it is what stops a stray mode in a "
            "shell from spending credit. See CLAUDE.md."
        )
