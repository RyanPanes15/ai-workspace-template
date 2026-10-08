# payload-decode module

`decode_response.py` turns compressed API bodies (base64 + zlib/gzip/deflate, e.g.
`{"response":"eJx…"}`), pasted payloads, or a browser HAR export into readable JSON.
`--summary` prints status/counts/keys only — use it first to keep context small.
Stdlib only. Decoded bodies can contain real user data: keep them in `_work/`.
