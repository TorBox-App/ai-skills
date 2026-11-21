---
name: torbox-api
description: "Use when calling the TorBox API (api.torbox.app) to add torrents, usenet or web downloads, check the cache, get download links, or interpret TorBox error codes and rate limits."
---

# TorBox API

How to call the TorBox API correctly on a user's behalf, and what to do when it returns an error.

Official reference: https://api-docs.torbox.app/ (machine-readable spec: https://api.torbox.app/openapi.json). If anything here disagrees with a live API response, the live response wins.

## Ground rules

1. **Branch on the `error` code, not the HTTP status.** Some user-caused problems (plan restrictions, unsupported sites, items not cached) come back with HTTP 500. The `error` string is the reliable signal.
2. **Never invent parameter values.** When a value is wrong the API answers `INVALID_OPTION` and `detail` lists the accepted values. Read it and retry once with a listed value.
3. **Show the user `detail`.** Every response carries a human-readable `detail` string written for end users. Relay it instead of paraphrasing the error code.
4. **Protect the API key.** It grants full account access. Never print it, log it, or put it in anything the user will share. Download links and permalinks embed the key or an account token (see "Download links"), so treat those as secrets too.
5. **Confirm before destructive calls.** Ask the user first for any `delete` operation, anything with `all: true`, clearing notifications, and resetting the usenet password.
6. **Be gentle with the API.** Respect the rate limits, use `bypass_cache` sparingly, prefer permalinks over repeated link requests, and retry only as the retry policy allows.

## MCP server

TorBox has an official MCP server at `https://api.torbox.app/mcp`. It exposes TorBox operations as tools an agent can call.

- **Check your tool list before building HTTP requests.** If TorBox MCP tools are connected in this session, you can use them to act on the user's account.
- **If they are not connected, tell the user once** that the server exists and can be added in their client's MCP settings with the URL above. Then carry on with the HTTP API as described below. Do not wait for them to add it.
- The server needs a TorBox login. The user's API key works: send it as `Authorization: Bearer <API_KEY>`, the same header the HTTP API uses. A client can also sign the user in to TorBox when the server is connected.
- The ground rules above apply to MCP tool calls too, including confirming destructive operations.
- Code or scripts you write for the user still call the HTTP API as the rest of this skill describes.

## Basics

| | |
|---|---|
| Base URL | `https://api.torbox.app` |
| Path prefix | `/v1/api/...` |
| Auth | `Authorization: Bearer <API_KEY>` header |
| Key location | https://torbox.app/settings, API key section |
| Dates | UTC, `YYYY-MM-DDTHH:MM:SSZ` (example `2024-10-21T20:47:03Z`) |
| Sizes | Bytes |

These endpoints take the key as a `token` query parameter instead of the header, because they are meant to be opened as plain URLs: `requestdl`, `requestdl/batch`, `notifications/rss`, `stream/getstreamdata`.

### Response envelope

```json
{ "success": true, "error": null, "detail": "Human readable message", "data": {} }
```

- `success`: boolean.
- `error`: an error code string, or `null`.
- `detail`: message safe to show the user.
- `data`: usually an object or array, but can be a string (a download link), `null`, or extra error context.

All responses are JSON except file downloads (torrent files, PDFs) and RSS feeds (XML).

### HTTP status codes

| Status | Usual meaning |
|---|---|
| 200 | Success |
| 307 | Redirect to a file (`requestdl` with `redirect=true`) |
| 400 | The request or the account state was the problem |
| 403 | Authentication problem |
| 404 | Wrong URL (`ENDPOINT_NOT_FOUND`) or nothing found (`ITEM_NOT_FOUND`) |
| 409 | `NOT_OWNER` |
| 422 | Validation error. `detail` is an array of `{loc, msg, type}` naming the bad field |
| 429 | Rate limited. Wait before retrying |
| 500 | Often a TorBox-side failure, but check `error` (ground rule 1). Retry up to 3 times (see "Retry policy") |

### Request body formats (common mistake)

The create endpoints take **form data, not JSON**. Almost everything else that has a body takes **JSON**.

| Endpoint | Body |
|---|---|
| `POST /torrents/createtorrent`, `POST /torrents/torrentinfo` | `multipart/form-data` |
| `POST /usenet/createusenetdownload` | `multipart/form-data` |
| `POST /webdl/createwebdownload` | form data |
| Control, edit, RSS, batch and cache-check POST endpoints | `application/json` |

Keep any single request under 100 MB (`TOO_MUCH_DATA`).

## Rate limits

Limits are **per API token**, not per IP.

| Scope | Limit |
|---|---|
| All endpoints unless listed | 300 requests per minute |
| `POST /torrents/createtorrent` | 300 per minute overall, plus **60 uncached torrents per hour** |
| `POST /usenet/createusenetdownload` | 60 per hour |
| `POST /webdl/createwebdownload` | 60 per hour |
| `POST /notifications/test` | 1 per minute |

How the torrent limit works: every create counts against the 300/min pool. A torrent that is **not** cached also counts against the 60/hour pool. Cached torrents are not limited hourly.

Practical consequences:

- Check the cache in bulk first (`checkcached`). Cached torrents can be added quickly. Uncached ones must be budgeted at 60 an hour.
- For a large batch, add cached items first, then pace the uncached ones and tell the user how long it will take.
- Stop on the first rate-limit response instead of pushing through.

## The three download types

Torrents, usenet and web downloads share the same design. Endpoint names and id fields differ:

| | Torrents | Usenet | Web downloads |
|---|---|---|---|
| Prefix | `/v1/api/torrents` | `/v1/api/usenet` | `/v1/api/webdl` |
| Create | `createtorrent` | `createusenetdownload` | `createwebdownload` |
| Async create | `asynccreatetorrent` | `asynccreateusenetdownload` | `asynccreatewebdownload` |
| Id returned by create | `torrent_id` | `usenetdownload_id` | `webdownload_id` |
| List | `mylist` | `mylist` | `mylist` |
| Cache check | `checkcached` | `checkcached` | `checkcached` |
| Control | `controltorrent` | `controlusenetdownload` | `controlwebdownload` |
| Id field in control | `torrent_id` | `usenet_id` | `webdl_id` |
| Download link | `requestdl` | `requestdl` | `requestdl` |
| Id param in `requestdl` | `torrent_id` | `usenet_id` | `web_id` |
| Edit | `edittorrent` | `editusenetdownload` | `editwebdownload` |
| Id field in edit | `torrent_id` | `usenet_download_id` | `webdl_id` |
| `type` value elsewhere | `torrent` | `usenet` | `webdl` (`webdownload` for streams) |

Using the wrong id name for the type is the most common cause of `MISSING_REQUIRED_OPTION` and 422 errors. There is no file-selection step: a download always fetches all of its files.

## Standard workflow

1. **Check the account** (optional): `GET /v1/api/user/me`. Confirms the key works and shows the plan.
2. **Check the cache**: `checkcached`. Cached items are ready instantly.
3. **Create** the download.
4. **Poll** `mylist?id=<id>` until `cached` is true.
5. **Request a link** with `requestdl`.

### 1. Check the cache

`GET /v1/api/torrents/checkcached?hash=<hash1>,<hash2>&format=list`

- `hash`: comma-separated, repeated (`?hash=A&hash=B`), or both mixed. About 100 hashes per GET because of URL length.
- For more hashes use `POST` with JSON `{"hashes": [...]}` (practically unlimited). `format` and `list_files` stay in the query string.
- `format`: `object` (default, keyed by hash) or `list` (faster).
- `list_files=true` adds each cached item's files (`id`, `name`, `size`, `short_name`, `mimetype`).
- **Only cached hashes are returned.** A hash missing from the result is not cached. Nothing cached gives an empty or `null` `data` with `success: true`. That is not an error.
- Results are cached for an hour. Do not re-check the same hash in a loop.
- For usenet and web downloads the "hash" is the MD5 of the link.
- Do not use `torrentinfo` to check the cache. It queries the BitTorrent network and is slow.

### 2. Create

`POST /v1/api/torrents/createtorrent` (multipart form)

| Field | Notes |
|---|---|
| `magnet` or `file` | Exactly one. Both gives `TOO_MANY_OPTIONS`, neither gives `MISSING_REQUIRED_OPTION` |
| `seed` | `1` auto, `2` seed, `3` don't seed. Default is the user's own setting. Only send it if the user asked |
| `allow_zip` | Whether TorBox may zip the result. It only zips torrents with 100 or more files. Send `false` if the user needs individual files |
| `name` | Optional display name |
| `as_queued` | `true` puts it straight in the queue instead of starting it. Ignored on the free plan |
| `add_only_if_cached` | `true` adds it only when instantly available, otherwise fails with `DOWNLOAD_NOT_CACHED` |

```bash
curl -X POST "https://api.torbox.app/v1/api/torrents/createtorrent" \
  -H "Authorization: Bearer $TORBOX_API_KEY" \
  -F "magnet=magnet:?xt=urn:btih:<hash>"
```

Success returns `data: {"hash": "...", "torrent_id": 123, "auth_id": "..."}`. Keep the id. If you sent `as_queued=true`, find the item with `queued/getqueued` instead.

**Usenet** (`link` or `file`, plus optional `name`, `password`, `as_queued`, `add_only_if_cached`). The `link` must point directly at the NZB, not at a redirect. `password` is used to extract the archive. `post_processing`:

| Value | Meaning |
|---|---|
| `-1` | Default. Repair, extract, delete sources, keep only the wanted files. **Leave this unless the user asks otherwise** |
| `0` | None. Download everything including PAR2, no repair or extraction |
| `1` | Repair only |
| `2` | Repair and unpack, archives kept |
| `3` | Repair, unpack, delete archives |

**Web downloads** take `link` (required, a direct link, not a redirect), plus optional `password`, `name`, `as_queued`, `add_only_if_cached`. Before submitting a link from a file hoster, `GET /v1/api/webdl/hosters` shows whether that hoster is supported and currently working (`status`), any `note` for users, and its daily and per-link limits. Send the auth header to that endpoint to see the user's own usage against those limits.

**Async variants** return immediately with no id, and report failures later as account notifications. Use them for bulk adds, then find the items through `mylist`.

### 3. Poll status

`GET /v1/api/torrents/mylist`

| Param | Notes |
|---|---|
| `id` | Return one item (an object) instead of the list |
| `offset`, `limit` | Pagination. Default limit 1000 |
| `bypass_cache` | `true` forces fresh data. Use it for the call right after a change, not on every poll |
| `active` | Only active downloads |
| `files` | Controls whether the file list is included. Leave it out when you need file ids |

How fresh the data is: torrent stats refresh about every 10 minutes unless you bypass the cache. Usenet and web download stats refresh every few seconds while downloading.

Deciding whether an item is ready:

- **Ready to download: `download_finished` is `true` and `download_present` is `true`.** Use these booleans.
- **Do not use `download_state` to detect completion.** It is a display string. Known values: `downloading`, `uploading` (seeding), `stalled (no seeds)`, `paused`, `completed`, `cached`, `metaDL` (fetching metadata), `checkingResumeData`, plus other qBittorrent state names.
- `progress` runs 0 to 1. `eta` is seconds. `download_speed` is bytes per second.
- Each entry in `files` has an `id`, `name`, `short_name`, `size`, `mimetype`. The `id` is the `file_id` for download links.
- `expires_at` shows when an unused item will be removed.
- An account with no items may return `ITEM_NOT_FOUND` here. Treat that as an empty list.

Poll every 10 to 30 seconds at most. A torrent in `stalled (no seeds)` may never finish. After a reasonable wait, tell the user rather than polling forever.

### 4. Download links

`GET /v1/api/torrents/requestdl?token=<API_KEY>&torrent_id=<id>&file_id=<file id>`

| Param | Notes |
|---|---|
| `token` | The API key as a query parameter. Required here |
| `torrent_id` / `usenet_id` / `web_id` | Item id, named per type |
| `file_id` | A file's `id` from `mylist` |
| `zip_link` | `true` for one zip of the whole item. **Required when no `file_id` is given**, and wins if both are sent |
| `redirect` | `true` makes the endpoint redirect (307) straight to the file instead of returning JSON |
| `user_ip` | IPv4 of the device that will download. Pass it when that is not the machine calling the API, so the closest CDN is chosen |
| `append_name` | `true` adds the filename to the returned link |

Two kinds of link:

- **Temporary link**: without `redirect`, `data` is a CDN URL string. The download must be **started within about 3 hours**. Once started it can run as long as it needs. Do not store these.
- **Permalink**: the `requestdl` URL itself with `redirect=true`, for example `https://api.torbox.app/v1/api/torrents/requestdl?token=APIKEY&torrent_id=123&file_id=4&redirect=true`. It keeps working and redirects to a fresh CDN link each time. **Prefer this** whenever a link will be saved or reused (playlists, media libraries). It also saves API calls. It stops working when the user resets their API key or deletes the item.

Both kinds carry the user's key or an account token. Warn the user not to share them publicly.

Several files at once: `requestdl/batch`, either `GET` with `file_ids`, or `POST` with JSON `{"file_ids": [1, 2, 3]}`. `token` and the item id stay in the query. `data` is an array of links.

### 5. Control

`POST /v1/api/torrents/controltorrent` with JSON `{"torrent_id": 123, "operation": "delete"}`

| Endpoint | Operations |
|---|---|
| `controltorrent` | `reannounce` (look for new peers), `resume`, `stop_seeding`, `delete` |
| `controlusenetdownload` | `delete` |
| `controlwebdownload` | `delete` |
| `queued/controlqueued` | `start`, `delete` |
| `rss/controlrss` | `update` (force a scan), `pause`, `resume`, `delete` |

- `delete` is permanent.
- `all: true` (instead of an id) applies the operation to **every** item of that type. Never set it unless the user explicitly asked for all, and confirm first. `start` cannot be combined with `all`.
- If an operation is rejected, `detail` lists the currently accepted ones.

## Queue

When the account's active slots are full, downloads can wait in a queue and start automatically.

- Add to the queue by sending `as_queued=true` on any create endpoint. There is no separate "add to queue" endpoint.
- `GET /v1/api/queued/getqueued?type=torrent` lists queued items. `type` is `torrent`, `usenet` or `webdl`, one type per call. Same `id`, `offset`, `limit`, `bypass_cache` params as `mylist`.
- `POST /v1/api/queued/controlqueued` with `{"queued_id": 1, "operation": "start"}`.
- Queued items have their own ids. They get a normal item id only once they start.
- The queue holds at most 1000 items (`DIFF_ISSUE` beyond that).

## Error codes

Codes ending in `_ERROR` are TorBox-side problems. Everything else was caused by the request or the account.

### Authentication

| Code | Meaning | What to do |
|---|---|---|
| `NO_AUTH` | No credentials sent | Add the `Authorization: Bearer` header, or `token` for `requestdl` |
| `BAD_TOKEN` | API key is invalid or was reset | Ask the user to copy the current key from Settings |
| `AUTH_ERROR` | TorBox could not verify the key right now | Retry once after a few seconds, then ask the user to check the key |
| `OAUTH_VERIFICATION_ERROR` | A third-party OAuth token was rejected | User must reconnect that integration |
| `INVALID_DEVICE` | Request came from the wrong device | Retry from the device that started the flow |
| `NOT_OWNER` | The item is not on this account, or cannot be controlled by it | Refresh ids from `mylist`. Do not retry |

### Bad request

| Code | Meaning | What to do |
|---|---|---|
| `INVALID_OPTION` | A value is not allowed | `detail` lists valid values or explains. Fix and retry once |
| `MISSING_REQUIRED_OPTION` | A required field is missing | Check field names for this download type |
| `TOO_MANY_OPTIONS` | Mutually exclusive fields were sent | Send only one, for example `magnet` or `file` |
| `TOO_MUCH_DATA` | Request over 100 MB | Send less |
| `ENDPOINT_NOT_FOUND` | Wrong URL | Fix the path and the `/v1/api` prefix |
| `ITEM_NOT_FOUND` | Nothing matches | On a list endpoint: the list is empty. With an id: refresh ids, the item may be deleted or be a different type |
| `DUPLICATE_ITEM` | Already exists | Not a failure. Use the existing item |
| `DIFF_ISSUE` | The request cannot be completed as sent (for example the queue is full) | Read `detail` |
| `BOZO_TORRENT` | Torrent file or magnet is invalid | Ask for a correct one |
| `BOZO_NZB` | NZB is invalid | Ask for a correct one |
| `BOZO_FILE` | Wrong kind of file (for example streaming a non-video) | Pick a different file |
| `BOZO_RSS_FEED` | Feed is invalid, malformed, or not allowed | Check the feed URL |
| `BOZO_REGEX` | A regex filter is invalid | Fix the regex |
| `INVALID_LINK` | The web link is not valid | Ask for a correct direct link |
| `UNSUPPORTED_SITE` | That site is not supported for web downloads | Tell the user. Check `webdl/hosters` |
| `TEMPORARILY_DISABLED` | That site is supported but switched off for now | Tell the user to try later |
| `LINK_OFFLINE` | The link or file is offline | Tell the user. Retrying right away will not help |
| `DOWNLOAD_NOT_CACHED` | `add_only_if_cached` was set and the item is not cached | Expected outcome. Offer to add it as a normal download |
| `NOT_CACHED` | Tried to edit an item that is not finished | Wait until it finishes |
| `NO_CHANGES` | Edit request contained nothing to change | Send at least one field |
| `NAME_TOO_SHORT` / `NAME_TOO_LONG` | Name must be 1 to 200 characters | Fix the name |
| `INVALID_HASH` | Alternative hash is not MD5, SHA1 or SHA256 | Fix the hash |
| `BAD_CONFIRMATION` / `CONFIRMATION_EXPIRED` | Emailed confirmation code is wrong or expired | Ask the user for the code again, or request a new one |
| `BOZO_REFERRAL` | Referral code gives no benefit or is the user's own | Tell the user |

### Plan and usage limits

These are account limits, not bugs. Do not retry in a loop. Explain the limit to the user.

| Code | Meaning | What to do |
|---|---|---|
| `PLAN_RESTRICTED_FEATURE` | The user's plan does not include this feature | Say which plan it needs (`detail` usually states it) |
| `DOWNLOAD_TOO_LARGE` | Larger than the plan allows | Limits: Free 10 GiB, Essential 200 GiB, Standard 200 GiB, Pro 500 GiB |
| `ACTIVE_LIMIT` | Maximum simultaneous downloads reached. `data` has `active_limit` and `current_active_downloads` | Re-send with `as_queued=true` so it starts when a slot frees, or wait, or remove an item with consent |
| `MONTHLY_LIMIT` | Monthly allowance used. `data` has `monthly_limit` and `current_downloads` | Tell the user the numbers. Resets next month |
| `COOLDOWN_LIMIT` | Account is in a cooldown. `data` has `cooldown_until` | Tell the user when it ends |
| `VENDOR_DISABLED` | Vendor account disabled | User must contact TorBox support |

### TorBox-side

| Code | Meaning | What to do |
|---|---|---|
| `DATABASE_ERROR` | Internal data store unavailable | Retry with backoff |
| `DOWNLOAD_SERVER_ERROR` | A download server did not respond properly, or metadata could not be fetched in time | Wait, then retry. For `torrentinfo`, raise `timeout` |
| `NO_SERVERS_AVAILABLE_ERROR` | No download server free | Retry later. If it persists, contact support |
| `REDIRECT_ERROR` | Redirect failed | Retry, or call without `redirect` and use the returned link |
| `STREAM_INFO_ERROR` | Could not read stream information | Retry later |
| `UNKNOWN_ERROR` | Unexpected failure. `data` may hold partial results or details | Retry once. If it persists, have the user report it to contact@torbox.app with the request details |

### Device-code login

| Code | Meaning |
|---|---|
| `DEVICE_CODE_NOT_USED` | User has not approved yet. Keep polling |
| `ITEM_NOT_FOUND` | Code is invalid or expired. Start again |

### Retry policy

- **Any HTTP 500**: retry up to 3 times with growing waits (2s, 5s, 15s), whatever the `error` code is. Never more than 3. Then stop and give the user the `detail`.
- **`_ERROR` codes with any other status**: the same, up to 3 retries.
- **Request and plan errors that are not HTTP 500**: do not retry unchanged. Fix the request or tell the user.
- **HTTP 429**: wait (for creates, the hourly window may need to pass), then retry.
- **HTTP 502 or no JSON body**: the API itself may be down. `GET https://api.torbox.app/` checks it. Status page: https://status.torbox.app (as JSON: https://status.torbox.app/index.json)

## Other endpoints

All under `/v1/api`. Auth header required unless noted.

### User

- `GET /user/me`: account info, including `plan`, `premium_expires_at`, `cooldown_until`, `is_subscribed`. Add `settings=true` for settings.
- Plans: `0` Free, `1` Essential, `2` Pro, `3` Standard.
- `GET /user/stats?general=true&bandwidth=true&bandwidth_grouping=day`: totals and last 30 days of bandwidth. Grouping is `hour`, `day`, `week` or `month`.
- `PUT /user/settings/editsettings`: JSON with only the settings to change. Takes effect immediately. Read current values first with `me?settings=true`.
- `GET /user/subscriptions`: show users `status`, `gateway` and `plan_name` only.
- `GET /user/transactions`, `GET /user/transaction/pdf?transaction_id=`, `GET /user/referraldata`.
- Resetting the API key and deleting the account need a website session token or an emailed confirmation code. Send users to https://torbox.app/settings for those instead of attempting them.

### Signing a user in without pasting a key (device code)

1. `GET /user/auth/device/start?app=<AppName>` (no auth). `app` is letters and numbers only. Returns `device_code`, `code` (6 digits), `verification_url`, `friendly_verification_url`, `interval`, `expires_at`.
2. Show the user the `code` and the `friendly_verification_url` (or the `verification_url` as a QR code). Do not wrap or redirect these URLs. The code is valid for 10 minutes.
3. `POST /user/auth/device/token` (no auth) with JSON `{"device_code": "..."}` every `interval` seconds. It returns `DEVICE_CODE_NOT_USED` until approved, then `data.access_token`, which is the API key.
4. Free-plan accounts cannot complete this flow.

### Torrent utilities

- `GET /torrents/torrentinfo?hash=<hash>` (no auth): name, size, files, trackers, seeds and peers for a hash without adding it. Slow, because it asks the BitTorrent network. `timeout` is in seconds (default 10). Raise it for poorly seeded torrents. `use_cache_lookup=true` reuses an earlier result.
- `POST /torrents/torrentinfo` (no auth, form data): same, accepting `hash`, `magnet` or `file`. `peers_only=true` returns just seed and peer counts quickly.
- `GET /torrents/exportdata?torrent_id=<id>&type=magnet|file`: `magnet` returns the magnet string in `data`, `file` returns a .torrent download. Does not work for items served from cache.
- `POST /torrents/magnettofile` (no auth): JSON `{"magnet": "..."}` returns a .torrent file.
- `PUT /torrents/edittorrent`: JSON with `torrent_id` plus `name`, `tags`, `alternative_hashes`. **Overwrites** the existing values, so send the full intended list of tags. The item must be finished.

### RSS feeds (Pro plan)

- `POST /rss/addrss`: JSON. `url` and `name` required. Optional: `do_regex` (only add matches), `dont_regex` (skip matches), `dont_older_than` (days), `scan_interval` (minutes, minimum 10, default 60), `rss_type` (`torrent`, `usenet`, `webdl`), `torrent_seeding` (`1` auto, `2` always, `3` never), `pass_check`.
- `POST /rss/modifyrss`: same fields with `rss_feed_id`. The URL cannot be changed.
- `GET /rss/getfeeds` (optional `id`): feed `status` is `active`, `paused` or `error`, with a `status_message` to show the user.
- `GET /rss/getfeeditems?rss_feed_id=<id>`: item `status` is `new`, `ignored` (filtered out by the feed's rules), `error` (will be retried), or `downloaded`.
- `POST /rss/controlrss`: see Control. Deleting a feed removes its items but not downloads already queued from it.

### Streaming (Pro plan)

**These endpoints are only for playing a file in a browser when the browser cannot play that file itself.** A request to "stream", "watch" or "play" a video does not by itself mean these endpoints.

For the best performance when playing video, request a normal download link (see "Download links") and open it in a dedicated player such as MPV or VLC. Reach for the stream endpoints only when playback has to happen in a browser and the file is incompatible with it.

- `GET /stream/createstream?id=<item id>&file_id=<file id>&type=torrent`: `type` is `torrent`, `usenet` or `webdownload`. Returns `hls_url` plus `metadata` listing the audio and subtitle tracks.
- First call without track choices to see what exists, then call again with `chosen_audio_index` and `chosen_subtitle_index`. These are positions in the returned lists starting at 0, not the tracks' own `index` values. No subtitle is `null`. Only text subtitles work.
- `chosen_resolution_index`: `null` original, `0` 144p, `1` 240p, `2` 360p, `3` 480p, `4` 720p, `5` 1080p, `6` 1440p, `7` 2160p. Video is never upscaled.
- `BOZO_FILE` means the file is not a video.

### Cloud transfers

- `POST /integration/googledrive` | `dropbox` | `onedrive` | `gofile` | `1fichier` | `pixeldrain`: JSON `{"id": <item id>, "file_id": <file id>, "zip": false, "type": "torrent"}` plus that provider's token field. Starts a background job.
- `GET /integration/jobs`, `GET /integration/job/<job_id>`, `GET /integration/jobs/<hash>`: job `status` is `pending`, `uploading`, `completed` (then `download_url` is set) or `failed` (reason in the job's `detail`).
- `DELETE /integration/job/<job_id>`: cancels a running job or removes a finished one.

### Notifications

- `GET /notifications/mynotifications`: recent account notifications. Useful for seeing why an async create failed.
- `POST /notifications/clear`, `POST /notifications/clear/<id>`: permanently deletes them.
- `POST /notifications/test`: sends a test to every channel the user enabled.

### Usenet provider access (Pro plan)

- `GET /usenet/provider/connection` (no auth): server host, port and connection limits.
- `GET /usenet/provider/account`: the user's credentials. The account is created on first call, and the password is only shown then.
- `POST /usenet/provider/account/resetpw`: generates a new password, shown once. It breaks any client still using the old one, so confirm first and tell the user to save it.

### Service info (no auth)

- `GET /` (is the API up), `GET /v1/api/stats`, `GET /v1/api/changelogs/json?offset=0&limit=10`.
- `GET /v1/api/speedtest?user_ip=<the user's public IP>`: speed test files, one per CDN region, with the nearest marked `closest`. Always pass the user's public IP. Without it, `closest` is the server nearest to you, not to the user. If you do not have their IP, follow the speed test procedure in the `torbox-troubleshooting` skill. If that skill is not installed, tell the user you cannot get a speed test for them and send them to https://torbox.app/speedtest.

## No search

TorBox does not offer a search API. Do not call `search-api.torbox.app` or any search endpoint, even if older code or documentation mentions one. The user must supply the magnet, torrent file, NZB or link. `checkcached` only tells you whether a hash you already have is cached.

## Common mistakes checklist

- Sent JSON to a create endpoint. Use form data.
- Forgot `/v1/api` in the path. Gives `ENDPOINT_NOT_FOUND`.
- Used `torrent_id` on a usenet or web download call. Check the id table.
- Used the Bearer header on `requestdl` without `token` in the query.
- Called `requestdl` with neither `file_id` nor `zip_link=true`.
- Used a file's position in the list as `file_id`. Use the file's `id` field.
- Waited for `download_state` to say `completed`. Check `download_finished`.
- Stored a temporary CDN link. Use a permalink (`redirect=true`).
- Used `createstream` to play a video. Use a normal `requestdl` link in a dedicated player such as MPV or VLC. The stream endpoints are only for files a browser cannot play.
- Sent `pause` to a torrent. The operations are `reannounce`, `resume`, `stop_seeding`, `delete`.
- Read stale `mylist` data right after a change. Add `bypass_cache=true` for that one call.
- Treated an HTTP 500 as an outage without reading `error`.
- Retried `ACTIVE_LIMIT` in a loop. Use `as_queued=true`.
- Treated `DUPLICATE_ITEM`, `DOWNLOAD_NOT_CACHED`, or an empty cache-check result as a failure.
- Burned the 60/hour uncached budget on items that were never going to be useful. Check the cache first.
- Called a search endpoint. There is none.

## Working with the user

- If no API key is available and no TorBox MCP tools are connected, ask the user for a key (https://torbox.app/settings) or use the device-code flow. Do not proceed without one or the other.
- Before a bulk job, say how many items are cached, how many are not, and roughly how long the rate limits make it take.
- Report sizes in GB and speeds in MB/s, not raw bytes.
- When something fails, give the user the `detail` text, what it means, and the one thing they can do next.
- When a plan limit blocks a request, say which limit and which plan lifts it. Do not push an upgrade beyond that.
- For problems you cannot resolve (repeated `_ERROR` codes, `UNKNOWN_ERROR`, billing questions), direct the user to TorBox support at contact@torbox.app rather than guessing.