from __future__ import annotations

import base64
import json

import httpx
import pytest

from avatar_pipeline.infrai_images import InfraiImages


@pytest.mark.asyncio
async def test_pipeline_uses_each_previous_image_and_finishes_optimized() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/image/upload":
            assert request.headers["content-type"] == "application/json"
            assert json.loads(request.content) == {
                "file": base64.b64encode(b"image bytes").decode("ascii"),
                "filename": "ada.png",
            }
            data = {"id": "uploaded-42"}
        elif request.url.path == "/v1/image/smart_crop":
            assert json.loads(request.content) == {
                "image": "uploaded-42",
                "aspect": "1:1",
            }
            data = {"image": "cropped-42"}
        else:
            assert request.url.path == "/v1/image/compress"
            assert json.loads(request.content) == {"image": "cropped-42"}
            data = {"image": "avatar-42", "bytes": 18432}
        return httpx.Response(200, json={"ok": True, "data": data})

    client = InfraiImages("test-key", transport=httpx.MockTransport(handler))
    try:
        result = await client.build_avatar(
            content=b"image bytes",
            filename="ada.png",
            content_type="image/png",
            aspect="1:1",
            operation_id="profile-42",
        )
    finally:
        await client.close()

    assert result.state == "optimized"
    assert result.optimized["image"] == "avatar-42"
    assert [request.method for request in requests] == ["POST", "POST", "POST"]
    assert [request.headers["Idempotency-Key"] for request in requests] == [
        "profile-42:upload",
        "profile-42:crop",
        "profile-42:compress",
    ]
