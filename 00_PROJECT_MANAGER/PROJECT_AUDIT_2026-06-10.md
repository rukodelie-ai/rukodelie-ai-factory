# PROJECT AUDIT — RUKODELIE AI FACTORY
> Дата аудита: 2026-06-10 | Аудитор: AI Project Manager  
> Охват: все .md файлы, .csv файлы, структура папок, ссылки между документами

---

## Итоговая оценка структуры: **7 / 10**

| Критерий | Оценка | Комментарий |
|----------|--------|------------|
| Ясность структуры | 9/10 | Логичная нумерация папок, понятные имена |
| Размещение файлов | 6/10 | 2 файла лежат не в своей папке |
| Целостность ссылок | 5/10 | 17 битых ссылок на документы, которых нет |
| Единообразие имён | 7/10 | Расхождение: `credentials.md` vs `CREDENTIALS.md` |
| Полнота документации | 6/10 | Много запланированных файлов ещё не создано |
| Навигация | 9/10 | START_HERE → PROJECT_MEMORY → INDEX работает |

---

## 1. Что существует и корректно связано

### Корневые файлы (4/4) — все OK

| Файл | Размер | Связи |
|------|--------|-------|
| `MASTER_PLAN.md` | 10,9 KB | Ссылается из SESSION_SUMMARY, PROJECT_MEMORY |
| `VISION.md` | 8,6 KB | Ссылается из SESSION_SUMMARY, START_HERE |
| `ROADMAP.md` | 8,6 KB | Ссылается из START_HERE, PROJECT_MEMORY |
| `TASKS.md` | 8,3 KB | Ссылается из START_HERE, PROJECT_MEMORY, SESSION_SUMMARY |

### 00_PROJECT_MANAGER (6/6) — все OK

| Файл | Размер | Статус |
|------|--------|--------|
| `START_HERE.md` | 6,1 KB | ✅ Все ссылки ведут на существующие файлы |
| `PROJECT_MEMORY.md` | 30,8 KB | ✅ Корректен, но ссылается на несуществующий код |
| `PROJECT_MEMORY_INDEX.md` | 7,2 KB | ✅ Все 20+ ссылок на существующие файлы |
| `SESSION_SUMMARY_2026-06-10.md` | 18,3 KB | ✅ Корректно размещён |
| `OBSIDIAN_INTEGRATION.md` | 8,2 KB | ✅ 1 битая ссылка (шаблон) |
| `GITHUB_SETUP.md` | 10,9 KB | ✅ Описывает создание .gitignore, который ещё не создан |

### 01_AI_SELLER (3/3) — все OK

| Файл | Размер | Статус |
|------|--------|--------|
| `SYSTEM_PROMPT.md` | 55,0 KB | ✅ Главный файл проекта, v1.1 |
| `AI_SELLER_REQUIREMENTS.md` | 42,0 KB | ✅ Корректен |
| `MVP_AI_SELLER_PLAN.md` | 30,4 KB | ⚠️ Ссылается на 12 несуществующих файлов |

### 02_PRODUCT_DATABASE (5/5) — все OK, есть дубликат

| Файл | Размер | Статус |
|------|--------|--------|
| `catalog_v1.csv` | 47,2 KB | ✅ Основная база, 50 товаров |
| `catalog_raw.csv` | 17,0 KB | ✅ Архивный исходник первого парсинга |
| `TEMPLATE_PRODUCT_CARD.md` | 2,2 KB | ✅ Пустой шаблон v2.0 |
| `EXAMPLE_PRODUCT_CARD_V1.md` | 5,1 KB | ✅ Заполненный пример v2.0 |
| `EXAMPLE_PRODUCT_CARD.md` | 2,8 KB | ⚠️ Устаревший пример v1.0 — см. раздел «Дублирующиеся документы» |

### 08_KNOWLEDGE_BASE (1/5 запланированных) — частично

| Файл | Размер | Статус |
|------|--------|--------|
| `SOP_PRODUCT_CATALOG.md` | 6,8 KB | ✅ Существует |

### 09_DOCUMENTS (10/10) — все OK, 2 файла не в своей папке

| Файл | Размер | Статус |
|------|--------|--------|
| `SALES_MODEL_RUKODELIE.md` | 10,6 KB | ✅ |
| `PRODUCT_DATABASE_V1_SCHEMA.md` | 27,9 KB | ✅ |
| `DATA_NORMALIZATION_RULES.md` | 25,9 KB | ✅ |
| `PRODUCT_DATABASE_READINESS.md` | 16,6 KB | ✅ |
| `NORMALIZATION_PREVIEW.md` | 15,4 KB | ✅ |
| `CATALOG_ANALYSIS.md` | 15,1 KB | ✅ |
| `CATALOG_IMPORT_REPORT.md` | 9,5 KB | ✅ |
| `SITE_AUDIT_RUKODELIE.md` | 12,3 KB | ✅ |
| `SESSION_SUMMARY_2026-06-07.md` | 9,4 KB | ⚠️ Не в своей папке |
| `SESSION_SUMMARY_2026-06-05.md` | 4,1 KB | ⚠️ Не в своей папке |

---

## 2. Битые ссылки

Всего найдено **20 битых ссылок** на несуществующие файлы.

### Группа A — Документы AI Seller (не созданы, запланированы)

Источник: `01_AI_SELLER/MVP_AI_SELLER_PLAN.md`

| Битая ссылка | Где упоминается |
|-------------|----------------|
| `01_AI_SELLER/SELLER_PERSONA.md` | MVP_AI_SELLER_PLAN.md |
| `01_AI_SELLER/DIALOG_SCENARIOS.md` | MVP_AI_SELLER_PLAN.md |
| `01_AI_SELLER/ORDER_FLOW.md` | MVP_AI_SELLER_PLAN.md |

### Группа B — Документы Telegram Bot (не созданы, запланированы)

Источники: `MVP_AI_SELLER_PLAN.md`, `PROJECT_MEMORY.md`, `SESSION_SUMMARY_2026-06-10.md`

| Битая ссылка | Источники |
|-------------|-----------|
| `03_TELEGRAM/BOT_ARCHITECTURE.md` | MVP_AI_SELLER_PLAN, PROJECT_MEMORY, SESSION_SUMMARY |
| `03_TELEGRAM/SETUP_GUIDE.md` | MVP_AI_SELLER_PLAN, PROJECT_MEMORY, SESSION_SUMMARY |
| `03_TELEGRAM/BOT_COMMANDS.md` | MVP_AI_SELLER_PLAN, PROJECT_MEMORY |
| `03_TELEGRAM/FSM_STATES.md` | MVP_AI_SELLER_PLAN, PROJECT_MEMORY |
| `03_TELEGRAM/KEYBOARDS.md` | MVP_AI_SELLER_PLAN, PROJECT_MEMORY |
| `03_TELEGRAM/NOTIFICATION_TEMPLATES.md` | MVP_AI_SELLER_PLAN, PROJECT_MEMORY |
| `03_TELEGRAM/bot.py` | PROJECT_MEMORY |

### Группа C — Knowledge Base (не созданы, запланированы)

Источник: `01_AI_SELLER/MVP_AI_SELLER_PLAN.md`

| Битая ссылка | Источник |
|-------------|---------|
| `08_KNOWLEDGE_BASE/SELLER_INSTRUCTIONS.md` | MVP_AI_SELLER_PLAN.md |
| `08_KNOWLEDGE_BASE/OBJECTION_HANDLING.md` | MVP_AI_SELLER_PLAN.md |
| `08_KNOWLEDGE_BASE/SALES_RULES.md` | MVP_AI_SELLER_PLAN.md |
| `08_KNOWLEDGE_BASE/PRODUCT_CATEGORIES_GUIDE.md` | MVP_AI_SELLER_PLAN.md |

### Группа D — Прочие (не созданы)

| Битая ссылка | Источник | Приоритет |
|-------------|---------|----------|
| `09_DOCUMENTS/CREDENTIALS.md` | 5 файлов | 🔴 Критичный |
| `.gitignore` | GITHUB_SETUP.md | 🔴 Критичный |
| `09_DOCUMENTS/GOOGLE_SHEETS_LINKS.md` | MVP_AI_SELLER_PLAN.md | 🟡 Средний |
| `10_PROMPTS/SESSION_SUMMARY_TEMPLATE.md` | OBSIDIAN_INTEGRATION.md | 🟢 Низкий |
| `ESCALATION_RULES.md` *(путь не указан)* | MVP_AI_SELLER_PLAN.md | 🟡 Средний |
| `FAQ_RESPONSES.md` *(путь не указан)* | MVP_AI_SELLER_PLAN.md | 🟡 Средний |
| `SEARCH_LOGIC.md` *(путь не указан)* | MVP_AI_SELLER_PLAN.md | 🟡 Средний |

> **Контекст:** большинство битых ссылок сосредоточено в `MVP_AI_SELLER_PLAN.md` — это план будущей разработки. Файлы упоминаются как «будут созданы», а не как уже существующие. Это не ошибка документации, а ожидаемые артефакты будущих этапов.

---

## 3. Отсутствующие документы (ожидаемые, но не созданные)

### Срочные (блокируют работу прямо сейчас)

| Файл | Почему важен |
|------|-------------|
| `.gitignore` | Без него первый `git add .` может загрузить CREDENTIALS на GitHub |
| `09_DOCUMENTS/CREDENTIALS.md` | 5 документов ссылаются на него; токены некуда сохранить |

### Важные (нужны до начала разработки бота)

| Файл | Назначение |
|------|-----------|
| `03_TELEGRAM/BOT_ARCHITECTURE.md` | Архитектура бота перед написанием кода |
| `03_TELEGRAM/SETUP_GUIDE.md` | Инструкция по деплою |
| `03_TELEGRAM/NOTIFICATION_TEMPLATES.md` | Шаблоны сообщений для 7 статусов заказа |
| `08_KNOWLEDGE_BASE/SELLER_INSTRUCTIONS.md` | Правила продаж для Алины (дополняют SYSTEM_PROMPT) |
| `08_KNOWLEDGE_BASE/OBJECTION_HANDLING.md` | Скрипты работы с возражениями |

### Запланированные (создавать по мере разработки)

| Файл | Этап |
|------|-----|
| `01_AI_SELLER/SELLER_PERSONA.md` | Этап 1 — AI Seller |
| `01_AI_SELLER/DIALOG_SCENARIOS.md` | Этап 1 — AI Seller |
| `01_AI_SELLER/ORDER_FLOW.md` | Этап 1 — AI Seller |
| `03_TELEGRAM/BOT_COMMANDS.md` | Этап 2 — Telegram Bot |
| `03_TELEGRAM/FSM_STATES.md` | Этап 2 — Telegram Bot |
| `03_TELEGRAM/KEYBOARDS.md` | Этап 2 — Telegram Bot |
| `08_KNOWLEDGE_BASE/SALES_RULES.md` | Этап 1–2 |
| `08_KNOWLEDGE_BASE/PRODUCT_CATEGORIES_GUIDE.md` | Этап 1–2 |
| `09_DOCUMENTS/GOOGLE_SHEETS_LINKS.md` | Этап 2 — Google Sheets |
| `10_PROMPTS/SESSION_SUMMARY_TEMPLATE.md` | Obsidian-интеграция |

---

## 4. Рекомендуемые документы к созданию

### Приоритет 1 — Перед первым push на GitHub

| Файл | Действие | Кто |
|------|---------|-----|
| `.gitignore` | Создать (шаблон в GITHUB_SETUP.md) | Владелец / AI PM |
| `09_DOCUMENTS/CREDENTIALS.md` | Создать заготовку с полями для токенов | Владелец (заполняет) |

### Приоритет 2 — Перед началом разработки бота

| Файл | Содержимое |
|------|-----------|
| `03_TELEGRAM/BOT_ARCHITECTURE.md` | Схема компонентов, webhook setup, flow входящего сообщения |
| `03_TELEGRAM/NOTIFICATION_TEMPLATES.md` | 7 шаблонов сообщений (new/confirmed/paid/assembling/shipped/delivered/closed) |
| `08_KNOWLEDGE_BASE/SELLER_INSTRUCTIONS.md` | Краткие правила для Алины: что делать, что не делать, граничные случаи |

### Приоритет 3 — Для улучшения навигации

| Файл | Содержимое |
|------|-----------|
| `10_PROMPTS/SESSION_SUMMARY_TEMPLATE.md` | Шаблон для быстрого заполнения итогов сессии |
| `01_AI_SELLER/SELLER_PERSONA.md` | Компактная карточка персоны Алины (имя, стиль, ограничения) |

---

## 5. Пустые папки

| Папка | Статус | Комментарий |
|-------|--------|------------|
| `03_TELEGRAM/` | 🔴 Пустая | Следующий этап разработки — будет заполнена в ближайшее время |
| `10_PROMPTS/` | 🟡 Пустая | Нужен минимум SESSION_SUMMARY_TEMPLATE.md |
| `99_ARCHIVE/` | 🟢 Пустая | Норма — архив пока не нужен |
| `04_SEO_AGENT/` | 🟢 Пустая | Второй этап, не критично |
| `05_MARKETING_AGENT/` | 🟢 Пустая | Второй этап |
| `06_ANALYTICS_AGENT/` | 🟢 Пустая | Второй этап |
| `07_VIDEO_AGENT/` | 🟢 Пустая | Второй этап |

---

## 6. Дублирующиеся документы

### Пара: EXAMPLE_PRODUCT_CARD (два файла — разные версии)

| Файл | Версия | Дата | Размер | Поля |
|------|--------|------|--------|------|
| `EXAMPLE_PRODUCT_CARD.md` | v1.0 | 2026-06-05 | 2,8 KB | 12 |
| `EXAMPLE_PRODUCT_CARD_V1.md` | v2.0 | 2026-06-07 | 5,1 KB | 30 |

**Вердикт:** `EXAMPLE_PRODUCT_CARD.md` (v1.0) — устаревший, создан до нормализации каталога. `EXAMPLE_PRODUCT_CARD_V1.md` — актуальный. Старый файл следует переместить в `99_ARCHIVE/`.

> **Рекомендация:** переименовать `EXAMPLE_PRODUCT_CARD_V1.md` → `EXAMPLE_PRODUCT_CARD.md`, старый перенести в `99_ARCHIVE/EXAMPLE_PRODUCT_CARD_v1.0_legacy.md`. Действие требует подтверждения владельца.

---

## 7. Файлы не в своей папке

### SESSION_SUMMARY — неправильное расположение

| Файл | Текущая папка | Правильная папка |
|------|--------------|-----------------|
| `SESSION_SUMMARY_2026-06-05.md` | `09_DOCUMENTS/` | `00_PROJECT_MANAGER/` |
| `SESSION_SUMMARY_2026-06-07.md` | `09_DOCUMENTS/` | `00_PROJECT_MANAGER/` |
| `SESSION_SUMMARY_2026-06-10.md` | `00_PROJECT_MANAGER/` | ✅ Корректно |

**Контекст:** первые две сессии (05 и 07 июня) создавались до того, как было принято решение хранить SESSION_SUMMARY в `00_PROJECT_MANAGER/`. Файл сессии 10 июня уже создан правильно. Перемещение требует подтверждения владельца.

---

## 8. Несоответствие в именовании файлов

### Регистр: CREDENTIALS vs credentials

| Вариант | Где упоминается |
|---------|----------------|
| `09_DOCUMENTS/CREDENTIALS.md` (заглавные) | GITHUB_SETUP.md, START_HERE.md, SESSION_SUMMARY_2026-06-10.md, PROJECT_MEMORY.md, MVP_AI_SELLER_PLAN.md |
| `09_DOCUMENTS/credentials.md` (строчные) | TASKS.md, SESSION_SUMMARY_2026-06-05.md |

**Вердикт:** правильный вариант — `CREDENTIALS.md` (в соответствии с соглашением ALL_CAPS для всех документов проекта). TASKS.md и SESSION_SUMMARY_2026-06-05.md содержат устаревшие ссылки строчными буквами.

### Путь без папки: три файла в MVP_AI_SELLER_PLAN.md

| Упомянутый файл | Ожидаемое правильное расположение |
|----------------|----------------------------------|
| `ESCALATION_RULES.md` | `08_KNOWLEDGE_BASE/ESCALATION_RULES.md` |
| `FAQ_RESPONSES.md` | `08_KNOWLEDGE_BASE/FAQ_RESPONSES.md` |
| `SEARCH_LOGIC.md` | `01_AI_SELLER/SEARCH_LOGIC.md` |

---

## Сводный чеклист проблем

```
КРИТИЧНЫЕ (сделать до первого git push):
[ ] Создать .gitignore
[ ] Создать 09_DOCUMENTS/CREDENTIALS.md (заготовку)

ВАЖНЫЕ (сделать до начала разработки бота):
[ ] Создать 03_TELEGRAM/BOT_ARCHITECTURE.md
[ ] Создать 03_TELEGRAM/NOTIFICATION_TEMPLATES.md
[ ] Создать 08_KNOWLEDGE_BASE/SELLER_INSTRUCTIONS.md

РЕКОМЕНДУЕМЫЕ (навигация и порядок):
[ ] Переместить SESSION_SUMMARY_2026-06-05 и -06-07 в 00_PROJECT_MANAGER/
[ ] Переместить EXAMPLE_PRODUCT_CARD.md (v1.0) в 99_ARCHIVE/
[ ] Исправить lowercase "credentials.md" в TASKS.md и SESSION_SUMMARY_2026-06-05.md
[ ] Создать 10_PROMPTS/SESSION_SUMMARY_TEMPLATE.md

НИЗКИЙ ПРИОРИТЕТ:
[ ] Уточнить пути к ESCALATION_RULES, FAQ_RESPONSES, SEARCH_LOGIC в MVP_AI_SELLER_PLAN.md
[ ] Создать 01_AI_SELLER/SELLER_PERSONA.md
```

---

## Статистика аудита

| Показатель | Значение |
|-----------|---------|
| Всего файлов проверено | 29 |
| Из них .md | 27 |
| Из них .csv | 2 |
| Папок всего | 12 |
| Папок пустых | 7 |
| Файлов OK (ссылки верны) | 22 |
| Файлов с битыми ссылками | 5 (MVP_AI_SELLER_PLAN, PROJECT_MEMORY, OBSIDIAN_INTEGRATION, TASKS, SESSION_SUMMARY_2026-06-05) |
| Всего битых ссылок | 20 |
| — из них плановые (будущие этапы) | 15 |
| — из них требуют немедленного создания | 2 (.gitignore, CREDENTIALS.md) |
| Файлов не в своей папке | 2 |
| Дублирующихся файлов | 1 пара |
| Расхождений в именовании | 1 |

---

*Аудит завершён: 2026-06-10 | Следующий аудит рекомендуется после завершения разработки Telegram Bot (ориентировочно 14–16 июня 2026)*
