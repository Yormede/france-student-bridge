"""
Boucle tools client-side pour le bridge France Student.
"""

import json
import re
import time
from config.config import MAX_RETRIES, RETRY_DELAYS

TOOL_NATIVE_MODELS = {"Mistral-Large-3", "Kimi-K2.5", "DeepSeek-V3.2"}


def is_tool_native(model_name):
    if not model_name:
        return False
    return model_name in TOOL_NATIVE_MODELS


def build_tool_prompt(tools, model_name=None):
    if not tools:
        return ""
    if is_tool_native(model_name):
        return _build_native_tool_prompt(tools)
    else:
        return _build_format_forced_prompt(tools)


def _build_native_tool_prompt(tools):
    tool_descs = []
    for t in tools:
        func = t.get("function", t)
        name = func.get("name", "")
        desc = func.get("description", "")
        params = func.get("parameters", {})
        props = params.get("properties", {})
        required = params.get("required", [])

        param_lines = []
        for pname, pinfo in props.items():
            req_mark = " (REQUIS)" if pname in required else ""
            param_lines.append("    - " + pname + ": " + pinfo.get("description", "") + req_mark)

        body = "### " + name + "\n" + desc
        if param_lines:
            body += "\nParametres:\n" + "\n".join(param_lines)
        tool_descs.append(body)

    tool_block = "\n\n".join(tool_descs)
    return "<SYSTEM_INSTRUCTION>\nTu es un agent IA avec acces a des outils. Tu DOIS utiliser ces outils pour repondre.\nNe donne JAMAIS une reponse directe si un outil peut t aider - appelle l outil d abord.\n\nQuand tu veux utiliser un outil, reponds EXACTEMENT et UNIQUEMENT avec :\n\n<function_call>\n{\"name\": \"<nom_outil>\", \"arguments\": {\"param1\": \"valeur1\"}}\n</function_call>\n\nREGLES STRICTES :\n1. RIEN avant <function_call>, RIEN apres </function_call>\n2. Le JSON dans <function_call> doit etre valide\n3. Si tu connais deja la reponse sans outil, reponds normalement\n\nOUTILS DISPONIBLES :\n" + tool_block + "\n</SYSTEM_INSTRUCTION>"


def _build_format_forced_prompt(tools):
    """Template JSON pour GPT/Claude. Zero mention d outils."""
    actions = []
    for t in tools:
        func = t.get("function", t)
        name = func.get("name", "")
        desc = func.get("description", "")
        params = func.get("parameters", {})
        props = params.get("properties", {})

        example = {"action": name, "params": {}}
        for pname, pinfo in props.items():
            example["params"][pname] = "<" + pname + ">"
        actions.append({"name": name, "desc": desc, "example": json.dumps(example, ensure_ascii=False)})

    lines = []
    lines.append("Complete le template JSON qui correspond le mieux. Retourne UNIQUEMENT le JSON, RIEN d autre.")
    lines.append("")
    for a in actions:
        lines.append("Option " + a["name"] + " (" + a["desc"] + "):")
        lines.append(a["example"])
        lines.append("")
    lines.append("Choisis la meilleure option et retourne le JSON complete. Pas de texte autour.")
    return "\n".join(lines)


def parse_function_call(text):
    # Format 1: <function_call>
    m = re.search(r"<function_call>\s*(.*?)\s*</function_call>", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1).strip())
            return {"name": data.get("name", ""), "arguments": data.get("arguments", {})}
        except (json.JSONDecodeError, ValueError):
            pass

    # Format 2: {"tool": ..., "args": ...}
    m = re.search(r'"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{[^}]+\})', text)
    if m:
        try:
            return {"name": m.group(1), "arguments": json.loads(m.group(2))}
        except (json.JSONDecodeError, ValueError):
            pass

    # Format 2b: {"action": ..., "params": ...}
    m = re.search(r'"action"\s*:\s*"([^"]+)"\s*,\s*"params"\s*:\s*(\{[^}]+\})', text)
    if m:
        try:
            return {"name": m.group(1), "arguments": json.loads(m.group(2))}
        except (json.JSONDecodeError, ValueError):
            pass

    # Format 3: DeepSeek <required>{"name": ...}</required>
    m = re.search(r"<required>\s*(\{.*?\"name\".*?\})\s*</required>", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1).strip())
            return {"name": data.get("name", ""), "arguments": data.get("arguments", {})}
        except (json.JSONDecodeError, ValueError):
            pass

    # Format 4: DeepSeek XML <name>...</name><arguments>...</arguments>
    m = re.search(r"<function_call>\s*<name>(.*?)</name>\s*<arguments>(.*?)</arguments>\s*</function_call>", text, re.DOTALL)
    if m:
        name = m.group(1).strip()
        args_xml = m.group(2).strip()
        args = {}
        for am in re.finditer(r"<(\w+)>(.*?)</\1>", args_xml, re.DOTALL):
            args[am.group(1)] = am.group(2).strip()
        return {"name": name, "arguments": args}

    # Format 5: DeepSeek <ref>name</ref> + JSON
    m = re.search(r"<ref>(\w+)</ref>\s*(\{[^}]+\})", text)
    if m:
        try:
            return {"name": m.group(1), "arguments": json.loads(m.group(2))}
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def has_function_call(text):
    return parse_function_call(text) is not None


def strip_function_call(text):
    text = re.sub(r"<function_call>.*?</function_call>", "", text, flags=re.DOTALL)
    text = re.sub(r'"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{[^}]+\}', "", text)
    text = re.sub(r'"action"\s*:\s*"[^"]+"\s*,\s*"params"\s*:\s*\{[^}]+\}', "", text)
    text = re.sub(r"<required>.*?</required>", "", text, flags=re.DOTALL)
    text = re.sub(r"<ref>.*?</ref>", "", text, flags=re.DOTALL)
    return text.strip()


def build_tool_result_message(tool_name, tool_call_id, result):
    result_str = json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
    return "\n[RESULTAT]\n" + tool_name + " a retourne :\n`\n" + result_str[:4000] + "\n`\n\nContinue ta reponse."


class ToolLoop:
    def __init__(self, api, max_rounds=10):
        self.api = api
        self.max_rounds = max_rounds

    async def run(self, message, agent_id, tools, images=None, files=None,
                  enable_web_search=False, model_name=None):
        full_message = message
        if tools:
            tool_prompt = build_tool_prompt(tools, model_name=model_name)
            if is_tool_native(model_name):
                full_message = tool_prompt + "\n\n[Message utilisateur]\n" + message
            else:
                full_message = tool_prompt + "\n\nQuestion : " + message

        events = await self.api.create_chat(
            message=full_message,
            agent_id=agent_id,
            images=images or [],
            files=files or [],
            enable_web_search=enable_web_search,
        )
        return events

    async def continue_with_result(self, chat_id, tool_name, tool_call_id,
                                    result, agent_id, enable_web_search=False):
        tool_msg = build_tool_result_message(tool_name, tool_call_id, result)
        events = await self.api.send_message(
            chat_id=chat_id,
            message=tool_msg,
            images=[],
            files=[],
            enable_web_search=enable_web_search,
        )
        return events
