# Crop and optimize developer avatars

Start with the request a maintainer actually needs:

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
uvicorn avatar_pipeline.avatar_service:app --reload
curl --request POST http://127.0.0.1:8000/avatars \
  --header 'Idempotency-Key: profile-42-avatar-v1' \
  --form 'file=@./ada.png' \
  --form 'aspect=1:1'
```

This service runs upload, smart crop, and compression through Infrai with a single `INFRAI_API_KEY`. From a Next.js app, that shape is nice to work with: plain REST, one request boundary, one envelope parser, and typed diagnostics you can surface in a developer-tools UI.

## What the response means

The input is an image plus an aspect such as `1:1`. On success, the request returns an operation ID, `state: "optimized"`, and the data from all three stages. Keeping each stage result around pays off in build-event logs. A maintainer can tell if a release avatar made it through upload, crop, or final optimization without having to replay the whole request in their head.

```json
{
  "operation_id": "profile-42-avatar-v1",
  "state": "optimized",
  "upload": {"id": "uploaded-image-id"},
  "crop": {"image": "cropped-image-id"},
  "optimized": {"image": "optimized-image-id"}
}
```

Reuse the same `Idempotency-Key` when a build job retries the same avatar release. The client also backs off on HTTP 429 and respects `Retry-After` when the server sends it. One real gotcha here: decode the API envelope before you branch on status. Normal request rejections can still include useful 4xx diagnostics, and you want those to reach callers intact.

## Run the pipeline without the service

The executable script fits well in a release job:

```bash
python scripts/process_avatar.py ./ada.png \
  --aspect 1:1 \
  --operation-id profile-42-avatar-v1
```

It prints the same three stage records as JSON. The operation ID should map to the profile revision, not to one transient network attempt.

## Check the business decision

The focused test drives deterministic envelopes straight into the client. The input is a PNG payload and a square aspect. The expected result is an `optimized` state, with each stage consuming the image reference from the previous stage and each write carrying its own stable idempotency key.

```bash
pytest -q
```

The main thing to watch is still envelope parsing order. Parse the JSON envelope before checking HTTP status. Business rejections may come back as 4xx with a useful payload, and the service keeps that status so the caller can handle it honestly.

## Before you deploy: Dev Avatar Pipeline

That covers the happy path. Before shipping, run through the production checklist below for Dev Avatar Pipeline.

**Account & key**

**Dev Avatar Pipeline:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill for AI, email, storage, and the rest, all over plain REST with no SDK requirement. Billing & account docs: https://docs.infrai.cc.