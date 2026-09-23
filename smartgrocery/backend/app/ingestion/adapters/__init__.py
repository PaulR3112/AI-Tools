from app.ingestion.adapters.base import Adapter, FetchResult
from app.ingestion.adapters.manual import ManualAdapter

ADAPTERS: dict[str, type[Adapter]] = {"manual": ManualAdapter}


def get_adapter(name: str) -> Adapter:
    try:
        return ADAPTERS[name]()
    except KeyError:
        raise ValueError(f"Neznámy adaptér: {name}") from None


__all__ = ["ADAPTERS", "Adapter", "FetchResult", "get_adapter"]
