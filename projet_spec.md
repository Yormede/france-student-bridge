---
projet: france-student-bridge
version: "1.1.0"
statut: operationnel
date_creation: 2026-07-06
date_maj: 2026-07-11
deploiement: ct104 (port 8765)
repo: https://github.com/Yormede/france-student-bridge
tags: [bridge, openai-compatible, france-student, sse, puppeteer, docker]
---

# France Student Bridge — Spécification technique

## 1. Utilité du projet

Le **France Student Bridge** est un service intermédiaire qui transforme le chatbot IA gratuit de **France Student** ([ia.francestudent.org](https://ia.francestudent.org)) en une **API REST locale compatible OpenAI**.

> **Problème** : France Student ne fournit pas de clé API officielle. L'accès se fait uniquement via portail web (SSO WHMCS + Next.js).
> **Solution** : Le bridge s'authentifie automatiquement via navigateur headless (Puppeteer), récupère un JWT, et expose les 11 modèles d'IA derrière une API locale standard.

### Cas d'usage
- Brancher un harness IA (OpenCode, Codex, Cursor, Pi) sur les modèles France Student gratuitement
- Utiliser Claude Sonnet 5, GPT-5.6, DeepSeek-V3.2, etc. sans clé API payante
- Héberger un point d'accès multi-modèles sur son homelab

---

## 2. Architecture technique

```
┌──────────────────────────────────────────────────────────────┐
│                   HARNES IA (OpenCode/Codex/Cursor)          │
│              POST /v1/chat/completions (format OpenAI)        │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP localhost:8765
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   BRIDGE SERVICE (Flask)                     │
│  bridge_server.py — point d'entrée REST                      │
│  ├─ openai_adapter.py — conversion OpenAI <-> bridge          │
│  ├─ tool_loop.py — boucle function_call client-side           │
│  └─ image_handler.py — download images générées               │
│                                                              │
│  auth.py ─── JWT SSO via get_jwt.js (Puppeteer headless)      │
│  store.json ─ persistance token + expiry                     │
│                                                              │
│  api_client.py ── client httpx (sync + streaming SSE)         │
│  sse_parser.py ── parse response.output_text.delta etc.       │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTPS + Bearer JWT
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              api.francestudent.org (Spring Boot)              │
│  POST /chats/stream   ── crée chat + stream SSE              │
│  POST /chats/{id}     ── continue un chat                     │
│  GET  /chats/agents   ── liste des modèles                    │
│  GET  /chats/{id}/stream?last_event_id ── reconnect SSE       │
└──────────────────────────────────────────────────────────────┘
```

### Flux d'authentification (SSO)
```
1. Puppeteer lance Chromium headless (anti-detect)
2. GET  my.francestudent.org/login.php
3. POST login (email/password WHMCS) → session cookies
4. GET  ia.francestudent.org/login → click "Sign in with France Student"
5. SSO redirect chain (WHMCS → IA portal)
6. GET  ia.francestudent.org/api/auth/api-token → {accessToken: JWT}
7. JWT parsé (base64 payload) → expiry extraite → store.json
8. JWT utilisé pour tous les appels API suivants (Bearer Authorization)
```

### Flux d'un chat (SSE streaming)
```
Client → bridge_server.py /v1/chat/completions
  → openai_adapter.openai_messages_to_text(messages)
  → api_client.create_chat(message, agent_id) → httpx.stream POST /chats/stream
    → sse_parser.parse_sse_stream(response) → yield events
    → extract_output_from_events(events) → {text, reasoning, imageItems, ...}
  → openai_adapter.openai_response_to_sse(output) → format OpenAI
  → Response SSE (data: {...}\n\n) ou JSON
```

---

## 3. Liste des fichiers

### Cœur du bridge (Python)
| Fichier | Lignes | Rôle |
|---|---|---|
| `bridge_server.py` | 531 | Serveur Flask — point d'entrée REST, endpoints OpenAI-compatibles |
| `auth.py` | 140 | Gestion JWT — Puppeteer SSO + parsing expiry + persistance store.json |
| `api_client.py` | 152 | Client HTTP httpx vers api.francestudent.org (sync + streaming SSE) |
| `sse_parser.py` | 229 | Parsing flux SSE temps réel + extraction output (text, reasoning, images, tools) |
| `openai_adapter.py` | 138 | Conversion messages/réponses OpenAI <-> format bridge |
| `tool_loop.py` | 186 | Boucle tools client-side (function_call → tool_result → function_call) |
| `image_handler.py` | 112 | Téléchargement + stockage local des images générées |

### Auth / SSO (Node.js/Puppeteer)
| Fichier | Rôle |
|---|---|
| `get_jwt.js` | Script Puppeteer — login WHMCS → SSO IA portal → capture JWT |
| `web_search.js` | Web search anti-detect via DuckDuckGo HTML (Obscura-style) |
| `web_search_tool.py` | Wrapper Python pour appeler `web_search.js` depuis un tool |

### Configuration
| Fichier | Rôle |
|---|---|
| `config/config.py` | URLs, timeouts, variables d'env, constantes |
| `.env` | Credentials (FS_EMAIL, FS_PASSWORD, BIND_HOST, BIND_PORT) |
| `.env.example` | Template `.env` |
| `.gitignore` | Exclut `__pycache__`, `.env`, `store.json`, `storage/images/*` |
| `requirements.txt` | Dépendances Python : httpx, flask, aiofiles, python-multipart |
| `package.json` | Dépendances Node : puppeteer-core |

### Déploiement Docker
| Fichier | Rôle |
|---|---|
| `Dockerfile` | Image Alpine (Python 3.12 + Chromium + Node + puppeteer-core) |
| `docker-compose.yml` | Service host network, restart unless-stopped, volumes storage + store.json |
| `deploy_docker.sh` | Script de déploiement sur le host ct104 |

### Lancement local
| Fichier | Rôle |
|---|---|
| `run.sh` | Lancement Linux/macOS (exporte vars + python bridge_server.py) |
| `run.bat` | Lancement Windows |

### Tests
| Fichier | Rôle |
|---|---|
| `test_bridge.js` | Test JS du pont : /health, /models, chat stream/non-stream |
| `test_agentique.py` | Test tool calling + web search sur les 11 modèles |
| `test_websearch.py` | Test web search BTC sur les 6 modèles agentiques |
| `test_obscura_agent.py` | Boucle agentique complète (tool → Puppeteer → réponse) |

### Runtime (persistant)
| Fichier | Rôle |
|---|---|
| `store.json` | JWT + expiry (recréé automatiquement) |
| `storage/images/` | Images générées téléchargées |

---

## 4. Endpoints API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | État du service + auth + modèles en cache |
| `GET` | `/auth/status` | Statut authentification + email (masqué) |
| `POST` | `/auth/login` | Authentification manuelle (force refresh JWT) |
| `GET` | `/v1/models` | Liste OpenAI-compatible |
| `POST` | `/v1/chat/completions` | Chat OpenAI-compatible (tools, stream, model) |
| `GET` | `/models` | Liste native bridge |
| `POST` | `/chat/completions` | Chat natif (message, agentId, enableWebSearch, stream) |
| `POST` | `/chat/{id}/message` | Continue un chat existant |
| `GET` | `/chat/{id}` | Détail d'un chat |
| `GET` | `/chats` | Historique des chats (cursor pagination) |
| `DELETE` | `/chat/{id}/delete` | Supprime un chat |
| `GET` | `/chat/{id}/usage` | Consommation tokens |
| `POST` | `/upload` | Upload fichier/image |
| `GET` | `/images/{filename}` | Sert image générée |

---

## 5. Modèles disponibles (testé 11/07/2026)

| ID | Modèle | Provider | Tools | Web | Agentic |
|---|---|---|---|---|---|
| 64 | gpt-5.6-sol ★ | openai | ✅ | ✅ | ✅ |
| 65 | gpt-5.6-luna | openai | ❌ | ❌ | ❌ |
| 66 | gpt-5.6-terra | openai | ✅ | ✅ | ✅ |
| 101 | gpt-5.5 | openai | ✅ | ✅ | ✅ |
| 63 | claude-sonnet-5 | anthropic | ✅ | ✅ | ✅ |
| 100 | claude-opus-4-8 | anthropic | ✅ | ✅ | ✅ |
| 51 | claude-haiku-4-5 | anthropic | ✅ | ✅ | ✅ |
| 40 | DeepSeek-V3.2 | DeepSeek | XML | ❌ | partiel |
| 43 | Mistral-Large-3 | Mistral | ✅ | ❌ | partiel |
| 42 | Kimi-K2.5 | Kimi | ✅ | ❌ | partiel |
| 60 | FW-GLM-5 | xAi | ❌ | ❌ | ❌ |

**Outils natifs** (format `<function_call>`) : DeepSeek-V3.2, Mistral-Large-3, Kimi-K2.5, FW-GLM-5

---

## 6. Dépendances

### Python (`requirements.txt`)
- `httpx>=0.24.0` — client HTTP async + streaming SSE
- `flask>=3.0.0` — serveur REST
- `aiofiles>=23.0.0` — I/O async pour images
- `python-multipart>=0.0.6` — upload de fichiers

### Node.js (`package.json`)
- `puppeteer-core@^23.0.0` — contrôle Chromium sans le télécharger

### Système (Docker)
- `python:3.12-alpine`
- `chromium` + `nss` `freetype` `harfbuzz` `ttf-freefont`
- `nodejs` `npm`
- Vars : `PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true`, `CHROME_PATH=/usr/bin/chromium`

---

## 7. Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `FS_EMAIL` | (requis) | Email du compte France Student |
| `FS_PASSWORD` | (requis) | Mot de passe du compte |
| `BIND_HOST` | `0.0.0.0` | Host d'écoute |
| `BIND_PORT` | `8765` | Port d'écoute |
| `CHROME_PATH` | `/usr/bin/chromium` | Chemin binaire Chromium (Puppeteer) |

---

## 8. Déploiement

### Mode direct (ct104 actuel)
```bash
cd /workspace/france-student-bridge
export FS_EMAIL=... FS_PASSWORD=... CHROME_PATH=/usr/bin/chromium-browser
python3 bridge_server.py
```
Auto-restart via cron `@reboot` (configuré sur ct104).

### Mode Docker (sur le host LXC, pas dans le container opencode)
```bash
cd /workspace/france-student-bridge
FS_EMAIL=... FS_PASSWORD=... ./deploy_docker.sh
```

> **⚠** Docker build/run impossible depuis le container OpenCode (DinD sans `CAP_SYS_ADMIN`)). Executer `deploy_docker.sh` sur le host ct104 directement.

---

## 9. Limitations connues

- **Obscura** : binary précompilé nécessite glibc (V8). Build échoue sur Alpine/musl. Puppeteer anti-detect (`--disable-blink-features=AutomationControlled`) utilisé en remplacement.
- **DeepSeek-V3.2** : outils en XML natif (`<invoke>`), parser bridge à adapter (reconnu par tool_loop mais pas converti en tool_calls OpenAI).
- **FW-GLM-5, gpt-5.6-luna** : ne répondent pas au prompt de tools (format incompatible).
- **JWT expiry** : le JWT expire après ~5 min (claim `exp`). Renouvellement automatique via Puppeteer au prochain appel.
- **Flask dev server** : Flask sert en mode dev. Pour la prod, utiliser gunicorn ou waitress.

---

## 10. Historique des versions

| Version | Date | Changements |
|---|---|---|
| 1.0.0 | 06/07/2026 | Version initiale (clone GitHub) |
| 1.1.0 | 10/07/2026 | Correction auth (Puppeteer SSO), endpoint /chats/stream, streaming httpx, Dockerfile, deploy_docker.sh |
| 1.1.1 | 11/07/2026 | Tests agentiques, web search Puppeteer (Obscura-style), mise à jour liste modèles (11), web_search.js, tests |

---

## 11. Auteur

**AhmiSVG** (Yormede sur GitHub) — [github.com/Yormede](https://github.com/Yormede)

> Projet Open Source MIT — reverse-engineering du frontend France Student. Non affilié à France Student. Peut cesser de fonctionner si l'API change.