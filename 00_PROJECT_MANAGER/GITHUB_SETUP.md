# GITHUB SETUP — RUKODELIE AI FACTORY
> Инструкция по подключению проекта к GitHub. Версия 1.0, 2026-06-10.

---

## Стратегия веток

```
main
├── dev
│   ├── feature/telegram-bot
│   ├── feature/google-sheets
│   ├── feature/ai-seller-v2
│   └── feature/catalog-publish
└── hotfix/*
```

| Ветка | Назначение | Кто пушит | Условие мержа |
|-------|-----------|-----------|--------------|
| `main` | Стабильная версия. Всё, что здесь — работает | PM | Только через PR из `dev` |
| `dev` | Активная разработка | PM | Merge в `main` после тестирования |
| `feature/*` | Одна фича / один компонент | PM | Merge в `dev` после готовности |
| `hotfix/*` | Срочные исправления production | PM | Merge сразу в `main` + `dev` |

**Правило:** `main` никогда не ломается. Весь код пишется в `feature/` → сливается в `dev` → в `main`.

---

## Что НЕ попадает в GitHub

> **Критически важно.** Эти файлы/папки должны быть в `.gitignore`.

| Что | Почему |
|-----|-------|
| `09_DOCUMENTS/CREDENTIALS.md` | Telegram Bot токен + Claude API ключ — никогда в публичный доступ |
| `.obsidian/` | Личные настройки Obsidian, не нужны в репозитории |
| `.claude/` | Настройки Claude Code, не часть проекта |
| `.DS_Store` | macOS системные файлы |
| `__pycache__/` | Python кэш (появится при разработке бота) |
| `*.env` | Файлы переменных окружения |
| `venv/`, `.venv/` | Python виртуальное окружение |

---

## Часть 1 — Создание Private Repository на GitHub

### Через браузер (5 минут)

```
1. Открыть: github.com → Sign in (или создать аккаунт)

2. Нажать: + → New repository

3. Заполнить:
   Repository name:  rukodelie-ai-factory
   Description:      Multi-agent AI system for Rukodelie.kz craft store
   Visibility:       ● Private  (не Public!)
   
   Initialize:       НЕ ставить галочки (README, .gitignore, license)
   — потому что локальная папка уже существует

4. Нажать: Create repository

5. Скопировать ссылку формата:
   https://github.com/YOUR_USERNAME/rukodelie-ai-factory.git
```

---

## Часть 2 — Подготовка локальной папки

### Шаг 2.1 — Создать .gitignore

Создать файл `.gitignore` в корне проекта (`RUKODELIE_AI_FACTORY/.gitignore`):

```gitignore
# Credentials — NEVER commit
09_DOCUMENTS/CREDENTIALS.md

# Obsidian personal settings
.obsidian/

# Claude Code settings
.claude/

# macOS
.DS_Store
**/.DS_Store

# Python (для будущего Telegram Bot)
__pycache__/
*.py[cod]
*.pyo
venv/
.venv/
*.env
.env.*

# Logs
*.log
logs/
```

### Шаг 2.2 — Открыть Terminal

```bash
# Перейти в папку проекта
cd "/Users/sergey/Library/Mobile Documents/com~apple~CloudDocs/RUKODELIE_AI_FACTORY"
```

---

## Часть 3 — Инициализация git

```bash
# 1. Инициализировать репозиторий
git init

# 2. Настроить имя и email (один раз на компьютере)
git config user.name "Sergey"
git config user.email "3295454@gmail.com"

# 3. Переименовать ветку по умолчанию в main
git branch -M main
```

---

## Часть 4 — Первый commit

```bash
# 1. Проверить, что будет добавлено (важно!)
git status

# 2. Добавить все файлы в staging
git add .

# 3. Убедиться, что CREDENTIALS.md НЕ в списке
git status
# Должны быть только .md и .csv файлы

# 4. Создать первый коммит
git commit -m "feat: initial project structure — RUKODELIE AI FACTORY

- Strategic docs: MASTER_PLAN, VISION, ROADMAP, TASKS
- AI Seller: SYSTEM_PROMPT v1.1, requirements, MVP plan
- Product Database: catalog_v1.csv (50 products, 30 fields)
- Knowledge Base, Documents, Project Manager docs
- Obsidian vault integration"
```

---

## Часть 5 — Подключение к GitHub и первый push

```bash
# 1. Добавить remote (вставить свою ссылку из шага 1.5)
git remote add origin https://github.com/YOUR_USERNAME/rukodelie-ai-factory.git

# 2. Проверить, что remote добавлен
git remote -v

# 3. Пушнуть в main
git push -u origin main
```

При первом push GitHub попросит авторизацию:
- Браузер откроется автоматически → авторизовать GitHub
- Или использовать Personal Access Token (PAT): github.com → Settings → Developer settings → Personal access tokens

---

## Часть 6 — Создать ветку dev

```bash
# Создать и перейти на dev
git checkout -b dev

# Пушнуть dev в GitHub
git push -u origin dev

# Вернуться на main
git checkout main
```

После этого в GitHub будут две ветки: `main` и `dev`.  
Вся разработка начинается с `dev`.

---

## Часть 7 — Стратегия резервирования

### Три уровня защиты

```
Уровень 1: iCloud Drive (автоматически)
    ↓ всегда синхронизируется с iCloud
    
Уровень 2: GitHub Private Repository
    ↓ push вручную или по расписанию
    
Уровень 3: GitHub Releases (версионные теги)
    ↓ при крупных milestone: v1.0, v1.1, v2.0
```

### Когда делать push

| Ситуация | Ветка | Команда |
|---------|-------|---------|
| Обновил документацию | `main` | `git add . && git commit -m "docs: ..." && git push` |
| Начал новую фичу | `feature/...` | `git checkout -b feature/telegram-bot` |
| Фича готова | `dev` → `main` | PR на GitHub или `git merge` |
| Выпустил MVP | `main` | `git tag v1.0.0 && git push --tags` |

### Минимальный режим (для документов)

Пока нет кода — коммитить прямо в `main`:

```bash
# После каждой рабочей сессии
git add .
git commit -m "docs: session 2026-06-10 — system prompt v1.1, obsidian setup"
git push
```

### Рекомендуемый ритм push

- **Ежедневно** (если была работа над проектом): `git push origin main`
- **После каждого крупного файла**: создать коммит с понятным сообщением
- **Перед переходом к новому этапу**: создать тег версии

---

## Структура веток для текущих этапов

```
Этап 1 (сейчас): Документация
    main ← коммиты документов напрямую

Этап 2 (следующий): Разработка MVP
    dev → feature/google-sheets     ← интеграция Google Sheets
        → feature/telegram-bot      ← код бота (Python)
        → feature/ai-seller-core    ← Claude API интеграция
    main ← только протестированный код

Этап 3: Production
    main   ← production
    dev    ← разработка
    hotfix ← срочные фиксы
```

---

## Соглашение о коммит-сообщениях

```
feat:     новая функциональность
docs:     изменения документации
fix:      исправление ошибки
refactor: рефакторинг без изменения функций
test:     добавление тестов
chore:    обновление зависимостей, конфигурация

Примеры:
  docs: add SYSTEM_PROMPT v1.1 with EN language support
  feat: telegram bot basic webhook setup
  fix: catalog csv encoding issue
  docs: session summary 2026-06-10
```

---

## Проверочный список (чеклист)

```
Перед первым push:
[ ] .gitignore создан и содержит CREDENTIALS.md
[ ] git status не показывает CREDENTIALS.md в списке файлов
[ ] Repository создан как Private (не Public)
[ ] Remote добавлен: git remote -v показывает origin

После первого push:
[ ] github.com/YOUR_USERNAME/rukodelie-ai-factory открывается
[ ] Видны все .md файлы и catalog_v1.csv
[ ] CREDENTIALS.md НЕ виден (не загружен)
[ ] Ветка dev создана
```

---

## Команды быстрого доступа (шпаргалка)

```bash
# Статус изменений
git status

# Добавить все изменения
git add .

# Коммит
git commit -m "docs: что сделал"

# Push текущей ветки
git push

# Посмотреть историю
git log --oneline -10

# Посмотреть ветки
git branch -a

# Создать feature ветку
git checkout -b feature/название

# Переключиться на dev
git checkout dev

# Слить feature в dev
git checkout dev && git merge feature/название

# Создать тег версии
git tag v1.0.0 && git push --tags
```

---

## Безопасность

| Правило | Детали |
|---------|--------|
| Repository = Private | Никогда не менять на Public |
| CREDENTIALS.md в .gitignore | Проверять git status перед каждым push |
| Токены = в переменных окружения | Telegram токен и API ключ → `.env` файл (тоже в .gitignore) |
| Не пушить в main напрямую | Когда появится код — только через PR из dev |

> **Правило одного**: если CREDENTIALS.md случайно попал в коммит — это не исправляется через `git rm`. Нужно отозвать все токены и выпустить новые. Именно поэтому .gitignore настраивается ДО первого `git add`.

---

*Создан: 2026-06-10 | Версия: 1.0 | Обновить при смене GitHub аккаунта или стратегии веток*
