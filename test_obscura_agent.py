#!/usr/bin/env python3
"""Test agentique complet: modele + Puppeteer web search (Obscura-style)"""
import json, subprocess, os
import requests

BRIDGE = "http://localhost:8765/v1/chat/completions"

TOOLS = [{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Recherche sur le web via un navigateur anti-detect (Obscura-style). Retourne titres, URLs et snippets.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "La requete de recherche"}
            },
            "required": ["query"]
        }
    }
}]

def call_web_search(query):
    """Execute Puppeteer web search."""
    result = subprocess.run(
        ["node", "/workspace/france-student-bridge/web_search.js", query, "5"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "CHROME_PATH": "/usr/bin/chromium-browser"},
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    return json.loads(result.stdout)

def agentic_chat(model, user_message, max_rounds=3):
    """Boucle agentique: modele -> tool -> resultat -> modele."""
    messages = [{"role": "user", "content": user_message}]
    
    for round_num in range(max_rounds):
        print(f"\n{'='*70}")
        print(f"ROUND {round_num+1}/{max_rounds} | Model: {model}")
        
        resp = requests.post(BRIDGE, json={
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
        }, timeout=90).json()
        
        choice = resp.get("choices", [{}])[0]
        msg = choice.get("message", {})
        finish = choice.get("finish_reason", "")
        
        content = msg.get("content") or "(vide)"
        tool_calls = msg.get("tool_calls") or []
        
        print(f"  finish_reason: {finish}")
        print(f"  content: {content[:200]}")
        print(f"  tool_calls: {len(tool_calls)}")
        
        if tool_calls:
            # Execute tools
            tool_msgs = []
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args = json.loads(func.get("arguments", "{}"))
                print(f"  -> Calling {name}({args})")
                
                if name == "web_search":
                    result = call_web_search(args.get("query", ""))
                    n_results = len(result.get("results", []))
                    print(f"  <- Web search: {n_results} results")
                    tool_msgs.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", f"call_{round_num}"),
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            
            # Add assistant message + tool results
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            messages.extend(tool_msgs)
            continue
        
        # No more tool calls - final answer
        print(f"\n  REPONSE FINALE: {content}")
        return content
    
    return "(max rounds)"

# Test avec plusieurs modeles
for model in ["claude-sonnet-5", "gpt-5.6-sol", "claude-opus-4-8"]:
    print(f"\n\n{'#'*70}")
    print(f"# TEST AGENTIQUE: {model}")
    print(f"{'#'*70}")
    agentic_chat(model, "Cherche sur le web le prix actuel du Bitcoin en dollars. Resume en 1 ligne.")
