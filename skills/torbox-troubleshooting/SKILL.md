---
name: torbox-troubleshooting
description: "Use when a TorBox user has a problem to diagnose: buffering or slow download speeds, running a TorBox speed test, download links that stop working or return 429, slow zip downloads, queued downloads that do not start, downloads that went inactive, trouble logging in or signing up, or TorBox being blocked by antivirus, a VPN, an ISP or a router."
---

# TorBox Troubleshooting

How to work out why TorBox is slow or not working for a user, and when to send them to TorBox support.

This skill follows the TorBox support articles at https://support.torbox.app. Each section links the article it comes from. If anything here disagrees with the article, the article wins.

## Ground rules

1. **Buffering or slow downloads: have the user run a speed test.** See "Speed test" for which way to run it.
2. **Never guess the user's IP address.** The speedtest endpoint picks the closest server from the IP you give it. Without the user's real IP its answer is about you, not them.
3. **Run the speed test on the device that has the problem.** A test from your own sandbox or server measures your connection. A test on another of the user's devices shows what their network can reach, not what the buffering device gets.
4. **Check the status page before digging.** Read https://status.torbox.app/index.json yourself (see "Status page"). If an incident or maintenance is listed for the user's region or the service, tell them and wait for it to be resolved.
5. **Allow TorBox, do not switch protection off.** When security software blocks TorBox, add TorBox's domains to its allow list where that is possible. Turning protection off leaves the user exposed.
6. **Protect the API key and download links.** Download links carry the user's key or an account token. Never post either one where other people can read it.
7. **Send persistent problems to TorBox support.** If the steps here do not fix it, or the problem keeps coming back, urge the user to contact support at https://torbox.app/contact. Do not keep guessing.

## Where to look

| The user says | Section |
|---|---|
| Video buffers, downloads are slow | "Speed test", then "Slow downloads and buffering". Most cases are one of its "Most common causes" |
| A link stopped working, 429, download stops partway | "Download links that stop working" |
| A zip download is slow or restarts | "Slow zip downloads" |
| A queued download never starts | "Queued downloads that do not start" |
| A download is inactive or its files are gone | "Inactive downloads" |
| Cannot log in, sign up, or pass the captcha | "Cannot log in or sign up" |
| Security alerts, blocked pages, SSL handshake errors | "TorBox is blocked" |

## Status page

https://status.torbox.app shows current incidents and maintenance. Give users that address. To read the status yourself, use the JSON version:

`GET https://status.torbox.app/index.json` (no auth)

| Where | What it holds |
|---|---|
| `data.attributes.aggregate_state` | The overall state: `operational`, `degraded`, `downtime` or `maintenance` |
| `included[]` entries with `type: "status_page_resource"` | One per service. `attributes.public_name` is the service (`API`, `Website`, `WebDAV Service`, `Usenet Service`, `WEUR CDN` and so on). `attributes.status` is `operational`, `degraded`, `downtime`, `maintenance` or `not_monitored` |
| `included[]` entries with `type: "status_report"` | Incidents and maintenance windows. `attributes` has `title`, `report_type` (`maintenance` for planned work, `manual` or `automatic` for an incident), `starts_at`, `ends_at`, `aggregate_state` and `affected_resources` |
| `included[]` entries with `type: "status_update"` | The messages posted on a report: `attributes.message` and `attributes.published_at` |

How to read it:

- **Start with `aggregate_state`.** `operational` means nothing is wrong right now. For anything else, find the resources whose `status` is not `operational`.
- **CDN entries are named by region code**, for example `WEUR CDN`. Match the user's region from the speed test (the `region` of the `closest` entry) to check their CDN.
- **A report is over when its `aggregate_state` is `resolved`.** The list keeps past reports, so skip those. For the rest, compare `starts_at` and `ends_at` (UTC) with the current time. Maintenance is often listed before it begins.
- **To name what a report affects**, match each `status_page_resource_id` in `affected_resources` to the `id` of a resource entry. A report's messages are the `status_update` entries listed under its `relationships.status_updates`.
- **Give the user the report's `title` and its latest message**, not your own summary of the outage.
- The response is large, about 300 KB, mostly each resource's 90 days of `status_history`. Pull out the fields above instead of reading it whole.
- It is JSON even though its `Content-Type` header says `text/html`.

## Speed test

A TorBox speed test downloads a test file from TorBox's CDN servers to the user's device. It shows which CDN is closest to the user and how fast their connection to it is.

### Which device to test

**Run the speed test on the device that is buffering or downloading slowly**, on the network it normally uses.

A speed test on a different device, such as a PC when the TV is the one buffering, answers a different question:

| Result on the other device | What it shows | What it does not show |
|---|---|---|
| Fast | The network can reach that speed, so the internet line at its peak is probably not the limit | That the buffering device has a fast connection. Its own link, such as Wi-Fi, or the device itself can still be the cause |
| Slow | The network itself is slow or busy right now | Whether the buffering device has a further problem of its own |

- A fast result on the other device moves suspicion to the buffering device and its link to the router. Go to the TV and Wi-Fi rows of "Most common causes".
- If the buffering device cannot run video-link-debugger, as with a TV or a phone, have the user open https://torbox.app/speedtest in a browser on that device if it has one.
- If only another device can be tested, say which device the result came from and what it does and does not show. Do not present it as the buffering device's speed.

### Which way to run it

| Your situation | What to do |
|---|---|
| You have the user's public IP address | Call the speedtest endpoint with it as `user_ip` |
| You do not have their IP, but you can run commands on the user's computer | Install video-link-debugger and run `video-link-debugger speedtest -n 5` |
| Neither | Tell the user you cannot get a speed test for them, and send them to https://torbox.app/speedtest |

### With the user's IP: the speedtest endpoint

`GET https://api.torbox.app/v1/api/speedtest?user_ip=<the user's public IP>` (no auth). With the TorBox MCP server connected, the `get_speedtest_files` tool takes the same parameters.

| Param | Notes |
|---|---|
| `user_ip` | Public IP address of the device that will download. Decides which server is marked closest |
| `region` | `all` (default), or one region code to return only that entry |
| `test_length` | `short` (default, a 100 MB file) or `long` (a 1 GB file) |

`data` is a list with one entry per CDN region. Each entry has `region`, `name`, `url` (the test file), `closest` and `coordinates`. The entry with `closest: true` is the server nearest to that IP.

- **Why `user_ip` matters.** Leave it out and the API uses the address the request came from. An agent or MCP server rarely runs on the user's device, so "closest" would mean closest to you.
- **A wrong IP is not rejected.** A made-up or malformed value, or a private address such as `192.168.1.10`, still returns `success: true` with some server marked closest. Only pass a public address you know is the user's.
- **Hand the file to the user.** Give them the `url` and `region` of the `closest: true` entry. They download it in a browser on the device that has the problem and read the speed there. Downloading it yourself measures your connection.
- An unknown `region` returns `ITEM_NOT_FOUND`. The list of regions changes, so read it from a call with `region=all` instead of from memory.

### On the user's computer: video-link-debugger

video-link-debugger is TorBox's open-source command-line tool: https://github.com/TorBox-App/video-link-debugger. It finds the closest CDN from the computer's own address, so it does not need the user's IP.

This option is for a shell on the user's own computer, on the network that has the problem. A cloud sandbox does not count. If that computer is not the device that buffers, read the result as described under "Which device to test".

Tell the user what you are installing, then install it:

```bash
# Linux and macOS
curl -fsSL https://raw.githubusercontent.com/TorBox-App/video-link-debugger/main/install.sh | bash
```

```powershell
# Windows (PowerShell)
powershell -c "irm https://raw.githubusercontent.com/TorBox-App/video-link-debugger/main/install.ps1 | iex"
```

Then run the speed test:

```bash
video-link-debugger speedtest -n 5
```

- `-n 5` tests the five closest CDNs, closest first. Each test file is downloaded twice, once over a single connection and once over four. The results are ranked by best speed, and the closest CDN is marked `*`.
- The run downloads about 1 GB (five 100 MB files, twice each). Warn a user on a metered or capped connection first.
- The installer puts the program in `~/.local/bin` (Linux and macOS) or `%LOCALAPPDATA%\video-link-debugger` (Windows). If the command is not found afterwards, run it by its full path, for example `~/.local/bin/video-link-debugger speedtest -n 5`.
- There is no build for Intel Macs. If the installer reports that, send the user to https://torbox.app/speedtest instead.
- The tool uploads the results to PrivateBin and prints a **Results URL**. Pass that URL on to the user so they can give it to TorBox support as their speed test result. Add `-P` to skip the upload if the user does not want one.

### Reading the numbers

Internet plans are sold in Mbps. Browsers and download tools usually show MB/s. Divide Mbps by 8 to compare them: a 100 Mbps plan tops out at about 12.5 MB/s before network overhead.

## Slow downloads and buffering

Article: https://support.torbox.app/en/articles/16168587-how-to-debug-slow-download-speeds

Symptoms: buffering while streaming a direct download link, download speeds below what the user's ISP provides, or a slow time to first byte.

Most buffering and slow-download reports come from the user's own device or connection, not from TorBox. Check the common causes first, then work through the steps.

### Most common causes

| Cause | Signs | What to try |
|---|---|---|
| The file is too large for the connection | A large or high-resolution file, and a speed test result below what that file needs (see "What a stream needs") | A smaller or lower-resolution version of the file. Raising the player's buffer cache size also makes playback steadier |
| Other devices are using the connection | It gets worse when other people or devices on the network stream, download, play games or update | Pause the other use and test again |
| Cellular data in a dead zone or slow area | The device is on mobile data, and the speed changes with where the user is | Move somewhere with better signal, or switch to Wi-Fi |
| The ISP or mobile provider is slowing the connection | Speeds are below what the plan promises on Speedtest.net as well as on the TorBox speed test | The user raises it with their provider. TorBox cannot change it |
| The TV is not powerful enough | Playback is on a smart TV or TV streaming device. Large, demanding files buffer while smaller ones play | A smaller or lower-resolution file, or a more capable device |
| Wi-Fi | The speed drops seemingly at random during playback or a download | Ethernet if possible. Otherwise move closer to the router or access point |

- More than one can apply at once, for example a 4K file on a TV over Wi-Fi.
- One good speed test does not rule out Wi-Fi, cellular or a busy network. Those change from minute to minute, so ask whether the slowdown comes and goes.
- A fast speed test on another device does not clear the buffering one (see "Which device to test").

### What a stream needs

TorBox's guide for streaming direct download links:

| Content | Connection | Device |
|---|---|---|
| High resolution such as 4K, large files | Strong, 75+ Mbps | Higher-end |
| Medium resolution such as 1080p, medium files | Strong, 50+ Mbps | Medium to high-end |
| 720p and below, small files | Strong, 25+ Mbps | Almost any modern device |

The connection figure is what has to reach that one device. A 25 Mbps line shared by a whole house, with several devices in use, leaves less than that for the stream.

### Steps

Work through these in order and stop when one fixes it.

1. **Check the status page** (see "Status page"). If a CDN or service incident is listed for the user's region, they wait for it to be resolved.
2. **Run a speed test** on the device that is buffering, on the network it uses (see "Speed test"). A result from another device does not stand in for it.
3. **Rule out the most common causes** above, using the speed test result. Ask what file they are playing or downloading, on which device, over which kind of connection, and what else is using the network.
4. **Test one clean direct download.** Use an item that is ready ("Download Ready" on the dashboard; in the API, `download_finished` and `download_present` are both `true`), pick one individual file, generate a new link, and open it in a browser.
   - Not a zip. Zips are slower by design (see "Slow zip downloads").
   - Not an item TorBox is still fetching. That speed depends on the seeders, the usenet provider or the hoster.
   - Not an old link. An expired or rate-limited link spoils the result.
5. **Remove everything in between**, then test the same link again:
   - Third-party apps used to generate or stream download links.
   - Download managers and apps that claim to speed downloads up.
   - VPNs, proxies, and anything else that changes network routing.
   - Custom DNS services, ad blockers, antivirus web protection, and router security features.
6. **Streaming only?** Open the direct download link in a player that plays URLs, such as VLC or MPV.
7. **Change the surroundings.** Restart the router. Try Ethernet instead of Wi-Fi. Try another device and another network. If it works somewhere else, the original device or connection is the cause.
8. **Use the recommended CDN.** After the speed test, the user selects the recommended CDN under CDN Selection in the Integration Settings section of https://torbox.app/settings (`cdn_selection` in the API settings), generates a new link and tests again. "Auto" uses the closest CDN and is the setting TorBox recommends in general. The regions are described at https://support.torbox.app/en/articles/10199645-torbox-cdn-hyperdrive.
9. **Run a single-connection test.** On https://speedtest.net, choose a server near the selected CDN and run the single-connection test. A normal multi-connection test can look fine while one download or stream is slow.
10. **Windows only.** Other applications sometimes disable TCP autotuning. The user opens Command Prompt as administrator and runs the command below, then restarts the browser or player and tests again.

    ```text
    netsh int tcp set global autotuninglevel=normal
    ```

If turning something off in step 5 fixed it, allow TorBox's domains in that product before turning it back on (see "TorBox is blocked").

### Testing a link with video-link-debugger

If you can run commands on the user's computer, the same tool that runs the speed test can do step 4 for you (install it as shown under "Speed test"):

```bash
video-link-debugger test "<direct download link>"
```

- It measures latency, time to first byte, seek times, and single- and multi-connection download speed for that one link, then prints a **Results URL**.
- This Results URL is the video-link-debugger result TorBox support asks for. It is a different result from the speed test one.
- The upload holds the link's host name and a blurred file name. It does not hold the link itself.

## Download links that stop working

Article: https://support.torbox.app/en/articles/15315517-why-are-my-download-links-not-working

A download link is valid for 3 hours. After that it expires and may stop working. An expired or rate-limited link shows up as:

- An "invalid presigned token" error when the link is opened.
- The download failing in the browser or download manager.
- HTTP 429, Too Many Requests.
- The download starting and then stopping partway through.

What to do:

- **Generate a new link**, from the dashboard or with `requestdl` in the API.
- **Limit connections.** In a download manager such as IDM or JDownloader, set the maximum connections to 4 or fewer. TorBox says this number may change later.
- **One link, one place.** Do not use the same link in more than one app, device or download manager at the same time. That triggers rate limits.
- **For a link that has to keep working**, such as one saved in a playlist or media library, use a permalink. The `torbox-api` skill describes it under "Download links".

## Slow zip downloads

Article: https://support.torbox.app/en/articles/15030073-why-are-zip-files-slow-downloading-to-my-computer

Zips are built on the fly and are normally slower than downloading files one by one. This is expected, not a fault.

| Reason | Detail |
|---|---|
| Many files | The more files in the zip, the longer it takes. File count matters as well as total size |
| One connection only | Individual files from the CDN accept several connections at once. A zip cannot |
| Two locations only | Zips are served from the main storage servers in the WNAM and WEUR regions. A user far from both gets lower speeds |
| Lower priority under load | Zips take a lot of compute to create. When the servers are busy, CDN traffic comes first |

- **A zip cannot be resumed.** Cancelling, pausing or losing the connection means starting again from the beginning.
- **What to do instead:** download the files individually, or move whole folders over WebDAV. The `torbox-webdav` skill covers that.
- Never judge a user's speed from a zip download.

## Queued downloads that do not start

Article: https://support.torbox.app/en/articles/10293822-why-do-queued-downloads-not-start

- A background process starts queued downloads **every 3 hours**. The user should wait at least 3 hours after adding one before treating it as stuck.
- That process watches server capacity. When capacity is low or usage is high it holds queued downloads back to leave room for more urgent ones.
- **To start one now:** the user opens the download on the dashboard and clicks "Force Start". In the API this is the `start` operation of `queued/controlqueued`.
- A forced start only works when the account has a free slot and the download passes TorBox's checks.

## Inactive downloads

Article: https://support.torbox.app/en/articles/10333785-why-is-my-download-inactive

TorBox removes unused downloads from storage to make room for others.

| Cause | What happened |
|---|---|
| Not downloaded within 30 days | An item that nobody downloads for 30 days after it is cached is removed |
| Failed download | An item that went inactive right after it was added hit an error. The dashboard says which kind |

- **Downloading resets the clock.** Each download of the item gives it another 30 days. Another TorBox user downloading the same item resets it too.
- **To keep an item, the user must download or stream it.**
- **WebDAV does not count.** Using files through WebDAV does not stop an item from going inactive.
- In the API, an item's `expires_at` shows when it will be removed if it stays unused.

## Cannot log in or sign up

Article: https://support.torbox.app/en/articles/9835830-i-cannot-log-in

The same steps apply to signing up.

| Problem | What to try |
|---|---|
| The captcha will not verify | Turn off ad blockers on torbox.app. Turn off the VPN. Switch between mobile data and Wi-Fi. Try a private (incognito) window. Try another browser. Remove extensions that might interfere |
| The sign-up email never arrives | Check spam and junk. Allow mail from account@torbox.app, notifications@torbox.app and contact@torbox.app. As a workaround, use the password reset link on the sign-in page, which gets past the email confirmation step, then sign in. If the email still never shows, contact support |
| The email link leads back to the login page | The link was already used or has expired (see below). Request a new one |
| Constant unknown errors | Check the status page (see "Status page"). It may be an API issue |

Why email links fail:

- **Each link works once**, whoever opens it. Mail apps that preview links (the iOS Mail app does), email forwarding services, and mail clients that scan links all open the link before the user does, which uses it up.
- **Each link expires after 15 minutes.**

The user should open a new link promptly and directly, from a mail client that does not open links for them.

## TorBox is blocked

Article: https://support.torbox.app/en/articles/12667085-torbox-is-being-blocked-by-my-anti-virus-software

Antivirus software, VPNs, ISPs and routers share block lists, and TorBox's domains are often put on them.

Symptoms:

- Alerts when opening a TorBox domain.
- TorBox domains refusing to load.
- SSL handshake errors.
- Content failing to play in third-party software.

Domains to allow:

```text
*.torbox.app
*.tb-cdn.cx
*.tb-cdn.io
*.tb-cdn.pw
*.tb-cdn.sh
*.tb-cdn.st
*.tb-cdn.to
*.tb-cdn.earth
```

Where the block usually comes from:

| Place | Examples |
|---|---|
| Software on the computer | Malwarebytes Browser Guard, Bitdefender |
| The ISP's security service | Spectrum Security Shield, Xfinity xFi Advanced Security, AT&T ActiveArmor, Verizon Home Network Protection, Virgin Media Web Safe, Starlink content filtering |
| A VPN's built-in filter | Surfshark CleanWeb, NordVPN Threat Protection, ExpressVPN Advanced Protection, PIA MACE, Proton VPN NetShield, IPVanish Threat Protection |
| The router | TP-Link HomeShield, Asus AiProtection, Netgear Armor, Linksys parental controls |

- Ask the user which of these they use. The article has steps for each product, and for more ISPs, VPNs and routers than are listed here. Send the user to the matching section instead of improvising menu paths.
- Add the domains to the product's allow list when it has one. Turn a protection off only when there is no allow list, and tell the user what they are giving up.
- After the change, the user restarts the router or reconnects the VPN where the article says to, then tests again.

## Contacting TorBox support

Support: https://torbox.app/contact

Urge the user to contact support when the steps for their problem did not fix it, when the problem keeps coming back, or when it is something only TorBox can change. Do not leave them retrying the same steps.

For slow speeds, support asks for all of these:

- The Results URL from `video-link-debugger test` run on a direct download link.
- The raw text of https://api.torbox.app/cdn-cgi/trace, opened on the affected device.
- The raw text of https://cf-debug.torbox.app, opened on the affected device.
- ISP, approximate location, device, operating system, browser or player, and whether the device is on Wi-Fi or Ethernet.
- The selected CDN, the expected speed, the actual speed, and whether other ready files have the same problem.
- The TorBox speed test result (what https://torbox.app/speedtest showed, or the Results URL from `video-link-debugger speedtest`) and the single-connection Speedtest.net result.

The trace and debug output go in as pasted text, not screenshots. Screenshots can cut off information support needs.

## Working with the user

- Ask what the problem happens on before suggesting anything: the device (a TV, phone or computer), the connection (Wi-Fi, Ethernet or cellular), the app, and for slow speeds the size and resolution of the file. Most of these fixes depend on it.
- Most slow-speed problems turn out to be on the user's side. Say what the checks show plainly and without blame, and do not point at TorBox unless the status page or the tests do.
- Give one step at a time and ask what happened. Do not hand over the whole list at once.
- Say plainly when something is expected behavior: zips are slow, queued downloads can take 3 hours or more to start, links expire after 3 hours, unused items are removed after 30 days.
- When you cannot run a speed test for the user, say so and give them https://torbox.app/speedtest. Do not report a speed or a closest CDN you did not measure for them.
- Report speeds in MB/s, and say which unit you mean when comparing against an internet plan in Mbps.
- If the `torbox-api` skill is installed, use it to read item state, request new links and change settings. If the `torbox-webdav` skill is installed, use it for WebDAV problems.
