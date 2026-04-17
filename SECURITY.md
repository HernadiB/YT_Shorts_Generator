# Security Policy

## Supported Branch

Security fixes target the `development` branch.

## Reporting A Vulnerability

Use GitHub Security Advisories for private reports:

https://github.com/HernadiB/YT_Shorts_Generator/security/advisories/new

Do not include OAuth tokens, API keys, `token.json`, `channel_token.json`,
`client_secret.json`, or generated media with private information in public
issues, pull requests, or discussions.

## Local Secrets

The following files are local-only and must remain uncommitted:

- `.env`
- `config.json`
- `client_secret.json`
- `token.json`
- `channel_token.json`
- `channel_state.json`
