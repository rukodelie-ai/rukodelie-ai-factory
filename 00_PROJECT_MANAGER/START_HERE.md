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

> Прочитай CURRENT_STATE.md → затем этот файл → ты готов к работе.

| Шаг | Файл | Зачем |
|-----|------|-------|
| **0** | **`00_PROJECT_MANAGER/CURRENT_STATE.md`** | **⚠️ ЧИТАТЬ ПЕРВЫМ. Что заморожено, что в работе, что запрещено** |
| 1 | `00_PROJECT_MANAGER/START_HERE.md` | Этот файл. Ориентация в проекте |
| 2 | `00_PROJECT_MANAGER/PROJECT_MEMORY.md` | Полный контекст: что строим, архитектура, решения |
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

**Дата:** 2026-07-08 | **MVP AI Seller завершён. Исследование OData полностью завершено → следующий этап: реализация AI Memory MVP**

| Что готово | Что не готово |
|-----------|--------------|
| ✅ Вся стратегическая документация | ❌ Google Sheets подключение (реализация готова, ждёт кредов) |
| ✅ catalog_v1.csv (50 товаров, 30 полей, все published) | ❌ Бета-тест с 3–5 реальными клиентами |
| ✅ SYSTEM_PROMPT.md v1.1 (Алина, 3 языка) | ❌ AI Memory MVP код (спецификация подтверждена, ждёт команды на разработку) |
| ✅ Telegram Bot + Claude API + полный цикл заказа | ❌ Этап 2 (SEO/Analytics) — не начат, не приоритет |
| ✅ Live-test пройден на реальном боте (заказ R-20260708-093733-947983) | — |
| ✅ Owner Review проведён владельцем 2026-07-08 | — |
| ✅ Полный аудит клиентской экосистемы 1С завершён 2026-07-08 | — |

---

## Следующий шаг

### ⏭ Утверждённый следующий этап: РЕАЛИЗАЦИЯ AI MEMORY MVP

Owner Review проведён, исследовательский этап OData полностью завершён. Продуктовое
решение владельца: стратегический этап OData (полный каталог/остатки) отложен;
первой практической OData-интеграцией утверждён **AI Memory MVP** — Алина узнаёт
клиента по телефону и использует историю его покупок из 1С для персонализации.
Полный аудит клиентской экосистемы (сайт, Kaspi, Halyk, Ozon, Wolt, розница,
лояльность) подтвердил Product Specification корректной без изменений архитектуры.
Полная спецификация — `00_PROJECT_MANAGER/CURRENT_STATE.md`, раздел 🧠 AI MEMORY MVP,
и `00_PROJECT_MANAGER/PROJECT_MEMORY.md`, раздел 14.

**Реализация не начата.** Код по AI Memory MVP пишется только после отдельного
задания на план реализации — следующая команда по проекту должна быть именно на разработку.

**Цель первого реального заказа через бот — достигнута: 2026-07-08.**

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
