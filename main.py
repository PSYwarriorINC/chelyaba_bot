import asyncio
import os
import logging
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from dotenv import load_dotenv

# Логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Завантаження .env (якщо потрібно)
load_dotenv()

# Список каналів-джерел (підстав свої)
SOURCE_CHANNEL_IDS = [
    -1001464909845,    # Канал 1
    -1001394179307,    # Канал 2
    -1001485594833,
    -1001119067534     # Канал 3
]

# Один чат-приймач для всіх повідомлень
DESTINATION_CHAT_ID = -1002664016862

def get_user_credentials():
    while True:
        try:
            api_id = '21077948'.strip()
            if not api_id.isdigit():
                raise ValueError("API_ID має бути числом")
            api_hash = '8d05d23c679698365caabd712804dcac'.strip()
            if not api_hash:
                raise ValueError("API_HASH не може бути порожнім")
            phone_number = '+380683221694'.strip()
            if not phone_number.startswith('+') or not phone_number[1:].isdigit():
                raise ValueError("Номер телефону має бути у форматі +380xxxxxxxxx")
            return int(api_id), api_hash, phone_number
        except ValueError as e:
            print(f"Помилка: {e}. Спробуйте ще раз.")

session_dir = 'secure_sessions'
os.makedirs(session_dir, exist_ok=True)
API_ID, API_HASH, PHONE_NUMBER = get_user_credentials()
client = TelegramClient(os.path.join(session_dir, 'session_name'), API_ID, API_HASH)

def remove_last_three_lines(text):
    if not text:
        return None
    lines = text.split('\n')
    if len(lines) <= 2:
        return text
    return '\n'.join(lines[:-2])

@client.on(events.Album(chats=SOURCE_CHANNEL_IDS))
async def album_handler(event):
    try:
        processed_text = remove_last_three_lines(event.messages[0].text) if event.messages[0].text else None
        media_paths = []
        for message in event.messages:
            if message.media:
                media_path = await client.download_media(message.media)
                if media_path:
                    media_paths.append(media_path)

        if media_paths:
            await client.send_file(DESTINATION_CHAT_ID, media_paths, caption=processed_text)
            for media_path in media_paths:
                try:
                    os.remove(media_path)
                except Exception as e:
                    logger.warning(f"Не вдалося видалити файл {media_path}: {e}")
        elif processed_text:
            await client.send_message(DESTINATION_CHAT_ID, processed_text)
        await asyncio.sleep(1)
    except FloodWaitError as e:
        logger.warning(f"Очікування через ліміт: {e.seconds} секунд")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Помилка обробки альбому: {e}")

@client.on(events.NewMessage(chats=SOURCE_CHANNEL_IDS))
async def single_message_handler(event):
    try:
        if event.grouped_id:
            return
        processed_text = remove_last_three_lines(event.message.text) if event.message.text else None
        if event.message.media:
            media_path = await client.download_media(event.message.media)
            if media_path:
                await client.send_file(DESTINATION_CHAT_ID, media_path, caption=processed_text)
                try:
                    os.remove(media_path)
                except Exception as e:
                    logger.warning(f"Не вдалося видалити файл {media_path}: {e}")
        elif processed_text:
            await client.send_message(DESTINATION_CHAT_ID, processed_text)
        await asyncio.sleep(1)
    except FloodWaitError as e:
        logger.warning(f"Очікування через ліміт: {e.seconds} секунд")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Помилка обробки повідомлення: {e}")

async def main():
    while True:
        try:
            await client.start(PHONE_NUMBER)
            try:
                for source_id in SOURCE_CHANNEL_IDS:
                    source = await client.get_entity(source_id)
                destination = await client.get_entity(DESTINATION_CHAT_ID)
                logger.info(
                    f"Бот слухає канали {SOURCE_CHANNEL_IDS}, "
                    f"відправляє в чат '{destination.title}' ({DESTINATION_CHAT_ID})"
                )
            except ValueError as e:
                logger.error(f"Помилка доступу: {e}")
                return
            session_file = os.path.join(session_dir, 'session_name.session')
            if os.path.exists(session_file):
                os.chmod(session_file, 0o600)
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"Помилка: {e}. Повторне підключення через 10 секунд...")
            await asyncio.sleep(10)

if __name__ == '__main__':
    asyncio.run(main())
