from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol


class ImageHost(Protocol):
    async def upload(self, path: Path) -> str:
        ...


class LocalPublicImageHost:
    def __init__(self, public_base_url: str, public_dir: Path = Path("artifacts/public/cards")) -> None:
        self.public_base_url = public_base_url.rstrip("/")
        self.public_dir = public_dir

    async def upload(self, path: Path) -> str:
        source = Path(path)
        self.public_dir.mkdir(parents=True, exist_ok=True)
        target = self.public_dir / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        return f"{self.public_base_url}/{target.name}"


class DisabledImageHost:
    async def upload(self, path: Path) -> str:
        raise RuntimeError("图片公网地址未配置。请设置 IMAGE_PUBLIC_BASE_URL。")


def build_image_host(public_base_url: str | None, public_dir: str | None = None) -> ImageHost:
    if not public_base_url:
        return DisabledImageHost()
    return LocalPublicImageHost(public_base_url, Path(public_dir or "artifacts/public/cards"))
