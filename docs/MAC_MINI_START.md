# Mac Mini Start Guide

This guide is for continuing CyberAgent iOS extension development from the Mac mini while this Windows PC stays as the main CyberAgent node.

## 1. Clone Repo

```bash
git clone https://github.com/FlEtsv/cyber-agent.git
cd cyber-agent
```

## 2. Understand The Existing Deployment

The Cloud Run relay is already deployed:

```text
https://cyberagent-relay-819820880956.us-central1.run.app
```

Check if the relay and Windows PC are alive:

```bash
curl https://cyberagent-relay-819820880956.us-central1.run.app/api/status
```

Expected when the Windows PC is running CyberAgent:

```json
{"relay":true,"pc_online":true}
```

Check auth mode:

```bash
curl https://cyberagent-relay-819820880956.us-central1.run.app/api/auth/status
```

Expected current mode:

```json
{"setup_done":true,"totp_required":false}
```

## 3. Mobile PWA Access

Open in iPhone Safari:

```text
https://cyberagent-relay-819820880956.us-central1.run.app/login
```

Then add it to Home Screen if desired.

## 4. iOS Native App Development

Create a new Xcode project:

- Platform: iOS
- App type: SwiftUI
- Name suggestion: `CyberAgentMobile`
- Bundle ID suggestion: `com.steve.cyberagent.mobile`
- Minimum iOS: current iPhone supported version

Initial constants:

```swift
let relayBaseURL = URL(string: "https://cyberagent-relay-819820880956.us-central1.run.app")!
```

First screens:

- Login.
- Status.
- Capabilities.
- Activity log.

First network calls:

```http
GET /api/status
GET /api/auth/status
POST /api/auth/login
```

Later WebSocket:

```text
wss://cyberagent-relay-819820880956.us-central1.run.app/mobile-node
```

`/mobile-node` does not exist yet. It is part of the next implementation phase.

## 5. Keep Windows PC As Main Node

Do not move the main agent runtime to the Mac mini for now.

The PC currently owns:

- Ollama local model.
- Desktop CyberAgent app.
- Local tools.
- RAG/database state.
- Relay host websocket.

PC path:

```text
C:\Users\steve\cyber-llm\agent-native
```

PC LAN IP observed:

```text
192.168.18.240
```

Use the LAN IP only for diagnostics. Use Cloud Run `/api/status` as the normal liveness source.

## 6. Free Apple ID Beta Flow

For this private beta:

- Use Xcode on Mac mini.
- Connect iPhone.
- Build and run directly on the iPhone.
- Reinstall from Xcode when the free provisioning expires.

Do not pay Apple Developer Program until the native extension proves useful.

## 7. First Implementation Ticket

Implement a SwiftUI app that:

1. Stores relay URL.
2. Calls `/api/status`.
3. Shows `relay` and `pc_online`.
4. Shows login form.
5. Stores authenticated session securely.
6. Has an activity log screen.

Second ticket:

1. Add `/mobile-node` to Cloud Run relay.
2. Add iOS WebSocket connection.
3. Register capabilities.
4. Show mobile node in PC agent tools.

