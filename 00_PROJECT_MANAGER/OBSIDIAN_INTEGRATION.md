# OBSIDIAN INTEGRATION
> Инструкция по настройке папки RUKODELIE_AI_FACTORY как Obsidian Vault.

---

## Что такое Obsidian Vault

Obsidian — редактор заметок в формате Markdown, работающий с локальными файлами.  
**Vault** = папка с `.md` файлами. Никакой синхронизации через серверы Obsidian — все файлы хранятся у тебя (iCloud / локально).

---

## Единственное ручное действие

```
Obsidian → Open folder as vault → выбрать:
/Users/sergey/Library/Mobile Documents/com~apple~CloudDocs/RUKODELIE_AI_FACTORY
```

> После этого Obsidian создаст папку `.obsidian/` внутри RUKODELIE_AI_FACTORY — это нормально.  
> `.obsidian/` содержит настройки, темы, плагины конкретно для этого vault.  
> Не удалять, не переносить.

---

## Что произойдёт автоматически

| Действие | Результат |
|---------|----------|
| Открыть папку как Vault | `.obsidian/` создаётся автоматически |
| Obsidian индексирует `.md` файлы | Все 20+ файлов появятся в левой панели |
| Graph View (Ctrl+G) | Граф связей между файлами |
| Quick Switcher (Ctrl+O) | Быстрый поиск по имени файла |
| Search (Ctrl+F / Ctrl+Shift+F) | Поиск по тексту во всём vault |

---

## Рекомендуемая начальная настройка

### Шаг 1 — Установить стартовую страницу

```
Settings → Options → Editor → Default new note location
Settings → Options → General → Start-up → Default file to open
```

Указать: `00_PROJECT_MANAGER/START_HERE.md`

### Шаг 2 — Включить плагины (Core plugins)

Убедиться, что включены:
- **Backlinks** — видеть, какие файлы ссылаются на текущий
- **Graph view** — граф связей
- **Quick switcher** — быстрый поиск (Ctrl+O)
- **Search** — поиск по vault
- **Templates** — для будущих шаблонов (папка `10_PROMPTS/`)
- **Starred / Bookmarks** — закладки для быстрого доступа

### Шаг 3 — Добавить в Bookmarks (Starred)

Добавить звёздочку или закладку на:
1. `00_PROJECT_MANAGER/START_HERE.md` ← стартовая точка
2. `00_PROJECT_MANAGER/PROJECT_MEMORY.md` ← главная память
3. `01_AI_SELLER/SYSTEM_PROMPT.md` ← ядро проекта
4. `02_PRODUCT_DATABASE/catalog_v1.csv` ← каталог
5. `TASKS.md` ← текущие задачи

### Шаг 4 — Настроить Excluded Files (опционально)

Если хочешь скрыть из списка:
```
Settings → Files and links → Excluded files
```
Добавить: `.claude/` (папка с настройками Claude Code — не нужна в Obsidian)

---

## Рекомендуемые Community Plugins

> Community Plugins → Browse → установить:

| Плагин | Зачем |
|--------|-------|
| **Dataview** | Динамические таблицы из метаданных файлов (например, список задач из TASKS.md) |
| **Calendar** | Навигация по SESSION_SUMMARY файлам по дате |
| **Advanced Tables** | Удобное редактирование markdown-таблиц |
| **CSV Viewer** | Просмотр `catalog_v1.csv` прямо в Obsidian |

> Для активации: Settings → Community plugins → Turn on community plugins → Browse

---

## Как работают wiki-ссылки

В Obsidian `[[filename]]` создаёт кликабельную ссылку на файл.  
В этом проекте ссылки написаны в формате путей (для совместимости с AI-агентами):

```markdown
`01_AI_SELLER/SYSTEM_PROMPT.md`   ← путь (работает везде)
[[SYSTEM_PROMPT]]                  ← wiki-link (только в Obsidian)
```

Оба формата корректны. При редактировании в Obsidian можно использовать `[[]]` для внутренних ссылок.

---

## Структура файлов в Obsidian (File Explorer)

```
RUKODELIE_AI_FACTORY/
├── .obsidian/              ← создаётся Obsidian автоматически
├── MASTER_PLAN.md
├── VISION.md
├── ROADMAP.md
├── TASKS.md
│
├── 00_PROJECT_MANAGER/
│   ├── START_HERE.md       ← 📌 Стартовая страница
│   ├── PROJECT_MEMORY.md   ← 📌 Главная память
│   ├── PROJECT_MEMORY_INDEX.md
│   ├── OBSIDIAN_INTEGRATION.md  ← Этот файл
│   └── SESSION_SUMMARY_*.md
│
├── 01_AI_SELLER/
│   ├── SYSTEM_PROMPT.md    ← 📌 Ядро MVP
│   ├── AI_SELLER_REQUIREMENTS.md
│   └── MVP_AI_SELLER_PLAN.md
│
├── 02_PRODUCT_DATABASE/
│   ├── catalog_v1.csv
│   └── ...
│
├── 08_KNOWLEDGE_BASE/
├── 09_DOCUMENTS/
├── 10_PROMPTS/             ← Templates folder для Obsidian
└── 99_ARCHIVE/
```

---

## Что Obsidian видит и не видит

| Тип | Видимость | Примечание |
|-----|----------|-----------|
| `.md` файлы | ✅ Полностью | Рендеринг markdown |
| `.csv` файлы | ✅ Как текст / CSV Viewer | catalog_v1.csv |
| `.obsidian/` папка | ✅ В File Explorer | Нормально, не трогать |
| `.claude/` папка | ✅ В File Explorer | Можно скрыть в Excluded Files |
| Wiki-ссылки `[[]]` | ✅ Кликабельны | Obsidian строит граф |

---

## Graph View — граф связей

После открытия vault нажать `Ctrl+G` (или `Cmd+G` на Mac).

Ожидаемый граф:
- Центральные узлы: `PROJECT_MEMORY.md`, `START_HERE.md`, `SYSTEM_PROMPT.md`
- Связанные: `MASTER_PLAN.md`, `ROADMAP.md`, `SESSION_SUMMARY_*.md`
- Изолированные: аналитические файлы из `09_DOCUMENTS/`

---

## Шаблон для новых SESSION_SUMMARY (через Obsidian Templates)

Настройка:
```
Settings → Core plugins → Templates → Template folder: 10_PROMPTS
```

Создать файл `10_PROMPTS/SESSION_SUMMARY_TEMPLATE.md` с шаблоном сессии.  
Использование: новый файл → Ctrl+T → выбрать шаблон → заполнить.

---

## Важные правила при работе в Obsidian

1. **Не переименовывать папки** — AI-агенты используют точные пути.
2. **Не перемещать файлы** без обновления ссылок (Obsidian предложит обновить автоматически).
3. **SESSION_SUMMARY сохранять** в `00_PROJECT_MANAGER/`, не в `09_DOCUMENTS/`.
4. **catalog_v1.csv редактировать** в Excel/Sheets или специализированном редакторе, не в Obsidian.
5. **`.obsidian/` папку** не добавлять в git (если будет использоваться git).

---

## Итого: что нужно сделать один раз

```
✅ 1. Obsidian → Open folder as vault → выбрать RUKODELIE_AI_FACTORY
✅ 2. Settings → Default file → 00_PROJECT_MANAGER/START_HERE.md
✅ 3. Добавить 5 файлов в Bookmarks (звёздочки)
✅ 4. (Опционально) Установить: Dataview, CSV Viewer, Advanced Tables
✅ 5. (Опционально) Скрыть .claude/ в Excluded Files
```

**Готово. Vault настроен.**

---

*Файл создан: 2026-06-10 | Версия: 1.0*
