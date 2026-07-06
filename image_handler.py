import time
import aiofiles
from pathlib import Path
from datetime import datetime
from config.config import IMAGES_DIR


def _sanitize(s, max_len=8):
    if not s:
        return "unknown"
    return str(s).replace("/", "_").replace("\\", "_").replace("..", "_").replace(" ", "_")[:max_len]


def generate_filename(chat_id, message_id, image_id, ext="png"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (
        f"{_sanitize(chat_id)}_{_sanitize(message_id)}_"
        f"{_sanitize(image_id)}_{ts}.{ext}"
    )


async def download_and_save_image(api, chat_id, message_id, image_id,
                                  server_host="localhost", server_port=8765):
    content, content_type = await api.get_image(chat_id, message_id, image_id)

    ext = "png"
    if content_type:
        ct = content_type.lower()
        if "jpeg" in ct or "jpg" in ct:
            ext = "jpg"
        elif "webp" in ct:
            ext = "webp"
        elif "gif" in ct:
            ext = "gif"
        elif "svg" in ct:
            ext = "svg"

    filename = generate_filename(chat_id, message_id, image_id, ext)
    filepath = IMAGES_DIR / filename

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    download_url = f"http://{server_host}:{server_port}/images/{filename}"

    return {
        "imageId": image_id,
        "messageId": message_id,
        "chatId": chat_id,
        "localPath": str(filepath.absolute()),
        "filename": filename,
        "downloadUrl": download_url,
        "contentType": content_type,
        "sizeBytes": len(content),
    }


async def download_images_from_output(api, output, server_host, server_port):
    images = []
    image_items = output.get("imageItems", [])

    chat_id = output.get("chatId")
    message_id = output.get("messageId")
    completed_msg = output.get("completedMessage") or {}

    if not message_id and completed_msg.get("id"):
        message_id = completed_msg["id"]

    seen = set()
    for item in image_items:
        if not item.get("done"):
            continue

        image_id = item.get("id") or item.get("image_id") or item.get("file_id")
        if not image_id or image_id in seen:
            continue

        if str(image_id).startswith("ig_"):
            continue

        seen.add(image_id)

        try:
            result = await download_and_save_image(
                api, chat_id, message_id, image_id,
                server_host, server_port,
            )
            images.append(result)
        except Exception as e:
            images.append({
                "imageId": image_id,
                "error": str(e),
            })

    used_ids = completed_msg.get("usedFileIds") or []
    used_ids_v2 = completed_msg.get("usedFilesV2Ids") or []
    for fid in used_ids + used_ids_v2:
        if fid not in seen and fid:
            seen.add(fid)
            try:
                result = await download_and_save_image(
                    api, chat_id, message_id, fid,
                    server_host, server_port,
                )
                images.append(result)
            except Exception as e:
                images.append({
                    "imageId": fid,
                    "error": str(e),
                })

    return images
