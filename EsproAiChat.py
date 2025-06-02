import asyncio
import base64
import mimetypes
import os
from typing import Union, Tuple

from pyrogram import Client, filters, types as t
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

from lexica import AsyncClient
from lexica.constants import languageModels

# ========== ENV VAR HELP ==========
def get_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Missing environment variable: {name}")
    return value

# ========== CONFIG ==========
API_ID = int(get_env_var("API_ID", 28294093))
API_HASH = get_env_var("API_HASH", "f24d982c45ab2f69a6cb8c0fee9630bd")
BOT_TOKEN = get_env_var("BOT_TOKEN", "7033324811:AAEpwCS9ulTN_rFLBCunJ7Y6DGN0ivylxR8")

app = Client("AIChatBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== USER MEMORY ==========
user_model_memory = {}

# ========== CHAT COMPLETION ==========
async def ChatCompletion(prompt, model) -> Union[Tuple[str, list], str]:
    try:
        modelInfo = getattr(languageModels, model)
        client = AsyncClient()
        output = await client.ChatCompletion(prompt, modelInfo)
        if model == "bard":
            return output['content'], output['images']
        return output['content']
    except Exception as E:
        raise Exception(f"API error: {E}")

# ========== GEMINI VISION ==========
async def geminiVision(prompt, model, images) -> str:
    imageInfo = []
    for image in images:
        with open(image, "rb") as imageFile:
            data = base64.b64encode(imageFile.read()).decode("utf-8")
            mime_type, _ = mimetypes.guess_type(image)
            imageInfo.append({
                "data": data,
                "mime_type": mime_type
            })
        os.remove(image)
    modelInfo = getattr(languageModels, model)
    client = AsyncClient()
    output = await client.ChatCompletion(prompt, modelInfo, json={"images": imageInfo})
    return output['content']['parts'][0]['text']

# ========== GET MEDIA ==========
def getMedia(message):
    media = message.media or (message.reply_to_message.media if message.reply_to_message else None)
    if media:
        target = message if message.media else message.reply_to_message
        if target.photo:
            return target.photo
        elif target.document and target.document.mime_type in ['image/png', 'image/jpeg'] and target.document.file_size < 5_242_880:
            return target.document
    return None

# ========== GET TEXT ==========
def getText(message):
    if not message.text:
        return None
    return message.text.split(None, 1)[1] if " " in message.text else None

# ========== /START ==========
@app.on_message(filters.command("start") & filters.private)
async def start_command(_, m: t.Message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👤 Owner", url="https://t.me/ll_Ksd_ll")],
            [InlineKeyboardButton("➕ Add Me To Group", url="https://t.me/PowerStudyChatgptBot?startgroup=s&admin=delete_messages+manage_video_chats+pin_messages+invite_users")]
        ]
    )
    await m.reply_text(
        f"👋 Hello {m.from_user.mention}!\n\n"
        "Welcome to the AI chatbot. Use commands like /gpt, /bard, /gemini to chat.\n\n"
        "For help or updates, contact the owner.",
        reply_markup=keyboard
    )

# ========== /PING ==========
@app.on_message(filters.command("ping") & filters.private)
async def ping(_, message):
    await message.reply_text("Pong! Bot is running ✅")

# ========== /GPT /BARD /GEMINI /ETC ==========
@app.on_message(filters.command(["gpt", "bard", "llama", "mistral", "palm", "gemini"]))
async def chatbots(_, m: t.Message):
    prompt = getText(m)
    media = getMedia(m)

    model = m.command[0].lower()
    user_model_memory[m.from_user.id] = model

    if media:
        return await askAboutImage(_, m, [media], prompt)

    if not prompt:
        return await m.reply_text(f"✅ Model set to `{model}`. Ab bina command ke message bhejo.")

    try:
        output = await ChatCompletion(prompt, model)

        if model == "bard":
            text, images = output
            if not images:
                return await m.reply_text(text)
            media_group = [InputMediaPhoto(i) for i in images]
            media_group[0] = InputMediaPhoto(images[0], caption=text)
            return await _.send_media_group(m.chat.id, media_group, reply_to_message_id=m.id)

        text = output['parts'][0]['text'] if model == "gemini" else output
        await m.reply_text(text)

    except Exception as e:
        await m.reply_text(f"❌ Error: {e}")

# ========== TEXT AUTO-REPLY ==========
@app.on_message(filters.private & filters.text & ~filters.command(["gpt", "bard", "llama", "mistral", "palm", "gemini"]))
async def smart_chat(_, m: t.Message):
    prompt = m.text
    model = user_model_memory.get(m.from_user.id, "gpt")

    try:
        output = await ChatCompletion(prompt, model)
        text = output['parts'][0]['text'] if model == "gemini" else output
        await m.reply_text(text)
    except Exception as e:
        await m.reply_text(f"❌ Error: {e}")

# ========== IMAGE + PROMPT HANDLER ==========
async def askAboutImage(_, m: t.Message, mediaFiles: list, prompt: str):
    images = []
    for media in mediaFiles:
        image = await _.download_media(media.file_id, file_name=f"./downloads/{m.from_user.id}_ask.jpg")
        images.append(image)
    output = await geminiVision(prompt or "What's this?", "gemini", images)
    await m.reply_text(output)

if __name__ == "__main__":
    print("Bot is starting...")
    app.run()
    print("Bot stopped.")
