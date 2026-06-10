# START HERE — RUKODELIE AI FACTORY
> Главный вход в проект. Читается первым — человеком или любым AI-агентом.

---

## Путь проекта

```
iCloud Drive / RUKODELIE_AI_FACTORY /
```

**Полный путь на macOS:**
```
/Users/sergey/Library/Mobile Documents/com~apple~CloudDocs/RUKODELIE_AI_FACTORY
```

---

## Что читать первым

> Прочитай этот файл → затем PROJECT_MEMORY.md → ты готов к работе.

| Шаг | Файл | Зачем |
|-----|------|-------|
| 1 | `00_PROJECT_MANAGER/START_HERE.md` | Этот файл. Ориентация в проекте |
| 2 | `00_PROJECT_MANAGER/PROJECT_MEMORY.md` | Полный контекст: что строим, где остановились, что делать |
| 3 | `00_PROJECT_MANAGER/PROJECT_MEMORY_INDEX.md` | Карта всех ключевых документов |

---

## Что читать вторым (по задаче)

| Если работаешь над... | Читай |
|----------------------|-------|
| AI Seller / Telegram Bot | `01_AI_SELLER/SYSTEM_PROMPT.md` → `01_AI_SELLER/MVP_AI_SELLER_PLAN.md` |
| Каталогом товаров | `02_PRODUCT_DATABASE/catalog_v1.csv` → `09_DOCUMENTS/SALES_MODEL_RUKODELIE.md` |
| Стратегией | `MASTER_PLAN.md` → `VISION.md` → `ROADMAP.md` |
| Текущими задачами | `TASKS.md` |
| Историей сессий | `00_PROJECT_MANAGER/SESSION_SUMMARY_2026-06-10.md` |
| Правилами каталога | `08_KNOWLEDGE_BASE/SOP_PRODUCT_CATALOG.md` |

---

## Где находятся ключевые файлы

| Что | Путь |
|-----|------|
| **Память проекта** | `00_PROJECT_MANAGER/PROJECT_MEMORY.md` |
| **Индекс документов** | `00_PROJECT_MANAGER/PROJECT_MEMORY_INDEX.md` |
| **История сессий** | `00_PROJECT_MANAGER/SESSION_SUMMARY_*.md` |
| **System Prompt Алины** | `01_AI_SELLER/SYSTEM_PROMPT.md` |
| **Требования к AI Seller** | `01_AI_SELLER/AI_SELLER_REQUIREMENTS.md` |
| **Product Database** | `02_PRODUCT_DATABASE/catalog_v1.csv` |
| **Модель продаж** | `09_DOCUMENTS/SALES_MODEL_RUKODELIE.md` |
| **Roadmap** | `ROADMAP.md` |
| **Текущие задачи** | `TASKS.md` |

---

## Текущее состояние проекта

**Дата:** 2026-06-10 | **Sprint #1, День 6**

| Что готово | Что не готово |
|-----------|--------------|
| ✅ Вся стратегическая документация | ❌ Telegram Bot (код) |
| ✅ catalog_v1.csv (50 товаров, 30 полей) | ❌ Google Sheets |
| ✅ SYSTEM_PROMPT.md v1.1 (Алина, 3 языка) | ❌ Claude API интеграция |
| ✅ AI_SELLER_REQUIREMENTS.md | ❌ 48/50 товаров в статусе draft |

---

## Следующий шаг

### Владелец (≈ 30 минут)

1. **Открыть** `02_PRODUCT_DATABASE/catalog_v1.csv`
2. **Изменить** `status: draft → published` для нужных категорий (стразы, ленты, украшения)
3. **Получить** Telegram Bot токен: Telegram → @BotFather → `/newbot`
4. **Получить** Claude API ключ: console.anthropic.com → сохранить в `09_DOCUMENTS/CREDENTIALS.md`

### AI PM (≈ 8 часов разработки)

1. Создать Google Sheets (4 листа: catalog, orders, settings, analytics)
2. Написать код Telegram Bot (Python + aiogram + Claude API)
3. Протестировать 20 диалогов в закрытом режиме
4. Открыть для первых 5–10 клиентов

**Цель: первый реальный заказ через бот — 14 июня 2026**

---

## Структура проекта (кратко)

```
RUKODELIE_AI_FACTORY/          ← Obsidian Vault (корень)
├── MASTER_PLAN.md             ← Миссия и роли агентов
├── VISION.md                  ← Цели 1 год + 3 года
├── ROADMAP.md                 ← План 30/90/365 дней
├── TASKS.md                   ← Текущий спринт
│
├── 00_PROJECT_MANAGER/        ← Память и управление
│   ├── START_HERE.md          ← Этот файл
│   ├── PROJECT_MEMORY.md      ← Главная память проекта
│   ├── PROJECT_MEMORY_INDEX.md
│   └── SESSION_SUMMARY_*.md
│
├── 01_AI_SELLER/              ← AI-продавец Алина ⭐
│   ├── SYSTEM_PROMPT.md       ← Production prompt v1.1
│   ├── AI_SELLER_REQUIREMENTS.md
│   └── MVP_AI_SELLER_PLAN.md
│
├── 02_PRODUCT_DATABASE/       ← Каталог товаров ⭐
│   ├── catalog_v1.csv         ← 50 товаров, 30 полей
│   └── ...
│
├── 03_TELEGRAM/               ← Telegram Bot (в разработке)
├── 08_KNOWLEDGE_BASE/         ← SOP и инструкции
├── 09_DOCUMENTS/              ← Аналитика и отчёты
└── 10_PROMPTS/                ← Библиотека промптов
```

---

## Правила для AI-агентов

1. **Все новые файлы** сохранять только внутри структуры проекта — в соответствующей папке агента.
2. **Не создавать файлы в корне** без явного указания.
3. **PROJECT_MEMORY.md обновлять** в разделах 3, 7, 8, 13 при каждом значимом изменении.
4. **SESSION_SUMMARY** создавать в `00_PROJECT_MANAGER/` (не в `09_DOCUMENTS/`).
5. **Работать только с `status = published`** товарами из catalog_v1.csv.

---

*Этот файл — постоянный. Обновляй только разделы «Текущее состояние» и «Следующий шаг».*
