from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """
    Handles the /start command.
    Replies with a message indicating the bot is running (in Persian).
    """
    await message.reply_text("بات در حال اجرا است!")

@Client.on_message(filters.command("health_check"))
async def health_check_command(client: Client, message: Message):
    """
    Handles the /health_check command for simple health status.
    Replies with a message indicating the bot is running (in English).
    """
    await message.reply_text("Bot is running and responsive!")
