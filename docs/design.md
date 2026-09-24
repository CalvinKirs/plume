# Plume design notes

## Goal
Minimal: one button in Gmail compose, one local send service.

## Flow
1. Extension reads the draft (from, to, cc, bcc, subject, body, threading headers).
2. Sends it to the local host: Chrome native messaging (default, host started on demand) or `POST /send` on 127.0.0.1 (HTTP mode).
3. Server submits via `mail-relay.apache.org` using the LDAP account.
4. Server inserts the sent message into Gmail (Sent label) via the Gmail API and the extension removes the draft.

## Security
- Native host: only the pinned extension id may launch it; no port is opened. HTTP mode: 127.0.0.1 only, Origin check and bearer token.
- The LDAP password lives in a 0600 config file (native mode has no shell environment). Moving it to the OS keychain is future work.

## Open questions
- Does mail-relay require From to equal the authenticated user?
- Gmail OAuth: token lifetime for an app in "testing" status (possibly 7 days).
- ~~Port 587/465 reachable?~~ Checked from the dev host: both accept TLS and offer AUTH PLAIN LOGIN (one transient DNS failure on the first 587 try).
- Gmail OAuth for an unverified app in testing status: refresh token may expire after 7 days; `python3 -m plume auth` again if archive errors mention authorization.
- Threading and quoting of replies to list mail.
