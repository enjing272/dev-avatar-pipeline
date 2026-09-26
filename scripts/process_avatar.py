from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import os
from pathlib import Path

from avatar_pipeline.infrai_images import InfraiImages


async def run(path: Path, aspect: str, operation_id: str) -> None:
    client = InfraiImages(os.environ["INFRAI_API_KEY"])
    try:
        result = await client.build_avatar(
            content=path.read_bytes(),
            filename=path.name,
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            aspect=aspect,
            operation_id=operation_id,
        )
        print(json.dumps(result.__dict__, indent=2))
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--aspect", default="1:1")
    parser.add_argument("--operation-id", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.image, args.aspect, args.operation_id))
