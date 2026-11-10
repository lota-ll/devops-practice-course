from __future__ import annotations

from ..config import Settings
from .base import BlockedError, Chain, ChainError, ChainOffer
from .fora import Fora
from .novus import Novus
from .silpo import Silpo

__all__ = ["BlockedError", "Chain", "ChainError", "ChainOffer", "build_chains"]


def build_chains(settings: Settings) -> dict[str, Chain]:
    available: dict[str, Chain] = {
        "silpo": Silpo(settings.silpo_api, settings.silpo_branch),
        "fora": Fora(settings.fora_api, settings.fora_filial),
        "novus": Novus(settings.novus_api, settings.novus_store),
    }
    unknown = set(settings.enabled_chains) - set(available)
    if unknown:
        raise ValueError(f"unknown chains in ENABLED_CHAINS: {sorted(unknown)}")
    return {name: available[name] for name in settings.enabled_chains}
