<p align="center">
  <img src="https://img.shields.io/badge/status-operational-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/models-10%2F10-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/python-3.8%2B-yellow?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20Mac-purple?style=for-the-badge" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" />
</p>

<p align="center">
  <h1 align="center">France Student AI Bridge</h1>
  <p align="center"><i>Transform your favorite AI harness into a multi-model powerhouse —<br>powered by France Student's free chatbot API.</i></p>
</p>

---

## C'est quoi France Student ?

**[France Student](https://ia.francestudent.org)** est un chatbot IA en ligne gratuit propose par l'association **France Student**. Il donne acces a **12 modeles d'IA** differents — Claude, DeepSeek, Mistral, Kimi, GPT et plus — via une interface web, sans abonnement payant.

> **Pour s'inscrire** : va sur [ia.francestudent.org](https://ia.francestudent.org) → clique sur "Se connecter" → connecte-toi avec ton compte France Student (gratuit).

---

## C'est quoi ce projet ?

Ce **Bridge Service** est un serveur local qui fait le pont entre ton **harness IA prefere** (OpenCode, Pi, Codex, OpenGravity, Cursor...) et le chatbot France Student. Il expose une API REST propre qui traduit tes requetes en appels vers France Student, et te renvoie les reponses — texte, code, raisonnement, images generees — dans un format standard.

> **En clair** : ton harness peut maintenant parler a GPT-5.6, Claude Sonnet 5, DeepSeek V3.2 et 7 autres modeles, gratuitement, sans quitter ton terminal.

---

## Modeles disponibles (teste le 10/07/2026)

| Statut | Modele | Fournisseur | ID |
|--------|--------|-------------|-----|
| | **gpt-5.6-sol** | OpenAI | `64` (defaut) |
| | **gpt-5.6-luna** | OpenAI | `65` |
| | **gpt-5.6-terra** | OpenAI | `66` |
| | **claude-sonnet-5** | Anthropic | `63` |
| | **claude-opus-4-8** | Anthropic | `100` |
| | **claude-haiku-4-5** | Anthropic | `51` |
| | **DeepSeek-V3.2** | DeepSeek | `40` |
| | **Mistral-Large-3** | Mistral | `43` |
| | **Kimi-K2.5** | Kimi | `42` |
| | **FW-GLM-5** | xAi | `60` |

> Les 10 modeles sont actifs et fonctionnels.

---

## Tutoriel debutant (zero code)

Tu n'as jamais touche a un terminal ? Pas de panique. Suis ces etapes dans l'ordre.

### Etape 1 — Installer Python

**Windows** : va sur [python.org](https://www.python.org/downloads/), telecharge la derniere version, lance l'installeur, et **coche la case "Add Python to PATH"** avant de cliquer Installer.

**Mac** : ouvre le Terminal (Cmd+Espace → taper "Terminal") et colle :
```bash
brew install python3
```

**Linux** : Python est deja installe. Ouvre juste ton terminal.

> Pour verifier que Python est installe : tape `python --version` dans le terminal. Tu dois voir `Python 3.x.x`.

### Etape 2 — Telecharger le projet

Clique sur le bouton vert **"Code"** en haut de cette page, puis **"Download ZIP"**.

Extrais le fichier ZIP dans un dossier (par exemple `Bureau/bridge-service`).

> Alternative : dans un terminal, tape :
> ```bash
> git clone https://github.com/Yormede/france-student-bridge.git
> cd france-student-bridge
> ```

### Etape 3 — Installer les dependances

Ouvre un terminal (ou PowerShell sur Windows) **dans le dossier du projet** :

```bash
pip install -r requirements.txt
```

Tu vas voir des lignes defiler. Attends que ca finisse.

### Etape 4 — Configurer ton compte

Recupere ton email et ton mot de passe France Student (ceux avec lesquels tu te connectes sur le site).

**Sur Windows (PowerShell) :**
```powershell
$env:FS_EMAIL="ton.email@exemple.com"
$env:FS_PASSWORD="ton_mot_de_passe"
```

**Sur Mac / Linux :**
```bash
export FS_EMAIL="ton.email@exemple.com"
export FS_PASSWORD="ton_mot_de_passe"
```

> Ces infos restent sur ton ordinateur. Personne d'autre ne les voit.

### Etape 5 — Lancer le service

**Windows** : double-clique sur `run.bat`

**Mac / Linux** : dans le terminal, tape :
```bash
./run.sh
```

Tu devrais voir :
```
Bridge Service demarre sur http://0.0.0.0:8765
```

**Laisse cette fenetre ouverte.** Le service tourne en arriere-plan. Pour l'arreter, fais `Ctrl+C`.

### Etape 6 — Tester que ca marche

Ouvre un **deuxieme terminal** (ne ferme pas le premier) et tape :

```bash
curl http://localhost:8765/health
```

Si tu vois `{"status":"ok","authenticated":true}` → tout fonctionne.

### Etape 7 — Envoyer ton premier message

```bash
curl -X POST http://localhost:8765/chat/completions ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"Explique-moi le big bang en 2 phrases\",\"agentId\":50,\"stream\":false}"
```

> Sur Mac/Linux, remplace `^` par `\` a la fin de chaque ligne.

Tu recevras une reponse de Claude, DeepSeek, ou du modele que tu as choisi.

---

## Guide utilisateur avance (pour les devs)

### Installation rapide

```bash
git clone https://github.com/Yormede/france-student-bridge.git
cd france-student-bridge
pip install -r requirements.txt
```

### Lancement

```bash
# Linux / macOS
FS_EMAIL="ton@email.com" FS_PASSWORD="tonmdp" ./run.sh

# Windows
$env:FS_EMAIL="ton@email.com"; $env:FS_PASSWORD="tonmdp"; python bridge_server.py
```

### Utilisation API

```bash
# Lister les modeles
curl http://localhost:8765/models

# Chat simple (JSON, pas de streaming)
curl -X POST http://localhost:8765/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"message":"Ecris une fonction quick sort en Python","agentId":50,"stream":false}'

# Chat streaming (SSE, temps reel)
curl -X POST http://localhost:8765/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"message":"Compte de 1 a 10","agentId":40}'

# Choisir un modele par son nom
curl -X POST http://localhost:8765/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"message":"Qui est Alan Turing ?","model":"claude-opus-4-8","stream":false}'

# Envoyer un message dans un chat existant
curl -X POST http://localhost:8765/chat/abc123/message \
  -H "Content-Type: application/json" \
  -d '{"message":"Continue","agentId":50}'

# Uploader un fichier
curl -X POST http://localhost:8765/upload \
  -F "file=@mon_image.png"
```

### Tous les endpoints

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Etat du service + auth |
| `GET` | `/models` | Modeles disponibles |
| `POST` | `/auth/login` | Authentification manuelle |
| `GET` | `/auth/status` | Verifier l'auth |
| `POST` | `/chat/completions` | **Chat principal** (streaming ou JSON) |
| `POST` | `/chat/{id}/message` | Message dans un chat existant |
| `GET` | `/chat/{id}` | Historique d'un chat |
| `GET` | `/chats` | Liste des chats |
| `DELETE` | `/chat/{id}/delete` | Supprimer un chat |
| `GET` | `/chat/{id}/usage` | Consommation tokens |
| `POST` | `/upload` | Uploader fichier/image |
| `GET` | `/images/{filename}` | Servir image generee |

### Format de reponse

```json
{
  "chatId": "uuid",
  "messageId": "uuid",
  "model": "claude-sonnet-4-6",
  "modelProvider": "anthropic",
  "content": {
    "text": "Le big bang est la theorie...",
    "reasoning": "Je vais expliquer simplement...",
    "codeBlocks": [{"language": "python", "code": "def quicksort..."}],
    "javascriptBlocks": [],
    "functionCalls": [],
    "webSearchCalls": []
  },
  "downloadedImages": [
    {
      "filename": "chat_msg_img_20260706_171635.png",
      "localPath": "/home/user/.../image.png",
      "downloadUrl": "http://localhost:8765/images/chat_msg_img_20260706_171635.png",
      "sizeBytes": 948005
    }
  ],
  "tokenUsage": {
    "promptTokenCount": 100,
    "candidatesTokenCount": 200,
    "totalTokenCount": 300,
    "reasoningTokenCount": 50
  },
  "isFinished": true,
  "finishedReason": "completed"
}
```

---

## Guide pour les IA / Harness

Tu es une IA (OpenCode, Claude Code, Pi, Codex, Cursor...) et tu veux utiliser ce bridge ? Voici comment.

### Connexion au bridge

Le bridge expose une API HTTP locale. Pas besoin de SDK, juste `fetch()` ou `curl`.

```python
# Exemple Python pour ton harness
import requests

def chat(message, agent_id=50, stream=False):
    """Appelle France Student via le bridge local."""
    r = requests.post(
        "http://localhost:8765/chat/completions",
        json={"message": message, "agentId": agent_id, "stream": stream}
    )
    r.raise_for_status()
    return r.json()

# Utilisation
reponse = chat("Explique le paradoxe de Fermi en 3 phrases", agent_id=100)
print(reponse["content"]["text"])
print(f"Modele utilise: {reponse['model']}")
print(f"Tokens: {reponse['tokenUsage']['totalTokenCount']}")
```

```javascript
// Exemple JavaScript
async function chat(message, agentId = 50, stream = false) {
  const res = await fetch("http://localhost:8765/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, agentId, stream })
  });
  return res.json();
}
```

### Architecture cible

```
[Harnass IA (Pi/Codex/OpenCode)]
          |
          v
  [Bridge Service :8765]  ←  Ce projet
          |
          v
  [api.francestudent.org]  ←  Backend France Student
          |
          v
  [Claude | DeepSeek | Mistral | Kimi | GPT | ...]
```

### Parametres de `/chat/completions`

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `message` | string | requis | Le prompt a envoyer |
| `agentId` | int | auto | ID du modele (50=Claude Sonnet par defaut) |
| `model` | string | - | Nom du modele (alternative a `agentId`) |
| `stream` | bool | true | `true`=SSE streaming, `false`=JSON |
| `images` | array | [] | UUIDs d'images uploadees |
| `files` | array | [] | IDs de fichiers uploades |
| `enableWebSearch` | bool | false | Activer la recherche web |

### Detection d'erreurs

Si `finishedReason` vaut `"error"`, le champ `errorMessage` contient le detail. Cela arrive souvent quand le modele est overload (503) ou indisponible.

```python
reponse = chat("Hello", agent_id=101)
if reponse["finishedReason"] == "error":
    print(f"Erreur: {reponse['errorMessage']}")
    # Reessaie avec un autre modele
    reponse = chat("Hello", agent_id=50)  # fallback Claude
```

---

## Architecture du projet

```
bridge-service/
├── bridge_server.py     # Serveur Flask — point d'entree
├── auth.py              # Login, token, refresh automatique
├── api_client.py        # Client HTTP pour l'API France Student
├── sse_parser.py        # Parsing du flux SSE temps reel
├── image_handler.py     # Download + stockage local des images
├── config/config.py     # Configuration centralisee
├── storage/images/      # Dossier de stockage des images
├── requirements.txt     # httpx, flask, aiofiles
├── run.sh               # Lancement Linux/Mac
├── run.bat              # Lancement Windows
└── .gitignore           # Protege les donnees sensibles
```

---

## Securite

Aucune donnee ne quitte ton ordinateur en dehors des appels vers France Student :

- Les credentials (`FS_EMAIL`, `FS_PASSWORD`) passent par **variables d'environnement** uniquement
- Le token API est stocke dans `store.json` (dans `.gitignore`, jamais commite)
- Le dossier `storage/images/` est exclu du repo
- Toute connexion vers France Student se fait en HTTPS

---

## Avertissement

> Ce projet est un **reverse-engineering** du frontend web de France Student. Il peut cesser de fonctionner a tout moment si France Student modifie son API, son authentification, ou ses endpoints.
>
> Ce projet n'est **pas affilie a France Student**. C'est un outil communautaire open-source. Utilise-le de facon raisonnable — ne spamme pas l'API, ne contourne pas les limites de rate limiting.
>
> Si le bridge ne fonctionne plus, ouvre une **issue** sur ce repo, on corrigera.

---

## Licence

MIT — fais-en ce que tu veux. Un petit mot sur le repo fait toujours plaisir.

<p align="center">
  <br>
  <b>Si ce projet t'est utile, laisse une etoile sur GitHub.</b>
  <br>
  <a href="https://github.com/Yormede/france-student-bridge">
    <img src="https://img.shields.io/github/stars/Yormede/france-student-bridge?style=social" />
  </a>
</p>
