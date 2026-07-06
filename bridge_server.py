import asyncio
import json
import os
import time
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_file, stream_with_context
from config.config import (
    SERVER_HOST, SERVER_PORT, IMAGES_DIR, DEFAULT_AGENT_ID, MAX_RETRIES, RETRY_DELAYS
)
from auth import AuthManager
from api_client import FranceStudentAPI
from sse_parser import extract_output_from_events
from image_handler import download_images_from_output

app = Flask(__name__)

auth = AuthManager()
api = FranceStudentAPI(auth)

CACHED_MODELS = []
MODELS_LAST_FETCH = 0


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _get_default_agent_id():
    global CACHED_MODELS, MODELS_LAST_FETCH
    if not CACHED_MODELS or time.time() - MODELS_LAST_FETCH > 3600:
        try:
            CACHED_MODELS = _run_async(api.get_models())
            MODELS_LAST_FETCH = time.time()
        except Exception:
            pass
    for m in CACHED_MODELS:
        if m.get("isDefault"):
            return m["id"]
    if CACHED_MODELS:
        return CACHED_MODELS[0]["id"]
    return DEFAULT_AGENT_ID


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "authenticated": auth.is_authenticated,
        "modelsCached": len(CACHED_MODELS),
        "timestamp": time.time(),
    })


@app.route("/auth/status", methods=["GET"])
def auth_status():
    return jsonify({
        "authenticated": auth.is_authenticated,
        "email": os.environ.get("FS_EMAIL", "***")[:3] + "***" if auth.is_authenticated else None,
    })


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    if data.get("email"):
        os.environ["FS_EMAIL"] = data["email"]
    if data.get("password"):
        os.environ["FS_PASSWORD"] = data["password"]
    auth.clear()
    try:
        token = auth.get_token(force=True)
        return jsonify({"status": "ok", "authenticated": True, "tokenPreview": token[:10] + "..."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 401


@app.route("/models", methods=["GET"])
def get_models():
    try:
        models = _run_async(api.get_models())
        global CACHED_MODELS, MODELS_LAST_FETCH
        CACHED_MODELS = models
        MODELS_LAST_FETCH = time.time()
        return jsonify({"models": models, "count": len(models)})
    except Exception as e:
        if CACHED_MODELS:
            return jsonify({"models": CACHED_MODELS, "count": len(CACHED_MODELS), "cached": True})
        return jsonify({"error": str(e)}), 500


@app.route("/chat/completions", methods=["POST"])
def chat_completions():
    data = request.get_json() or {}
    message = data.get("message") or data.get("prompt") or ""
    if not message:
        return jsonify({"error": "message or prompt required"}), 400

    agent_id = data.get("agentId") or data.get("model") or _get_default_agent_id()
    if isinstance(agent_id, str):
        for m in CACHED_MODELS:
            if m["name"].lower() == agent_id.lower() or m["model"].lower() == agent_id.lower():
                agent_id = m["id"]
                break

    images = data.get("images", [])
    files = data.get("files", [])
    enable_web_search = data.get("enableWebSearch", False)
    stream = data.get("stream", True)

    def generate():
        for attempt in range(MAX_RETRIES):
            try:
                events = _run_async(api.create_chat(
                    message=message,
                    agent_id=agent_id,
                    images=images,
                    files=files,
                    enable_web_search=enable_web_search,
                ))
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    auth.clear()
                    time.sleep(1)
                else:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

        output = extract_output_from_events(events)
        if not output.get("isFinished"):
            last_id = None
            for ev in events:
                if ev.get("last_event_id"):
                    last_id = ev["last_event_id"]
            if last_id:
                chat_id = output.get("chatId")
                for attempt in range(MAX_RETRIES):
                    try:
                        reconnect_events = _run_async(api.reconnect_stream(chat_id, last_id))
                        events.extend(reconnect_events)
                        output = extract_output_from_events(events)
                        break
                    except Exception:
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAYS[attempt])
                        else:
                            output["finishedReason"] = "timeout"

        image_results = _run_async(
            download_images_from_output(api, output, SERVER_HOST, SERVER_PORT)
        )
        output["downloadedImages"] = image_results

        if stream:
            yield f"data: {json.dumps(output)}\n\n"
            yield "data: [DONE]\n\n"
        else:
            yield json.dumps(output)

    if stream:
        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    else:
        return jsonify(json.loads("".join(generate())))


@app.route("/chat/<chat_id>/message", methods=["POST"])
def send_chat_message(chat_id):
    data = request.get_json() or {}
    message = data.get("message") or data.get("content") or ""
    if not message:
        return jsonify({"error": "message or content required"}), 400

    images = data.get("images", [])
    files = data.get("files", [])
    enable_web_search = data.get("enableWebSearch", False)
    stream = data.get("stream", True)

    def generate():
        for attempt in range(MAX_RETRIES):
            try:
                events = _run_async(api.send_message(
                    chat_id=chat_id,
                    message=message,
                    images=images,
                    files=files,
                    enable_web_search=enable_web_search,
                ))
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    auth.clear()
                    time.sleep(1)
                else:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

        output = extract_output_from_events(events)
        if not output.get("isFinished"):
            last_id = None
            for ev in events:
                if ev.get("last_event_id"):
                    last_id = ev["last_event_id"]
            if last_id:
                for attempt in range(MAX_RETRIES):
                    try:
                        reconnect_events = _run_async(api.reconnect_stream(chat_id, last_id))
                        events.extend(reconnect_events)
                        output = extract_output_from_events(events)
                        break
                    except Exception:
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAYS[attempt])
                        else:
                            output["finishedReason"] = "timeout"

        image_results = _run_async(
            download_images_from_output(api, output, SERVER_HOST, SERVER_PORT)
        )
        output["downloadedImages"] = image_results

        if stream:
            yield f"data: {json.dumps(output)}\n\n"
            yield "data: [DONE]\n\n"
        else:
            yield json.dumps(output)

    if stream:
        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    else:
        return jsonify(json.loads("".join(generate())))


@app.route("/chat/<chat_id>", methods=["GET"])
def get_chat_detail(chat_id):
    try:
        result = _run_async(api.get_chat(chat_id))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat/<chat_id>/delete", methods=["DELETE"])
def delete_chat(chat_id):
    try:
        _run_async(api.delete_chat(chat_id))
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chats", methods=["GET"])
def list_chats():
    limit = request.args.get("limit", 20, type=int)
    cursor = request.args.get("cursor")
    try:
        result = _run_async(api.get_chats(limit=limit, cursor_chat_id=cursor))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat/<chat_id>/usage", methods=["GET"])
def chat_usage(chat_id):
    try:
        result = _run_async(api.get_chat_usage(chat_id))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/images/<filename>", methods=["GET"])
def serve_image(filename):
    safe_name = Path(filename).name
    filepath = IMAGES_DIR / safe_name
    if not filepath.exists():
        return jsonify({"error": "image not found"}), 404
    return send_file(str(filepath))


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400
    f = request.files["file"]
    tmp = Path(f"/tmp/{f.filename}")
    f.save(str(tmp))
    try:
        result = _run_async(api.upload_file(str(tmp)))
        tmp.unlink()
        return jsonify(result)
    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        return jsonify({"error": str(e)}), 500


def main():
    print(f"🚀 Bridge Service démarré sur http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"   Health: http://{SERVER_HOST}:{SERVER_PORT}/health")
    print(f"   Models: http://{SERVER_HOST}:{SERVER_PORT}/models")
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
