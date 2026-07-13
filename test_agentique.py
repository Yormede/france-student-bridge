#!/usr/bin/env python3
"""Teste tous les modèles France Student pour le tool calling et le web search."""
import json, sys, time
import requests

URL = "http://localhost:8765/v1/chat/completions"
AUX = "http://localhost:8765/models"

TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Obtenir la meteo actuelle d une ville",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Nom de la ville"}
            },
            "required": ["city"]
        }
    }
}]

TOOL_PROMPT = "Quelle est la meteo actuelle a Paris ? Utilise get_weather."

WEBSEARCH_PROMPT = "Recherche sur le web quel est le cours actuel du Bitcoin en dollars."

def test_model(mid, mname, mprov):
    r = {"id": mid, "name": mname, "provider": mprov}

    # Test 1: Tool calling
    try:
        resp = requests.post(URL, json={
            "model": mname,
            "messages": [{"role": "user", "content": TOOL_PROMPT}],
            "tools": TOOLS,
            "stream": False,
        }, timeout=60)
        data = resp.json()
        msg = data.get("choices", [{}])[0].get("message", {})
        tool_calls = msg.get("tool_calls")
        content = msg.get("content", "")
        r["tool_calls"] = len(tool_calls) if tool_calls else 0
        r["tool_name"] = tool_calls[0]["function"]["name"] if tool_calls else None
        r["content_preview"] = content[:80] if content else "(vide)"
        r["tool_ok"] = bool(tool_calls)
    except Exception as e:
        r["tool_calls"] = "ERROR"
        r["tool_ok"] = False
        r["error"] = str(e)[:80]

    time.sleep(1)

    # Test 2: Web search
    try:
        resp = requests.post("http://localhost:8765/chat/completions", json={
            "message": WEBSEARCH_PROMPT,
            "model": mname,
            "enableWebSearch": True,
            "stream": False,
        }, timeout=60)
        data = resp.json()
        c = data.get("content", {})
        text = c.get("text", "")
        ws_calls = c.get("webSearchCalls", [])
        r["web_search_calls"] = len(ws_calls)
        r["web_ok"] = len(ws_calls) > 0
        r["ws_content_preview"] = text[:100] if text else "(vide)"
    except Exception as e:
        r["web_search_calls"] = "ERROR"
        r["web_ok"] = False
        r["ws_error"] = str(e)[:80]

    return r

def main():
    models = requests.get(AUX, timeout=10).json()["models"]
    print(f"\n{'='*100}")
    print(f"{'ID':>4} {'MODELE':<25} {'PROVIDER':<12} {'TOOLS':>8} {'WEB':>8} {'TOOL_NAME':<20} {'CONTENT'}")
    print(f"{'='*100}")

    results = []
    for m in models:
        sys.stdout.write(f"  [{m['id']:>3}] {m['name']:<25} ... ")
        sys.stdout.flush()
        r = test_model(m['id'], m['name'], m['modelProvider'])
        results.append(r)
        tool_emoji = "✅" if r.get("tool_ok") else ("❌" if r.get("tool_calls") == 0 else "⚠")
        web_emoji = "✅" if r.get("web_ok") else ("❌" if r.get("web_search_calls") == 0 else "⚠")
        tn = r.get('tool_name', '') or ''
        cp = r.get('content_preview', '')[:50]
        print(f"{tool_emoji}{web_emoji} {tn[:18]:<20} {cp}")

    print(f"\n{'='*100}")
    print(f"\n=== RESUME ===")
    tool_ok = sum(1 for r in results if r.get("tool_ok"))
    web_ok = sum(1 for r in results if r.get("web_ok"))
    print(f"  Tool calling:  {tool_ok}/{len(results)} modeles")
    print(f"  Web search:    {web_ok}/{len(results)} modeles")

    print(f"\n=== MODELES AGENTIQUES (tools + web) ===")
    for r in results:
        if r.get("tool_ok") and r.get("web_ok"):
            print(f"  [{r['id']:>3}] {r['name']:<25} {r['provider']} ★ FULL AGENTIC")

    print(f"\n=== MODELES PARTIELS ===")
    for r in results:
        if r.get("tool_ok") and not r.get("web_ok"):
            print(f"  [{r['id']:>3}] {r['name']:<25} {r['provider']} (tools only)")
        elif not r.get("tool_ok") and r.get("web_ok"):
            print(f"  [{r['id']:>3}] {r['name']:<25} {r['provider']} (web only)")

if __name__ == "__main__":
    main()
