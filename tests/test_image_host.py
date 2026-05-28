import pytest

from ba_monitor.image_host import DisabledImageHost, LocalPublicImageHost


@pytest.mark.asyncio
async def test_local_public_image_host_copies_file_and_returns_url(tmp_path) -> None:
    source = tmp_path / "card.png"
    public_dir = tmp_path / "public"
    source.write_bytes(b"png")

    url = await LocalPublicImageHost("https://example.com/cards", public_dir).upload(source)

    assert url == "https://example.com/cards/card.png"
    assert (public_dir / "card.png").read_bytes() == b"png"


@pytest.mark.asyncio
async def test_disabled_image_host_fails_with_clear_message(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="IMAGE_PUBLIC_BASE_URL"):
        await DisabledImageHost().upload(tmp_path / "card.png")
