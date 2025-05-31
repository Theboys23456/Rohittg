import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from gtts import gTTS
from moviepy.editor import *
from gtts import gTTS
from telegram.ext import Updater, CommandHandler

def start(update, context):
    update.message.reply_text("Bot is working!")

if __name__ == '__main__':
    updater = Updater("YOUR_BOT_TOKEN")
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    updater.start_polling()
    updater.idle()
import uuid

BOT_NAME = os.environ.get("BOT_NAME", "TXT Video Bot")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Welcome! I convert .txt files into videos. Please send a .txt file to begin."
    )

async def handle_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please send a valid .txt file.")
        return

    file_path = f"/tmp/{document.file_unique_id}.txt"
    await document.get_file().download_to_drive(file_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    user_id = update.message.from_user.id
    user_data[user_id] = {
        "lines": lines,
        "step": "ask_start",
        "file": file_path
    }

    await update.message.reply_text(
        f"✅ File loaded with {len(lines)} lines.\nWhich line number should I start from? (e.g., 1)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_data:
        await update.message.reply_text("Please send a .txt file first.")
        return

    user_state = user_data[user_id]

    if user_state["step"] == "ask_start":
        if not update.message.text.isdigit():
            await update.message.reply_text("❌ Please enter a valid number.")
            return
        start_line = int(update.message.text)
        if start_line < 1 or start_line > len(user_state["lines"]):
            await update.message.reply_text("❌ That line number is not in the file.")
            return
        user_state["start"] = start_line - 1
        user_state["step"] = "ask_resolution"
        await update.message.reply_text("📽 Choose video resolution:\n1. 480p\n2. 720p\n3. 1080p\n(Reply with 1, 2, or 3)")
        return

    elif user_state["step"] == "ask_resolution":
        options = {"1": (640, 480), "2": (1280, 720), "3": (1920, 1080)}
        resolution = options.get(update.message.text.strip())
        if not resolution:
            await update.message.reply_text("❌ Please enter 1, 2, or 3.")
            return
        user_state["resolution"] = resolution
        user_state["step"] = "ask_name"
        await update.message.reply_text("✍️ What name should I show at the bottom of the video?")
        return

    elif user_state["step"] == "ask_name":
        user_state["name"] = update.message.text.strip()
        user_state["step"] = "done"
        await update.message.reply_text("✅ Thanks! Generating videos now...")
        await create_and_send_videos(update, context, user_state)
        user_data.pop(user_id, None)
        return

async def create_and_send_videos(update, context, state):
    lines = state["lines"][state["start"]:]
    resolution = state["resolution"]
    name = state["name"]

    for idx, line in enumerate(lines, start=1):
        video_path = create_video_from_text(line, resolution, name)
        await context.bot.send_video(chat_id=update.message.chat_id, video=open(video_path, 'rb'), caption=f"🎬 Line {state['start'] + idx}")
        os.remove(video_path)

def create_video_from_text(text, resolution, name_text):
    tts = gTTS(text=text, lang='en')
    audio_path = f"/tmp/audio_{uuid.uuid4()}.mp3"
    tts.save(audio_path)

    clip = TextClip(txt=text, fontsize=48, color='white', size=resolution, method='caption', bg_color='black')
    clip = clip.set_duration(AudioFileClip(audio_path).duration)

    name_clip = TextClip(txt=name_text, fontsize=30, color='yellow', size=(resolution[0], 50), method='caption')
    name_clip = name_clip.set_duration(clip.duration).set_position(("center", resolution[1] - 60))

    final = CompositeVideoClip([clip, name_clip])
    final = final.set_audio(AudioFileClip(audio_path))

    output_path = f"/tmp/video_{uuid.uuid4()}.mp4"
    final.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', verbose=False, logger=None)

    os.remove(audio_path)
    return output_path

if __name__ == '__main__':
    import asyncio
    import os
    TOKEN = os.environ.get("BOT_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_txt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

