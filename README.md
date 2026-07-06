# Bridge Service — France Student AI API

Service intermediaire qui expose une API REST compatible avec les harness IA (Pi, Codex, OpenGravity, OpenCode) pour communiquer avec le chatbot [ia.francestudent.org](https://ia.francestudent.org).

## Fonctionnalites

- **12 modeles IA** : GPT-5.5, Claude Opus 4, DeepSeek V3.2, Mistral Large 3, Kimi K2.5...
- **Streaming SSE** : reponse en temps reel via Server-Sent Events
- **Generation d'images** : detection auto + telechargement + stockage local renomme
- **Parsing complet** : texte, reasoning, code blocks, JavaScript integre, function calls
- **Retry automatique** : reconnexion SSE, token refresh, backoff exponentiel
- **Cross-platform** : Windows, Linux, macOS

## Installation

```bash
git clone https://github.com/<user>/bridge-service.git
cd bridge-service
pip install -r requirements.txt
```

## Configuration

```bash
# Linux / macOS
export FS_EMAIL="ton@email.com"
export FS_PASSWORD="ton_mot_de_passe"
export BIND_PORT=8765

# Windows (CMD)
set FS_EMAIL=ton@email.com
set FS_PASSWORD=ton_mot_de_passe
set BIND_PORT=8765

# Windows (PowerShell)
$env:FS_EMAIL="ton@email.com"
$env:FS_PASSWORD="ton_mot_de_passe"
$env:BIND_PORT="8765"
```

## Lancement

```bash
# Linux / macOS
./run.sh

# Windows
python bridge_server.py

# Avec custom port
python bridge_server.py
# puis ouvrir http://localhost:8765/health
```

## Endpoints

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Etat du service |
| `GET` | `/models` | Liste des modeles dispo |
| `POST` | `/auth/login` | Login (si pas en env var) |
| `GET` | `/auth/status` | Statut auth |
| `POST` | `/chat/completions` | Envoyer un prompt (streaming SSE) |
| `POST` | `/chat/<id>/message` | Message dans un chat existant |
| `GET` | `/chat/<id>` | Recuperer un chat |
| `GET` | `/chats?limit=20` | Lister les chats |
| `DELETE` | `/chat/<id>/delete` | Supprimer un chat |
| `GET` | `/chat/<id>/usage` | Token usage d'un chat |
| `POST` | `/upload` | Uploader un fichier |
| `GET` | `/images/<filename>` | Servir une image stockee |

## Utilisation avec un harness

```bash
# Chat simple
curl -X POST http://localhost:8765/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"message": "Explique la theorie de la relativite", "agentId": 101}'

# Generation d'image
curl -X POST http://localhost:8765/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"message": "Genere un chat cyberpunk", "agentId": 101}'

# Changer de modele
curl -X POST http://localhost:8765/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"message": "Ecrit du code Python", "model": "claude-sonnet-4-6"}'
```

## Reponse format

```json
{
  "chatId": "uuid",
  "messageId": "uuid",
  "model": "gpt-5.5",
  "content": {
    "text": "reponse complete...",
    "reasoning": "raisonnement si dispo",
    "codeBlocks": [{"language": "python", "code": "..."}],
    "javascriptBlocks": [{"code": "...", "source": "script_tag"}],
    "functionCalls": [],
    "webSearchCalls": []
  },
  "downloadedImages": [
    {
      "filename": "chatid_msgid_imgid_timestamp.png",
      "localPath": "/abs/path/to/image.png",
      "downloadUrl": "http://localhost:8765/images/..."
    }
  ],
  "tokenUsage": {
    "promptTokenCount": 100,
    "candidatesTokenCount": 200,
    "totalTokenCount": 300
  },
  "isFinished": true,
  "finishedReason": "completed"
}
```

## Structure du projet

```
bridge-service/
├── bridge_server.py     # Serveur Flask principal
├── auth.py              # Authentification (login, token, refresh)
├── api_client.py        # Client API France Student
├── sse_parser.py        # Parser SSE (tous les events)
├── image_handler.py     # Download + stockage images
├── config/
│   └── config.py        # Configuration
├── storage/
│   └── images/          # Images telechargees
├── requirements.txt     # Dependances Python
├── run.sh               # Script de lancement Linux/macOS
├── run.bat              # Script de lancement Windows
├── .env.example         # Template variables
└── .gitignore           # Fichiers exclus du repo
```

## Securite

- Les credentials sont passes via variables d'environnement (`FS_EMAIL`, `FS_PASSWORD`)
- Le token API est stocke localement dans `store.json` (auto-refresh)
- `store.json` et `.env` sont dans `.gitignore`
- Le dossier `storage/images/` est exclu du repo
- Les logs ne contiennent pas de donnees sensibles

## Licence

MIT
