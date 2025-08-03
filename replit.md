# Telegram Бот Контролю Часу

## Overview

Python проект з Telegram ботом, який контролює час надсилання повідомлень українською мовою. Бот дозволяє спілкування тільки у вказані години (8:00-23:00) та відповідає користувачам відповідними повідомленнями залежно від поточного часу.

## User Preferences

Preferred communication style: Simple, everyday language (Ukrainian).
Project language: Ukrainian interface and messages.

## Recent Changes

- 2025-08-03: Створено новий Python проект з вашим кодом на українській мові
- 2025-08-03: Оновлено до сучасної версії python-telegram-bot (20.8) з async/await
- 2025-08-03: Бот успішно запущено та підключено до Telegram API
- 2025-08-03: Створено українську документацію у README.md
- 2025-08-03: Додано підтримку київського часу (Europe/Kiev timezone) з бібліотекою pytz
- 2025-08-03: Налаштовано бота для роботи в групах з персоналізованими відповідями
- 2025-08-03: Додано систему збереження та перегляду історії повідомлень з JSON файлом
- 2025-08-03: Впроваджено захист приватності - доступ до історії тільки для адміністраторів групи
- 2025-08-03: Додано приватні повідомлення адміністраторам - історія та статистика надсилаються в особисті чати
- 2025-08-03: Створено систему відзначення повідомлень як відповіджених з командою /replied [ID]
- 2025-08-03: Переробка на автоматичний контроль групи - бот блокує/розблокує можливість писати повідомлення
- 2025-08-03: Додано автоматичні повідомлення о 8:00 та 23:00 про початок/кінець робочого дня
- 2025-08-03: Виправлено спам повідомлень - тепер тільки при зміні стану робочих годин
- 2025-08-03: Додано адмінку для налаштування робочих годин (/set_hours, /show_hours)

## System Architecture

### Bot Framework Architecture
- **Telegram Bot API Integration**: Uses `python-telegram-bot` library for handling Telegram API interactions
- **Handler-Based Design**: Implements separate handlers for commands (`/start`) and text messages using the Application pattern
- **Asynchronous Processing**: Built on async/await pattern for efficient message handling

### Configuration Management
- **Environment-Based Config**: Uses `.env` files and environment variables for secure token management
- **Centralized Settings**: All configuration constants stored in `bot/config.py` module
- **Runtime Flexibility**: Time ranges configurable via `ALLOWED_START_HOUR` and `ALLOWED_END_HOUR` environment variables

### Time Control Logic
- **Hour-Based Filtering**: Core business logic validates current time against allowed hours range
- **Real-Time Validation**: Each message triggers time validation using `is_within_allowed_hours()` function
- **Smart Response System**: Different message templates for allowed vs restricted hours

### Error Handling and Logging
- **Comprehensive Logging**: File-based (`bot.log`) and console logging with timestamp, level, and message details
- **Error Handler Integration**: Dedicated error handler for API failures and unexpected exceptions
- **Startup Validation**: Bot token validation before application initialization

### Project Structure
- **Modular Design**: Separated into `bot/` package with distinct modules for configuration, handlers, and main entry point
- **Handler Separation**: Commands and message handlers organized in dedicated `handlers.py` module
- **Package Organization**: Clean package structure with `__init__.py` and version management

## External Dependencies

### Core Libraries
- **python-telegram-bot**: Primary Telegram Bot API wrapper for handling updates, commands, and messages
- **python-dotenv**: Environment variable loading from `.env` files for configuration management

### System Dependencies
- **Python 3.7+**: Minimum Python version requirement for async/await support and modern language features

### Telegram Services
- **Telegram Bot API**: Direct integration with Telegram's bot platform for message handling and user interaction
- **BotFather Integration**: Bot token management through Telegram's official bot creation service