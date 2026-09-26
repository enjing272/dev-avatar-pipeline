from __future__ import annotations

import os
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .infrai_images import InfraiError, InfraiImages


class AvatarResponse(BaseModel):
    operation_id: str
    state: str
    upload: dict[str, Any]
    crop: dict[str, Any]
    optimized: dict[str, Any]


class DiagnosticResponse(BaseModel):
    operation_id: str
    stage: str
    code: str
    message: str


class AvatarRequest(BaseModel):
    aspect: str = Field(default="1:1", pattern=r"^\d+:\d+$")


def image_client() -> InfraiImages:
    api_key = os.environ["INFRAI_API_KEY"]
    return InfraiImages(api_key)


app = FastAPI(title="Developer avatar pipeline")


@app.post(
    "/avatars",
    response_model=AvatarResponse,
    responses={400: {"model": DiagnosticResponse}, 422: {"model": DiagnosticResponse}},
)
async def create_avatar(
    file: Annotated[UploadFile, File()],
    aspect: Annotated[str, Form()] = "1:1",
    idempotency_key: Annotated[str | None, Header()] = None,
    client: InfraiImages = Depends(image_client),
) -> AvatarResponse:
    request = AvatarRequest(aspect=aspect)
    operation_id = idempotency_key or str(uuid4())
    try:
        result = await client.build_avatar(
            content=await file.read(),
            filename=file.filename or "avatar",
            content_type=file.content_type or "application/octet-stream",
            aspect=request.aspect,
            operation_id=operation_id,
        )
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=status,
            detail=DiagnosticResponse(
                operation_id=operation_id,
                stage="image_processing",
                code=exc.code,
                message=str(exc),
            ).model_dump(),
        ) from exc
    finally:
        await client.close()

    return AvatarResponse(operation_id=operation_id, **result.__dict__)
