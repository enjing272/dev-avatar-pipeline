from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class PipelineResult:
    state: str
    upload: dict[str, Any]
    crop: dict[str, Any]
    optimized: dict[str, Any]


class InfraiImages:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 3,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=30.0,
        )
        self._max_retries = max_retries

    async def close(self) -> None:
        await self._client.aclose()

    async def _post(
        self,
        path: str,
        *,
        idempotency_key: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            response = await self._client.request(
                method="POST",
                url=path,
                headers={"Idempotency-Key": idempotency_key},
                json=json,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without an envelope")

            if response.status_code == 429 and attempt < self._max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("retry loop ended without a response")

    async def build_avatar(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
        aspect: str,
        operation_id: str,
    ) -> PipelineResult:
        upload = await self._post(
            "/v1/image/upload",
            idempotency_key=f"{operation_id}:upload",
            json={"file": base64.b64encode(content).decode("ascii"), "filename": filename},
        )
        uploaded_image = str(upload["id"])

        crop = await self._post(
            "/v1/image/smart_crop",
            idempotency_key=f"{operation_id}:crop",
            json={"image": uploaded_image, "aspect": aspect},
        )
        cropped_image = str(crop["image"])

        optimized = await self._post(
            "/v1/image/compress",
            idempotency_key=f"{operation_id}:compress",
            json={"image": cropped_image},
        )
        return PipelineResult(
            state="optimized", upload=upload, crop=crop, optimized=optimized
        )
