import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UserContext:
    user_key: str | None = None


class BindingStore:
    def __init__(self, path: Path | str = "data/bindings.json") -> None:
        self.path = Path(path)

    def bind(self, user_key: str, steam_id: str) -> None:
        data = self._load()
        data[user_key] = {"steam_id": steam_id}
        self._save(data)

    def unbind(self, user_key: str) -> bool:
        data = self._load()
        existed = user_key in data
        data.pop(user_key, None)
        self._save(data)
        return existed

    def get_steam_id(self, user_key: str | None) -> str | None:
        if not user_key:
            return None
        value = self._load().get(user_key)
        if not value:
            return None
        return value.get("steam_id")

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_steam_id(value: str) -> str:
    steam_id = value.strip()
    if not steam_id.isdigit() or len(steam_id) < 16:
        raise ValueError("请输入 SteamID64，例如：/bind 76561198157609957")
    return steam_id
