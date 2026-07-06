import json
import re
import asyncio
from datetime import datetime
from config.config import MAX_RETRIES, RETRY_DELAYS


SSE_LINE_RE = re.compile(r"^(event|data|id|retry):\s*(.*)$")


async def parse_sse_stream(response, timeout=30):
    event_type = ""
    data_buffer = ""
    last_event_id = None

    async for line in response.aiter_lines():
        if line == "":
            if event_type and data_buffer:
                try:
                    parsed = json.loads(data_buffer)
                except (json.JSONDecodeError, ValueError):
                    parsed = {"raw": data_buffer}

                yield {
                    "event": event_type,
                    "data": parsed,
                    "last_event_id": last_event_id,
                }

                if event_type == "response.created":
                    last_event_id = parsed.get("id", last_event_id)

            event_type = ""
            data_buffer = ""
            continue

        m = SSE_LINE_RE.match(line)
        if not m:
            if data_buffer:
                data_buffer += "\n" + line
            continue

        field, value = m.group(1), m.group(2)
        if value.startswith(" "):
            value = value[1:]

        if field == "event":
            event_type = value
        elif field == "data":
            data_buffer += value
        elif field == "id":
            last_event_id = value

    if event_type and data_buffer:
        try:
            parsed = json.loads(data_buffer)
        except (json.JSONDecodeError, ValueError):
            parsed = {"raw": data_buffer}
        yield {
            "event": event_type,
            "data": parsed,
            "last_event_id": last_event_id,
        }


def extract_output_from_events(events):
    text_parts = []
    reasoning_parts = []
    code_blocks = []
    js_blocks = []
    function_calls = []
    web_search_calls = []
    image_items = []
    message_id = None
    chat_id = None
    user_message_id = None
    model = None
    model_provider = None
    token_usage = None
    error_message = None
    finish_reason = None
    created_at = None
    last_completed_message = None

    for ev in events:
        etype = ev["event"]
        data = ev["data"]

        if etype == "response.created":
            chat_id = data.get("chat_id") or chat_id
            user_message_id = data.get("user_message_id") or user_message_id

        elif etype == "response.output_text.delta":
            text_parts.append(data.get("delta", ""))

        elif etype == "response.output_text.done":
            if data.get("text"):
                text_parts = [data["text"]]

        elif etype == "response.output_item.added":
            item = data.get("item", {})
            item_type = item.get("type", "")
            if item_type == "web_search_call":
                web_search_calls.append(item)
            elif item_type == "function_call":
                function_calls.append(item)
            elif item_type == "image_generation_call":
                image_items.append(item)

        elif etype == "response.output_item.done":
            item = data.get("item", {})
            item_type = item.get("type", "")
            if item_type == "image_generation_call":
                for i, img in enumerate(image_items):
                    if img.get("type") == "image_generation_call" and not img.get("done"):
                        image_items[i] = {**img, **item, "done": True}
                        break
                else:
                    image_items.append({**item, "done": True})
            elif item_type == "message":
                if item.get("id"):
                    message_id = item["id"]

        elif etype == "response.reasoning_summary_text.delta":
            reasoning_parts.append(data.get("delta", ""))

        elif etype == "response.completed":
            resp = data.get("response", {})
            model = model or resp.get("model")
            model_provider = model_provider or resp.get("modelProvider")
            token_usage = token_usage or resp.get("usage")
            created_at = created_at or datetime.utcnow().isoformat() + "Z"

        elif etype == "response.failed":
            error_message = data.get("error", {}).get("message", "Unknown error")
            finish_reason = "failed"

        elif etype == "completed":
            msg = data.get("message", {})
            last_completed_message = msg
            message_id = msg.get("id") or message_id
            chat_id = data.get("chat_id") or chat_id
            model = msg.get("model") or model
            model_provider = msg.get("modelProvider") or model_provider
            token_usage = token_usage or msg.get("tokenUsage")
            created_at = msg.get("createdAt") or created_at
            finish_reason = "completed"

            used_ids = msg.get("usedFileIds") or []
            used_ids_v2 = msg.get("usedFilesV2Ids") or []
            parts = msg.get("parts") or []
            if isinstance(parts, list):
                for part in parts:
                    if isinstance(part, dict) and part.get("type") == "tool-imageGeneration":
                        output_data = part.get("output", {})
                        if isinstance(output_data, dict) and output_data.get("id"):
                            image_items.append({
                                "id": output_data["id"],
                                "generationId": output_data.get("generationId"),
                                "kind": output_data.get("kind", "image"),
                                "contentType": output_data.get("contentType"),
                                "fileExtension": output_data.get("fileExtension"),
                                "sizeBytes": output_data.get("sizeBytes"),
                                "revisedPrompt": output_data.get("revisedPrompt"),
                                "url": output_data.get("url"),
                                "type": "image_generation_call",
                                "done": True,
                            })
            elif isinstance(parts, dict):
                for key, val in parts.items():
                    if "image" in key.lower():
                        if isinstance(val, list):
                            for i in val:
                                if isinstance(i, dict) and i.get("id"):
                                    image_items.append({**i, "type": "image_generation_call", "done": True})
                        elif isinstance(val, dict) and val.get("id"):
                            image_items.append({**val, "type": "image_generation_call", "done": True})

            for fid in used_ids + used_ids_v2:
                if fid not in [i.get("id") for i in image_items if i.get("id")]:
                    image_items.append({"id": fid, "type": "image_generation_call", "done": True})

        elif etype == "error":
            error_message = data.get("message", "Unknown error")
            finish_reason = "error"

    full_text = "".join(text_parts)
    full_reasoning = "".join(reasoning_parts) if reasoning_parts else None

    code_block_re = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
    for match in code_block_re.finditer(full_text):
        lang = match.group(1).strip() or "text"
        code = match.group(2).strip()
        code_blocks.append({"language": lang, "code": code})
        if lang.lower() in ("javascript", "js"):
            js_blocks.append({"code": code, "source": "code_block"})

    js_inline_re = re.compile(
        r"<script[^>]*>\s*(.*?)\s*</script>",
        re.DOTALL | re.IGNORECASE,
    )
    for match in js_inline_re.finditer(full_text):
        code = match.group(1).strip()
        if code:
            js_blocks.append({"code": code, "source": "script_tag"})

    return {
        "chatId": chat_id,
        "messageId": message_id,
        "userMessageId": user_message_id,
        "role": "assistant",
        "model": model,
        "modelProvider": model_provider,
        "content": {
            "text": full_text,
            "reasoning": full_reasoning,
            "codeBlocks": code_blocks,
            "javascriptBlocks": js_blocks,
            "functionCalls": function_calls,
            "webSearchCalls": web_search_calls,
        },
        "imageItems": image_items,
        "completedMessage": last_completed_message,
        "tokenUsage": token_usage,
        "createdAt": created_at,
        "isFinished": finish_reason is not None,
        "finishedReason": finish_reason,
        "errorMessage": error_message,
    }
