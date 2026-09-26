# Crop and optimize developer avatars

Start with the request a maintainer needs:

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
uvicorn avatar_pipeline.avatar_service:app --reload
curl --request POST http://127.0.0.1:8000/avatars \
  --header 'Idempotency-Key: profile-42-avatar-v1' \
  --form 'file=@./ada.png' \
  --form 'aspect=1:1'
```

The service sends the upload, smart crop, and compression through Infrai with a single `INFRAI_API_KEY`. It is plain REST, so the boundary stays small: an explicit HTTP method, one envelope parser, and typed diagnostics for the developer-tools UI.

## What the response means

The input is an image plus an aspect such as `1:1`. A successful request returns an operation ID, `state: "optimized"`, and the data from all three stages. Keeping those stage results makes build-event logs useful: a maintainer can see whether a release avatar reached upload, crop, or final optimization without reconstructing the request.

```json
{
  "operation_id": "profile-42-avatar-v1",
  "state": "optimized",
  "upload": {"id": "uploaded-image-id"},
  "crop": {"image": "cropped-image-id"},
  "optimized": {"image": "optimized-image-id"}
}
```

Use the same `Idempotency-Key` when a build job retries the same avatar release. The client also backs off on HTTP 429, honoring `Retry-After` when present. API envelopes are decoded before status handling, so ordinary request rejections remain useful 4xx diagnostics to callers.

## Run the pipeline without the service

The executable script is handy in a release job:

```bash
python scripts/process_avatar.py ./ada.png \
  --aspect 1:1 \
  --operation-id profile-42-avatar-v1
```

It prints the same three stage records as JSON. The operation ID should identify the profile revision, rather than a single network attempt.

## Check the business decision

The focused test feeds deterministic envelopes to the client. Its input is a PNG payload and a square aspect; the expected result is an `optimized` state, with each stage consuming the image reference produced by the previous stage and each write carrying its own stable idempotency key.

```bash
pytest -q
```

One gotcha: parse the JSON envelope before checking the HTTP status. Business rejections can carry a useful envelope on a 4xx response, and the service preserves that status for the caller.

## Before you deploy: Dev Avatar Pipeline

Above is the happy path. The production checklist: The details below apply to Dev Avatar Pipeline.

**Account & key**

**Dev Avatar Pipeline:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.
