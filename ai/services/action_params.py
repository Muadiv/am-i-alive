from __future__ import annotations


def get_str_param(params: dict[str, object], key: str) -> str:
    value = params.get(key)
    return value if isinstance(value, str) else ""


def get_int_param(params: dict[str, object], key: str, default: int) -> int:
    value = params.get(key)
    return value if isinstance(value, int) else default


def get_str_list_param(params: dict[str, object], key: str) -> list[str]:
    value = params.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []
