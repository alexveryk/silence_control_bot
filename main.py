from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from datetime import datetime
import os
import logging
import pytz
import json
from pathlib import Path

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашого бота з environment variables
TOKEN = os.getenv('BOT_TOKEN')

# Файл для збереження повідомлень
MESSAGES_FILE = 'messages_history.json'

# Глобальна змінна для відстеження останнього статусу кожного чату
last_status_per_chat = {}

# Глобальні змінні для налаштування робочих годин
working_hours = {
    'start_hour': 8,
    'end_hour': 23
}

# Функція для збереження повідомлення
def save_message(user_name, user_id, chat_id, chat_type, message_text, timestamp, status):
    """Зберігає повідомлення у файл для історії"""
    try:
        # Читаємо існуючі повідомлення
        if Path(MESSAGES_FILE).exists():
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
        else:
            messages = []
        
        # Додаємо нове повідомлення з унікальним ID
        message_id = len(messages) + 1
        message_data = {
            'id': message_id,
            'user_name': user_name,
            'user_id': user_id,
            'chat_id': chat_id,
            'chat_type': chat_type,
            'message_text': message_text,
            'timestamp': timestamp,
            'status': status,  # 'received', 'replied', 'rejected_time', 'manually_replied'
            'replied_by': None,  # ID адміністратора, який відзначив як відповіджене
            'reply_timestamp': None
        }
        messages.append(message_data)
        
        # Зберігаємо назад у файл (тримаємо останні 1000 повідомлень)
        if len(messages) > 1000:
            messages = messages[-1000:]
            
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Помилка збереження повідомлення: {e}")

# Функція для отримання останніх повідомлень
def get_recent_messages(limit=10):
    """Повертає останні повідомлення"""
    try:
        if Path(MESSAGES_FILE).exists():
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                
                # Оновлюємо старі записи без ID
                updated = False
                for i, msg in enumerate(messages):
                    if 'id' not in msg:
                        msg['id'] = i + 1
                        msg['replied_by'] = None
                        msg['reply_timestamp'] = None
                        updated = True
                
                # Зберігаємо оновлені дані
                if updated:
                    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f_write:
                        json.dump(messages, f_write, ensure_ascii=False, indent=2)
                
                return messages[-limit:] if messages else []
        return []
    except Exception as e:
        logger.error(f"Помилка читання повідомлень: {e}")
        return []

# Функція для перевірки часу за київським часом
def is_allowed_time():
    # Отримуємо поточний час за київським часом (Europe/Kiev)
    kyiv_tz = pytz.timezone('Europe/Kiev')
    current_time_kyiv = datetime.now(kyiv_tz)
    current_hour = current_time_kyiv.hour
    return working_hours['start_hour'] <= current_hour < working_hours['end_hour']

# Функція для отримання поточного часу у Києві
def get_kyiv_time_string():
    kyiv_tz = pytz.timezone('Europe/Kiev')
    current_time_kyiv = datetime.now(kyiv_tz)
    return current_time_kyiv.strftime("%H:%M")

# Функція для блокування/розблокування чату
async def set_chat_permissions(context, chat_id, can_send_messages=True):
    """Встановлює дозволи для чату"""
    try:
        from telegram import ChatPermissions
        permissions = ChatPermissions(
            can_send_messages=can_send_messages,
            can_send_audios=can_send_messages,
            can_send_documents=can_send_messages,
            can_send_photos=can_send_messages,
            can_send_videos=can_send_messages,
            can_send_video_notes=can_send_messages,
            can_send_voice_notes=can_send_messages,
            can_send_polls=can_send_messages,
            can_send_other_messages=can_send_messages,
            can_add_web_page_previews=can_send_messages
        )
        await context.bot.set_chat_permissions(chat_id=chat_id, permissions=permissions)
        return True
    except Exception as e:
        logger.error(f"Помилка зміни дозволів чату {chat_id}: {e}")
        return False

# Функція для надсилання повідомлення про статус часу
async def send_time_status_message(context, chat_id, is_allowed):
    """Надсилає повідомлення про статус робочого часу тільки при зміні статусу"""
    global last_status_per_chat
    
    # Перевіряємо чи змінився статус для цього чату
    current_status = 'allowed' if is_allowed else 'blocked'
    last_status = last_status_per_chat.get(chat_id, None)
    
    # Якщо статус не змінився, не надсилаємо повідомлення
    if last_status == current_status:
        return
    
    try:
        current_time = get_kyiv_time_string()
        if is_allowed:
            message = f"🌅 Доброго ранку! \n\nТепер можна писати повідомлення в групі.\n\nРобочі години: {working_hours['start_hour']:02d}:00 - {working_hours['end_hour']:02d}:00\nПоточний час у Києві: {current_time}"
        else:
            message = f"🌙 Робочий день закінчено!\n\nПовідомлення після {working_hours['end_hour']:02d}:00 неможна написати.\nПовертайтесь до нас після {working_hours['start_hour']:02d}:00 ранку.\n\nПоточний час у Києві: {current_time}"
        
        await context.bot.send_message(chat_id=chat_id, text=message)
        
        # Зберігаємо поточний статус для цього чату
        last_status_per_chat[chat_id] = current_status
        
        logger.info(f"Надіслано повідомлення про зміну статусу до чату {chat_id}: {current_status}")
    except Exception as e:
        logger.error(f"Помилка надсилання повідомлення про час до чату {chat_id}: {e}")

# Функція для обробки повідомлень (тепер тільки для особистих чатів та команд)
async def message_handler(update: Update, context):
    current_time_str = get_kyiv_time_string()
    user_name = update.message.from_user.first_name or "друже"
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    chat_type = update.message.chat.type
    message_text = update.message.text
    
    # Логування отриманого повідомлення
    logger.info(f"Повідомлення від {user_name} (ID: {user_id}) в чаті {chat_id} ({chat_type}): {message_text}")
    
    # В особистих чатах завжди відповідаємо
    if chat_type == 'private':
        if not is_allowed_time():
            response = f"Зараз не робочий час. Можна писати з {working_hours['start_hour']:02d}:00 до {working_hours['end_hour']:02d}:00.\n\nПоточний час у Києві: {current_time_str}"
            await update.message.reply_text(response)
            save_message(user_name, user_id, chat_id, chat_type, message_text, current_time_str, 'rejected_time')
        else:
            response_message = f"Дякую за повідомлення, {user_name}! 🙏\n\nПоточний час у Києві: {current_time_str}"
            await update.message.reply_text(response_message)
            save_message(user_name, user_id, chat_id, chat_type, message_text, current_time_str, 'replied')
    else:
        # В групах зберігаємо повідомлення для статистики
        if is_allowed_time():
            save_message(user_name, user_id, chat_id, chat_type, message_text, current_time_str, 'received')
        else:
            # Це повідомлення не повинно дійти, але якщо дійшло - зберігаємо
            save_message(user_name, user_id, chat_id, chat_type, message_text, current_time_str, 'blocked_time')

# Функція для старту бота
async def start(update: Update, context):
    current_time_str = get_kyiv_time_string()
    user_name = update.message.from_user.first_name or "друже"
    chat_type = "групі" if update.message.chat.type in ['group', 'supergroup'] else "особистому чаті"
    
    start_message = f"""Привіт, {user_name}! 👋

Я бот, який працює з {working_hours['start_hour']:02d}:00 до {working_hours['end_hour']:02d}:00 за київським часом.

Я дякую за повідомлення та обов'язково відповідаю!

**Доступні команди:**
/start - показати це повідомлення
/history або /messages - історія останніх 10 повідомлень (приватно адмінам)
/stats - статистика всіх повідомлень (приватно адмінам)
/replied [ID] - відзначити повідомлення як відповіджене (тільки адміни)
/update_permissions - оновити дозволи групи (тільки адміни)
/clear_history - очистити всю історію (тільки власник)

**Адмінські команди:**
/set_hours [початок] [кінець] - встановити робочі години (наприклад: /set_hours 9 22)
/show_hours - показати поточні робочі години

Поточний час у Києві: {current_time_str}
Робота в {chat_type}"""
    
    await update.message.reply_text(start_message)

# Функція для перевірки прав адміністратора
async def is_admin(update: Update, context):
    """Перевіряє чи є користувач адміністратором в групі"""
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    
    # В особистому чаті завжди дозволяємо
    if update.message.chat.type == 'private':
        return True
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator']
    except Exception as e:
        logger.error(f"Помилка перевірки прав адміністратора: {e}")
        return False

# Команда для перегляду останніх повідомлень (тільки для адмінів)
async def history_command(update: Update, context):
    """Показує останні повідомлення (тільки для адміністраторів)"""
    try:
        # Перевіряємо права адміністратора
        if not await is_admin(update, context):
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам групи.")
            return
        recent_messages = get_recent_messages(10)
        
        if not recent_messages:
            await update.message.reply_text("📝 Історія повідомлень порожня.")
            return
        
        history_text = "📋 **Останні 10 повідомлень:**\n\n"
        
        for i, msg in enumerate(recent_messages, 1):
            status_emoji = {
                'replied': '✅',
                'manually_replied': '💬',
                'rejected_time': '⏰',
                'blocked_time': '🚫',
                'received': '📨'
            }.get(msg['status'], '❓')
            
            # Додаткова інформація для відповіджених повідомлень
            reply_info = ""
            if msg['status'] == 'manually_replied' and msg.get('replied_by'):
                reply_info = f" (відповів адмін, {msg.get('reply_timestamp', 'невідомий час')})"
            
            # Безпечне екранування тексту для Markdown
            safe_user_name = msg['user_name'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]')
            safe_message_text = msg['message_text'][:50].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]')
            if len(msg['message_text']) > 50:
                safe_message_text += "..."
            
            history_text += f"{i}. {status_emoji} *{safe_user_name}* ({msg['timestamp']}) [ID: {msg.get('id', 'N/A')}]\n"
            history_text += f"   💬 {safe_message_text}\n"
            history_text += f"   📍 {msg['chat_type']} | Статус: {msg['status']}{reply_info}\n\n"
        
        # Відправляємо приватно адміністратору
        user_id = update.message.from_user.id
        
        # Розбиваємо на частини якщо занадто довго
        if len(history_text) > 4000:
            parts = [history_text[i:i+4000] for i in range(0, len(history_text), 4000)]
            for part in parts:
                await context.bot.send_message(chat_id=user_id, text=part, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=user_id, text=history_text, parse_mode='Markdown')
        
        # Підтвердждення в групі
        if update.message.chat.type != 'private':
            await update.message.reply_text("✅ Історію надіслано вам в особисті повідомлення.")
            
    except Exception as e:
        logger.error(f"Помилка при показі історії: {e}")
        await update.message.reply_text("❌ Помилка при отриманні історії повідомлень.")

# Команда для статистики повідомлень (тільки для адмінів)
async def stats_command(update: Update, context):
    """Показує статистику повідомлень (тільки для адміністраторів)"""
    try:
        # Перевіряємо права адміністратора
        if not await is_admin(update, context):
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам групи.")
            return
        if not Path(MESSAGES_FILE).exists():
            await update.message.reply_text("📊 Статистика: поки що немає повідомлень.")
            return
            
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            all_messages = json.load(f)
        
        if not all_messages:
            await update.message.reply_text("📊 Статистика: поки що немає повідомлень.")
            return
        
        # Підрахунок статистики
        total = len(all_messages)
        replied = len([m for m in all_messages if m['status'] == 'replied'])
        rejected = len([m for m in all_messages if m['status'] == 'rejected_time'])
        
        # Унікальні користувачі
        unique_users = len(set(m['user_name'] for m in all_messages))
        
        # Сьогоднішні повідомлення
        today_kyiv = get_kyiv_time_string()[:5]  # HH:MM format
        today_messages = [m for m in all_messages if m['timestamp'][:5] == today_kyiv[:5]]
        today_count = len(today_messages)
        
        stats_text = f"""📊 **Статистика повідомлень**

🔢 **Загальна кількість:** {total}
✅ **Відповіли:** {replied}
⏰ **Відхилено (час):** {rejected}
👥 **Унікальних користувачів:** {unique_users}
📅 **Сьогодні:** {today_count}

⏰ **Поточний час у Києві:** {get_kyiv_time_string()}
🕒 **Робочі години:** 8:00 - 23:00"""

        # Відправляємо приватно адміністратору
        user_id = update.message.from_user.id
        await context.bot.send_message(chat_id=user_id, text=stats_text, parse_mode='Markdown')
        
        # Підтвердждення в групі
        if update.message.chat.type != 'private':
            await update.message.reply_text("📊 Статистику надіслано вам в особисті повідомлення.")
        
    except Exception as e:
        logger.error(f"Помилка при показі статистики: {e}")
        await update.message.reply_text("❌ Помилка при отриманні статистики.")

# Команда для очищення історії (тільки для власника)
async def clear_history_command(update: Update, context):
    """Очищує історію повідомлень (тільки для власника групи)"""
    try:
        user_id = update.message.from_user.id
        chat_id = update.message.chat.id
        
        # В особистому чаті завжди дозволяємо
        if update.message.chat.type == 'private':
            is_owner = True
        else:
            try:
                member = await context.bot.get_chat_member(chat_id, user_id)
                is_owner = member.status == 'creator'
            except Exception as e:
                logger.error(f"Помилка перевірки прав власника: {e}")
                is_owner = False
        
        if not is_owner:
            await update.message.reply_text("❌ Ця команда доступна тільки власнику групи.")
            return
        
        # Очищаємо історію
        if Path(MESSAGES_FILE).exists():
            with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
            await update.message.reply_text("✅ Історію повідомлень очищено.")
            logger.info(f"Історію очищено власником {update.message.from_user.first_name} (ID: {user_id})")
        else:
            await update.message.reply_text("📝 Історія і так порожня.")
            
    except Exception as e:
        logger.error(f"Помилка при очищенні історії: {e}")
        await update.message.reply_text("❌ Помилка при очищенні історії.")

# Команда для відзначення повідомлення як відповіджене
async def mark_replied_command(update: Update, context):
    """Відзначає повідомлення як відповіджене (тільки для адміністраторів)"""
    try:
        # Перевіряємо права адміністратора
        if not await is_admin(update, context):
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам групи.")
            return
        
        # Отримуємо ID повідомлення з аргументів
        if not context.args:
            await update.message.reply_text("❌ Вкажіть ID повідомлення. Приклад: /replied 5")
            return
        
        try:
            message_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ ID повідомлення має бути числом. Приклад: /replied 5")
            return
        
        # Читаємо історію повідомлень
        if not Path(MESSAGES_FILE).exists():
            await update.message.reply_text("❌ Історія повідомлень порожня.")
            return
            
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        # Знаходимо повідомлення за ID
        message_found = None
        for msg in messages:
            if msg.get('id') == message_id:
                message_found = msg
                break
        
        if not message_found:
            await update.message.reply_text(f"❌ Повідомлення з ID {message_id} не знайдено.")
            return
        
        # Відзначаємо як відповіджене
        message_found['status'] = 'manually_replied'
        message_found['replied_by'] = update.message.from_user.id
        message_found['reply_timestamp'] = get_kyiv_time_string()
        
        # Зберігаємо оновлену історію
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        
        # Відправляємо підтвердження приватно
        user_id = update.message.from_user.id
        # Безпечне екранування для Markdown
        safe_user_name = message_found['user_name'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]')
        safe_message_text = message_found['message_text'][:100].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]')
        if len(message_found['message_text']) > 100:
            safe_message_text += "..."
        
        confirmation_text = f"✅ Повідомлення ID {message_id} від *{safe_user_name}* відзначено як відповіджене.\n\n💬 Текст: {safe_message_text}"
        
        await context.bot.send_message(chat_id=user_id, text=confirmation_text, parse_mode='Markdown')
        
        # Підтвердження в групі
        if update.message.chat.type != 'private':
            await update.message.reply_text(f"✅ Повідомлення ID {message_id} відзначено як відповіджене.")
        
        logger.info(f"Повідомлення ID {message_id} відзначено як відповіджене адміністратором {update.message.from_user.first_name} (ID: {user_id})")
        
    except Exception as e:
        logger.error(f"Помилка при відзначенні повідомлення: {e}")
        await update.message.reply_text("❌ Помилка при відзначенні повідомлення.")

# Функція для перевірки та оновлення статусу всіх груп
async def check_and_update_group_permissions(context):
    """Перевіряє час та оновлює дозволи для всіх груп"""
    try:
        is_allowed = is_allowed_time()
        
        # Читаємо список груп з повідомлень
        if Path(MESSAGES_FILE).exists():
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Отримуємо унікальні ID груп
            group_chats = set()
            for msg in messages:
                if msg.get('chat_type') in ['group', 'supergroup']:
                    group_chats.add(msg['chat_id'])
            
            # Оновлюємо дозволи для кожної групи
            for chat_id in group_chats:
                success = await set_chat_permissions(context, chat_id, is_allowed)
                if success:
                    # Надсилаємо повідомлення про зміну статусу
                    await send_time_status_message(context, chat_id, is_allowed)
                    
        logger.info(f"Оновлено дозволи для груп: {'дозволено' if is_allowed else 'заборонено'}")
        
    except Exception as e:
        logger.error(f"Помилка оновлення дозволів груп: {e}")

# Команда для ручного оновлення дозволів (тільки для адмінів)
async def update_permissions_command(update: Update, context):
    """Ручне оновлення дозволів групи (тільки для адміністраторів)"""
    try:
        # Перевіряємо права адміністратора
        if not await is_admin(update, context):
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам групи.")
            return
        
        chat_id = update.message.chat.id
        is_allowed = is_allowed_time()
        
        success = await set_chat_permissions(context, chat_id, is_allowed)
        if success:
            await send_time_status_message(context, chat_id, is_allowed)
            await update.message.reply_text("✅ Дозволи групи оновлено.")
        else:
            await update.message.reply_text("❌ Помилка оновлення дозволів групи.")
        
    except Exception as e:
        logger.error(f"Помилка команди оновлення дозволів: {e}")
        await update.message.reply_text("❌ Помилка при оновленні дозволів.")

# Команда для встановлення робочих годин (тільки для адмінів)
async def set_hours_command(update: Update, context):
    """Встановлення робочих годин (тільки для адміністраторів)"""
    global working_hours, last_status_per_chat
    
    try:
        # Перевіряємо права адміністратора
        if not await is_admin(update, context):
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам групи.")
            return
        
        # Перевіряємо аргументи
        if len(context.args) != 2:
            await update.message.reply_text("❌ Використання: /set_hours [початок] [кінець]\nПриклад: /set_hours 9 22")
            return
        
        try:
            start_hour = int(context.args[0])
            end_hour = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ Години повинні бути числами. Приклад: /set_hours 9 22")
            return
        
        # Перевіряємо валідність годин
        if not (0 <= start_hour <= 23) or not (0 <= end_hour <= 23):
            await update.message.reply_text("❌ Години повинні бути від 0 до 23.")
            return
        
        if start_hour >= end_hour:
            await update.message.reply_text("❌ Час початку повинен бути менше часу закінчення.")
            return
        
        # Зберігаємо нові години
        old_start = working_hours['start_hour']
        old_end = working_hours['end_hour']
        working_hours['start_hour'] = start_hour
        working_hours['end_hour'] = end_hour
        
        # Скидаємо статуси чатів для повторного надсилання повідомлень
        last_status_per_chat.clear()
        
        success_message = f"""✅ Робочі години оновлено!

📅 Було: {old_start:02d}:00 - {old_end:02d}:00
🕐 Тепер: {start_hour:02d}:00 - {end_hour:02d}:00

Автоматичний контроль груп оновлено."""
        
        await update.message.reply_text(success_message)
        logger.info(f"Робочі години змінено: {start_hour}:00-{end_hour}:00 (адмін: {update.message.from_user.first_name})")
        
    except Exception as e:
        logger.error(f"Помилка команди set_hours: {e}")
        await update.message.reply_text("❌ Помилка при встановленні робочих годин.")

# Команда для показу поточних робочих годин
async def show_hours_command(update: Update, context):
    """Показати поточні робочі години"""
    try:
        current_time = get_kyiv_time_string()
        is_working = is_allowed_time()
        status = "🟢 АКТИВНО" if is_working else "🔴 НЕАКТИВНО"
        
        message = f"""🕐 **Робочі години бота**

⏰ Початок: {working_hours['start_hour']:02d}:00
⏰ Кінець: {working_hours['end_hour']:02d}:00

🌍 Поточний час у Києві: {current_time}
📊 Статус: {status}

{'✅ Зараз можна писати повідомлення' if is_working else '❌ Зараз повідомлення заблоковані'}"""
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Помилка команди show_hours: {e}")
        await update.message.reply_text("❌ Помилка при отриманні інформації про години.")

# Головна функція для запуску бота
def main():
    if not TOKEN:
        logger.error("BOT_TOKEN не знайдено в environment variables!")
        return
    
    current_kyiv_time = get_kyiv_time_string()
    logger.info("Запускаю Telegram бота для контролю часу...")
    logger.info(f"Дозволені години: {working_hours['start_hour']:02d}:00 - {working_hours['end_hour']:02d}:00 (за київським часом)")
    logger.info(f"Поточний час у Києві: {current_kyiv_time}")
    
    # Створення Application
    application = Application.builder().token(TOKEN).build()
    
    # Додавання команд
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('history', history_command))
    application.add_handler(CommandHandler('messages', history_command))  # альтернативна команда
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_handler(CommandHandler('clear_history', clear_history_command))
    application.add_handler(CommandHandler('replied', mark_replied_command))
    application.add_handler(CommandHandler('update_permissions', update_permissions_command))
    application.add_handler(CommandHandler('set_hours', set_hours_command))
    application.add_handler(CommandHandler('show_hours', show_hours_command))
    
    # Додавання обробника для повідомлень
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Додавання автоматичної перевірки часу кожну хвилину
    try:
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(check_and_update_group_permissions, interval=60, first=10)
            logger.info("Автоматична перевірка часу налаштована: кожну хвилину")
        else:
            logger.warning("JobQueue недоступний, автоматична перевірка вимкнена")
    except Exception as e:
        logger.error(f"Помилка налаштування автоматичної перевірки: {e}")
    
    # Запуск бота
    logger.info("Бот запускається...")
    logger.info("Автоматична перевірка часу: кожну хвилину")
    application.run_polling()

if __name__ == '__main__':
    main()
