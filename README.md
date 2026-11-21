# TorBox AI Skills

Skills that teach AI agents how to work with [TorBox](https://torbox.app).

Each skill is a folder with a `SKILL.md` file in the open [Agent Skills](https://agentskills.io) format. They install as a plugin in Claude Code and can be copied into any other agent that reads that format.

## Skills

| Skill                                                              | What the agent learns                                                                                                                                   |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`torbox-api`](skills/torbox-api/SKILL.md)                         | How to call the TorBox API: add torrents, usenet and web downloads, check the cache, get download links, and handle error codes and rate limits.        |
| [`torbox-webdav`](skills/torbox-webdav/SKILL.md)                   | How to use TorBox WebDAV: connect a client or media player, list and download files, and fix login problems and missing or stale files.                 |
| [`torbox-troubleshooting`](skills/torbox-troubleshooting/SKILL.md) | How to diagnose TorBox problems: buffering and slow speeds, speed tests, broken links, queued or inactive downloads, login trouble and blocked domains. |

## Install in Claude Code

This repository is a plugin marketplace named `torbox-skills`. It holds one plugin, `torbox`, which bundles every skill listed above.

On Claude Code 2.1.275 or later, one command adds the marketplace and installs the plugin:

```text
/plugin install torbox --marketplace TorBox-App/ai-skills
```

On earlier versions, add the marketplace first:

```text
/plugin marketplace add TorBox-App/ai-skills
/plugin install torbox@torbox-skills
```

Then run `/reload-plugins` or start a new session.

The same commands work from your shell with `claude` in front, for example `claude plugin install torbox --marketplace TorBox-App/ai-skills`.

## Install in other agents

The plugin above is specific to Claude Code. The skill itself is plain Markdown with nothing tied to one agent, so any agent that supports Agent Skills can use it. Copy the skill's folder into the directory your agent loads skills from.

[Codex](https://learn.chatgpt.com/docs/build-skills), [Gemini CLI](https://geminicli.com/docs/cli/skills/), [Cursor](https://cursor.com/docs/context/skills) and [GitHub Copilot](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) all load skills from `~/.agents/skills/` for every project, or `.agents/skills/` inside one project:

```bash
git clone https://github.com/TorBox-App/ai-skills.git
mkdir -p ~/.agents/skills
cp -R ai-skills/skills/torbox-api ~/.agents/skills/
```

Claude Code without the plugin uses `~/.claude/skills/` or `.claude/skills/` instead. For any other agent, look up its skills folder in its documentation. The [Agent Skills client list](https://agentskills.io/clients) shows many of the agents that support the format.

If your AI tool has no skills support, attach `skills/torbox-api/SKILL.md` to the conversation or paste its contents in. It then works as ordinary instructions for that one conversation.

## Use

Ask for what you want. The agent loads the skill on its own when a request involves the TorBox API:

- "Check which of these magnet links are cached on TorBox and add the cached ones."
- "Why does TorBox answer `ACTIVE_LIMIT` when I add a torrent?"
- "Write a script that adds an NZB to TorBox and prints a download link when it finishes."

In Claude Code you can also load it yourself: `/torbox:torbox-api` if you installed the plugin, or `/torbox-api` if you copied the folder.

The agent needs your TorBox API key, which is in your [TorBox settings](https://torbox.app/settings). The key gives full access to your account, so only hand it to an agent you trust. The `curl` example in the skill reads it from a `TORBOX_API_KEY` environment variable. You can set that, or give the agent the key when it asks.

## Update

Every commit to this repository is a new version of the plugin. To get the latest:

```bash
claude plugin marketplace update torbox-skills
claude plugin update torbox@torbox-skills
```

To have Claude Code do this for you, run `/plugin`, open **Marketplaces**, and enable auto-update for `torbox-skills`.

## Repository layout

```text
.claude-plugin/
  marketplace.json      the torbox-skills marketplace
  plugin.json           the torbox plugin
skills/
  torbox-api/
    SKILL.md
  torbox-troubleshooting/
    SKILL.md
  torbox-webdav/
    SKILL.md
.github/
  scripts/validate_skills.py
  workflows/validate.yml
```

## Add or change a skill

1. Create `skills/<skill-name>/SKILL.md`. Name the folder with lowercase letters, digits and hyphens.
2. Start the file with frontmatter. `name` must be identical to the folder name. `description` says what the skill does and when to use it, in 1024 characters or fewer, because agents decide from it whether to load the skill.

   ```markdown
   ---
   name: skill-name
   description: What this skill does and when to use it.
   ---

   # Instructions for the agent
   ```

3. Write the instructions below the frontmatter. Keep `SKILL.md` under 500 lines and move long reference material into separate files in the same folder.
4. Add the skill to the table in this README.
5. Run the checks:

   ```bash
   pip install pyyaml
   python .github/scripts/validate_skills.py
   claude plugin validate .
   ```

You do not need to edit `marketplace.json` or `plugin.json`. The `torbox` plugin loads every folder in `skills/`.

The first check also runs in GitHub Actions on every pull request and every push to `main`. It fails when a `SKILL.md` is missing, its frontmatter does not parse, `name` differs from the folder name, or `description` is empty.

`claude plugin validate` warns that the plugin has no version. Leave it that way. Without a `version`, Claude Code treats each commit as a new version, so users get changes as soon as they update. With one, they stay on their installed copy until someone changes the number.

## Support

- TorBox API reference: <https://api-docs.torbox.app>
- A skill gives wrong or outdated instructions: open an issue in this repository.
- Anything about your TorBox account: <contact@torbox.app>
