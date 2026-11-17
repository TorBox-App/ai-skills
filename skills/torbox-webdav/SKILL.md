---
name: torbox-webdav
description: "Use when working with TorBox WebDAV (webdav.torbox.app): connecting a WebDAV client or media player to a TorBox account, listing or downloading the account's files over WebDAV, or troubleshooting login failures and missing or stale files."
---

# TorBox WebDAV

How to reach a user's TorBox files over WebDAV, and what to expect from the server.

Official article: https://support.torbox.app/en/articles/14662867-torbox-webdav. If anything here disagrees with what the live server returns, the live server wins.

## Ground rules

1. **Treat it as read-only.** Nothing can be uploaded, edited or renamed through WebDAV. Do not attempt it.
2. **Confirm before any delete.** Delete is the one change that works, and deleting a single file removes the **entire item** from the user's TorBox account, not just that file. It happens at once. Only ever delete a single file path. What a delete on a folder, a tag folder or the root does is not documented, so never send one.
3. **Protect the credentials.** The login is the account password or the API key, and either one gives full access to the account. Never print or log them, and never write them into a URL (`https://user:password@...`) or a config file the user might share.
4. **Do not poll.** The listing refreshes every 15 minutes. Listing again and again does not show new files sooner.

## Connection

| | |
|---|---|
| Server URL | `https://webdav.torbox.app` |
| Protocol | HTTPS |
| Port | 443 |
| Auth | HTTP Basic |

Either of these logins works:

| Username | Password |
|---|---|
| `torbox` (the literal word) | The user's API key, from https://torbox.app/settings |
| The user's TorBox email | The user's TorBox password |

- When you connect yourself, use `torbox` and the API key. Do not ask the user for their account password.
- An account created with Google or Apple sign-in has no password. Use `torbox` and the API key, or have the user set a password at https://torbox.app/forgotpw and use that.
- A request without credentials returns HTTP 401 with `{"detail":"Not authenticated"}`. Wrong credentials return HTTP 401 with a `detail` saying the credentials are invalid.

Any client that supports WebDAV over HTTPS can connect. To list the root from a shell:

```bash
curl -u "torbox:$TORBOX_API_KEY" -X PROPFIND -H "Depth: 1" "https://webdav.torbox.app/"
```

How the server behaves:

- **Methods.** It accepts `GET`, `HEAD`, `OPTIONS`, `PROPFIND` and `DELETE`, and nothing else.
- **Listing.** `PROPFIND` returns HTTP 207 with the direct children of the folder, whatever `Depth` header is sent. It never recurses. To walk the tree, list one folder at a time. The root listing includes the root itself as its first entry. A subfolder listing does not include the folder, so do not skip its first entry.
- **Files.** `GET` on a file returns the file itself and supports `Range` requests.
- **Delete.** `DELETE` on a file returns HTTP 204.

## What appears in it

The root has one folder for each item on the user's account whose files are currently available. An account with no items can still log in, but has nothing to show.

- **Only available items are listed.** An item appears when `download_present` is `true` in the TorBox API. Items that are still downloading, or whose files are no longer present, are not in the WebDAV.
- **Folder names come from the files, not the item.** An item's folder is named after the top-level folder in its file paths. That can differ from the item's name on the dashboard.
- **Tags become folders.** Each tag the user puts on an item creates a folder in the root, named with the tag in lowercase, holding the folder of every item with that tag. The item also stays in the root. TorBox's example: the tag "Linux ISOs" gives a folder at `webdav.torbox.app/linux isos`.
- **Flatten setting.** TorBox describes it as placing all files in the root directory instead of in folders. After changing it, list the root to confirm it took effect before relying on it.
- **Explorer View setting.** Gives the WebDAV website a richer interface, similar to a file explorer.

Both settings are on https://torbox.app/settings, in the integrations section. The flatten setting is also `webdav_flatten` in the TorBox API (`PUT /v1/api/user/settings/editsettings`). Change it only when the user asks.

List the root and read what is there before building any path. Do not guess folder names.

## Freshness

- **The listing refreshes every 15 minutes.** A download that just finished, or a tag that was just added, can be missing until the next refresh. That is expected, not an error.
- **Manual refresh:** send `GET https://webdav.torbox.app/refresh` with the same login. Leave off the trailing slash: `/refresh` answers HTTP 303 with a redirect to `/`, while `/refresh/` returns HTTP 404. Wait about 15 seconds, then list again. Do this once after a change. The 15-minute limit exists because of the load WebDAV puts on TorBox, so never call it in a loop.
- **A delete shows immediately.** The deleted item is gone from the listing without a refresh.
- **Caching.** Files are currently served only through Cloudflare, which can cause cached results. If a listing still looks stale after one refresh, tell the user instead of retrying.

## Setting up a client

Give the user the connection values above. TorBox has guides for these two clients:

**Cyberduck** (macOS and Windows)

1. Click Open Connection.
2. Change the protocol from "FTP (File Transfer Protocol)" to "WebDAV (HTTPS)".
3. Enter `webdav.torbox.app` as the server and keep the port at 443.
4. Enter the login and click Connect.

Guide: https://support.torbox.app/en/articles/9917933-how-to-access-torbox-webdav-over-cyberduck

**Infuse**

- Protocol: HTTPS.
- Address: `https://webdav.torbox.app`.
- Leave these unchecked: Auto Scan, Pre-Cache Details, Pre-Cache Artwork, Smart Folders.

Guide: https://support.torbox.app/en/articles/13433186-how-to-access-torbox-webdav-over-infuse

## Troubleshooting

| Symptom | Cause | What to do |
|---|---|---|
| HTTP 401, or the client rejects the login | Wrong credentials, or the account has no password because it uses Google or Apple sign-in | Use `torbox` with the API key, or set a password at https://torbox.app/forgotpw |
| A new download is not listed | The 15-minute refresh has not run yet, or the download's files are not available yet | Check `download_present` for the item in the TorBox API. If it is `true`, request `/refresh` once, wait about 15 seconds, then list again |
| The refresh URL returns 404 | It was requested as `/refresh/` | Request `/refresh` with no trailing slash |
| An item's folder cannot be found by its name | The folder is named after the item's files, not the item | List the root and match on the file paths |
| A tag folder is missing | The tag was added after the last refresh | Request `/refresh` once, wait about 15 seconds, then list again |
| Upload, edit or rename fails | The WebDAV is read-only | Tell the user it is not supported |
| Every file is in the root with no folders | The flatten setting is on | The user can turn it off in settings |
| The listing is still stale after a refresh | Cloudflare caching | Tell the user and wait. Do not keep retrying |

## Working with the user

- When you need to connect yourself and have no login, ask the user for their API key (https://torbox.app/settings). When you are only helping the user set up a client, you do not need it. The user types the login into the client.
- WebDAV only reads what is already on the account. Adding downloads, tagging items and changing settings happen on the TorBox website or through the TorBox API. If the `torbox-api` skill is installed, use it for those.
- When the user asks to delete something, say that the whole item will be removed from their account and get a yes first.
- For problems you cannot resolve, direct the user to TorBox support at contact@torbox.app rather than guessing.
