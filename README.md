# EGE_BOT

Телеграм-бот для подготовки к ЕГЭ: ежедневные мотивационные сообщения с персональным обратным отсчётом дней до экзамена по каждому предмету. Поддерживает разные волны ЕГЭ (досрочная, основная, дополнительная, президентская пересдача) для каждого предмета отдельно.

## Возможности

- Онбординг через инлайн-кнопки (без слэш-команд в UI)
- Выбор предметов и волны ЕГЭ **отдельно для каждого предмета**
- Ежедневная рассылка мотивационной фразы с обратным отсчётом по всем предметам
- Проверка подписки на Telegram-канал перед доступом к боту
- Кнопка поддержки и пожеланий в настройках
- Отметка сданных экзаменов, поздравление после последнего предмета

## Стек

- **Python 3.11+**
- **aiogram 3.x** — Telegram Bot API framework
- **SQLAlchemy (async) + aiosqlite** — база данных
- **APScheduler** — планировщик ежедневных рассылок
- **proxychains4** — обход блокировки Telegram API на российских VPS

## Структура проекта

```
EGE_BOT/
├── bot.py                  # точка входа, запуск polling
├── config.py                # конфиг, переменные окружения, SUBJECT_WAVES
├── database/
│   ├── models.py             # User, UserSubject, ExamSchedule
│   └── db.py                 # engine, session
├── handlers/
│   ├── onboarding.py
│   ├── settings.py
│   ├── status.py
│   └── subscription.py
├── middlewares/
│   └── subscription.py       # проверка подписки на канал
├── keyboards/
│   └── settings.py
├── messages.py               # шаблоны текстов рассылки
├── scheduler.py              # APScheduler задачи
├── seed_exam_schedule.py     # загрузка расписания ЕГЭ
├── .env                      # переменные окружения (не в git)
└── requirements.txt
```

## Переменные окружения (.env)

```env
BOT_TOKEN=              # токен бота от @BotFather
DATABASE_URL=           # строка подключения к БД, см. ниже
CHANNEL_ID=             # @username или numeric ID канала для проверки подписки
CHANNEL_URL=            # https://t.me/your_channel — ссылка на канал для кнопки
SUPPORT_USERNAME=       # твой username без @, для кнопки поддержки
TIMEZONE=Europe/Moscow  # часовой пояс для планировщика
```

### Где взять DATABASE_URL

- **Managed PostgreSQL (рекомендуется для MVP):** [Neon](https://neon.tech) или [Supabase](https://supabase.com) — есть бесплатный тариф. После создания проекта строка подключения находится в Project Settings → Database → Connection string. Формат: `postgresql://user:password@host:port/dbname`
- **Если БД у хостинг-провайдера бота** (Amvera, Railway и т.д.) — строка выдаётся автоматически в разделе Environment/Variables соответствующего сервиса
- **Локально / на своём VPS** — собирается вручную из данных, заданных при установке PostgreSQL

Для SQLite (текущая локальная разработка) переменная не обязательна — используется файл базы напрямую через aiosqlite.

## Установка и запуск локально

```bash
git clone <repo_url>
cd EGE_BOT
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # заполнить своими значениями
python seed_exam_schedule.py   # загрузить расписание ЕГЭ в БД
python bot.py
```

## Развёртывание в продакшене

### Важно: блокировка Telegram в России

С 2026 года на российских VPS доступ к Telegram API нестабилен из-за замедлений. Бот должен работать через сервер за пределами РФ, либо через VPS в России с настроенным обходом.

**Вариант A — Amvera Cloud (рекомендуется для старта)**
Специализированный сервис для хостинга ботов с региона Варшава, оплата в рублях без иностранной карты. Деплой через `git push` или загрузку файлов в интерфейсе.

```bash
git push amvera master
```

Переменные окружения задаются в панели Amvera (Variables), включая `BOT_TOKEN`, `DATABASE_URL` и остальные.

**Вариант B — российский VPS + proxychains4**
Если сервер физически в России (как текущий RUVDS Moscow), нужен IPv6 SOCKS5-прокси и proxychains4 на уровне ОС:

```bash
# /etc/proxychains4.conf
[ProxyList]
socks5 <proxy_ip> <proxy_port> <user> <pass>
```

```bash
# systemd unit — запуск бота через proxychains
ExecStart=/usr/bin/proxychains4 /path/to/venv/bin/python /path/to/EGE_BOT/bot.py
```

**Вариант C — зарубежный VPS**
RuVDS (иностранный регион), AdminVPS (Нидерланды/Польша/Финляндия) — полный контроль, но требует ручной настройки сервера, systemd, обновлений.

### systemd сервис (пример)

```ini
[Unit]
Description=EGE_BOT Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/EGE_BOT
ExecStart=/path/to/venv/bin/python bot.py
Restart=always
RestartSec=5
EnvironmentFile=/path/to/EGE_BOT/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ege_bot
sudo systemctl start ege_bot
sudo systemctl status ege_bot
```

## Модель данных

| Таблица | Назначение |
|---|---|
| `User` | telegram id, имя, класс, часовой пояс, время уведомления, номер текущей фразы |
| `UserSubject` | связь пользователя с предметом: волна, дата экзамена, `is_passed` |
| `ExamSchedule` | расписание по предмету/волне/году, обновляется вручную раз в год |

**Ключевое правило:** волна ЕГЭ привязана к предмету, а не к аккаунту — один пользователь может сдавать разные предметы в разных волнах (пример: русский досрочно, математика в основную волну, химия пересдача в июле).

## Обновление расписания ЕГЭ на новый год

После публикации расписания Рособрнадзором:

```bash
python seed_exam_schedule.py --year 2027
```

Запрос в коде должен идти **без фильтра по году** с сортировкой `ORDER BY year DESC`, иначе есть риск получить `exam_date = NULL` для новых записей (баг, с которым уже сталкивались).

## Известные грабли

- `dp.start_polling()` должен идти строго после инициализации `bot` и `dp` в `bot.py`
- Не забывать `import os` и `ProxyConnector` при работе с прокси на уровне сессии бота (сейчас не используется — прокси на уровне ОС через proxychains4)
- Проверка подписки в middleware должна отрабатывать по `getChatMember`; для приватных каналов бот обязан быть администратором канала

## Roadmap (после MVP)

- [ ] Предэкзаменационные напоминания (за 7, 3, 1 день)
- [ ] Отдельное сообщение в день экзамена
- [ ] Admin-панель для обновления расписания без ручного запуска скрипта
- [ ] Поддержка нескольких волн/пересдач для одного предмета без дублей
- [ ] Виральное приглашение одноклассников после сдачи всех экзаменов

## Контакты

Поддержка и пожелания: [@your_username](https://t.me/your_username) — также доступно из бота через `Настройки → Поддержка и пожелания`
