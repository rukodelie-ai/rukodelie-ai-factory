# CURRENT ITERATION

## Current Status

E1 Release завершён со статусом COMPLETE / PASS и зафиксирован в `origin/main`; E2 не начат.

## Last Accepted Decisions

- RAW COMPLETE v1 считается окончательно утверждённым.
- Контракт RAW COMPLETE v1 изменению не подлежит без нового подтверждённого critical defect.
- Все найденные ошибки после утверждения контракта трактуются как ошибки реализации extractor/validator/loader, а не архитектуры.
- Первая тестовая загрузка в Google Sheets считается эталонной проверкой цепочки ETL.
- E1 snapshot с cutoff `2026-07-18T17:49:40Z` принят как завершённый REQUIRED core Phase 1.
- Следующим этапом остаётся только E2 — Phase 2 для JUSTIFIED_OPTIONAL sources по утверждённому import plan.
- Четыре подготовленных commit успешно отправлены в `origin/main`; безопасный E1 commit: `fa5557c5147b00c828f06c486762686d157d6635`.
- Проверенный локальный ZIP с подтверждённым SHA-256 считается достаточной резервной копией E1 Release.
- Google Drive backup и XLSX backup не выполнены из-за внешних ограничений Google и не блокируют завершение E1.

## Known Risks

- Snapshot validation зависит от неизменности данных 1С между двумя выгрузками.
- Изменение цен или остатков между snapshot может изменить checksum.
- Повторная проверка идемпотентности должна выполняться на одном и том же cutoff.
- Полный read-back может достигать минутной квоты Google Sheets API; E1 loader использует pacing, bounded timeout и ожидание quota reset при HTTP 429.

## Success Criteria

E2 считается завершённым только при одновременном выполнении критериев утверждённого import plan:

- PHASE 2 blockers закрыты;
- JUSTIFIED_OPTIONAL sources загружены малыми batches;
- Ozon complete traversal подтверждён;
- optional misses явно зафиксированы;
- affected optional partitions прошли validation и read-back;
- завершённый Phase 1 snapshot остаётся валидным и неизменным вне утверждённых optional partitions.

## Last Completed Step

E1 Release завершён с COMPLETE / PASS: четыре подготовленных commit отправлены в `origin/main`, последний отправленный commit — `fa5557c5147b00c828f06c486762686d157d6635`.

## Current Blockers

NONE

## Current Working Branch

E1 Release закрыт; E2 не начат и ожидает отдельной команды владельца проекта.

## Next Single Step

Ожидать отдельную команду владельца проекта на начало E2.

## Strictly Do NOT

- не пересматривать архитектуру;
- не менять утверждённый контракт RAW COMPLETE v1;
- не выполнять повторные широкие исследования OData и 1С;
- не менять CURRENT RAW;
- не менять старую Product Knowledge;
- не изменять AI Seller;
- не изменять завершённый E1 snapshot вне утверждённых optional partitions;
- не начинать E2 без отдельного указания владельца;
- не изменять 1С, кроме разрешённых read-only операций;
- не выполнять git commit и git push без отдельного указания.

## Context For Next Session

Native Google Sheets RAW COMPLETE подключена только через `RAW_COMPLETE_SPREADSHEET_ID`.
E1 snapshot: `e1_yarn_204_9114_20260718T174940Z`; cutoff `2026-07-18T17:49:40Z`.
Полный scope подтверждён: 204 товара и 9 114 вариантов.
Live-схема сохранена: 32 листа, 466 полей, точный порядок колонок.
DRY RUN: PASS 171/171; PK duplicates 0; FK failures 0; invalid GUID 0.
Google Sheets full load и read-back validation: PASS.
Canonical checksum: `7f62edbaeab9e5d495c41b341c21b6b81c15c04fe0dea5af9b4ed934cb861c57`.
Same-snapshot idempotency: PASS; новых строк 0; checksum не изменился.
`RAW_CURRENT_PRICES`: 62 878 строк; `RAW_CURRENT_STOCK`: 72 912 строк.
Atomic commit всех 32 листов и failure/rollback test: PASS.
Leading zeros, NULL, GUID, headers и column order сохранены.
Артефакты E1 находятся в `09_DOCUMENTS/RAW_COMPLETE_V1_CONTRACT/E1_PHASE_1_FULL/yarn_204_9114`.
Полный E1 dataset сохранён локально и отсутствует в Git.
Безопасный E1 commit `fa5557c5147b00c828f06c486762686d157d6635` отправлен в `origin/main` вместе с тремя ранее подготовленными commit.
Локальный архив E1 проверен; SHA-256: `f31d9276baef169f84b228cd79954bb4a7927c753573df3466c2ff6bebd1b154`.
Google Drive backup не выполнен из-за внешнего ограничения Drive storage quota.
XLSX backup не выполнен из-за ограничения Google по размеру экспорта.
Оба ограничения не блокируют завершение E1 Release.
Source exclusions честно сохранены в `source_exclusions.json`.
CURRENT RAW, старая Product Knowledge, AI Seller, 1С и контракт не изменялись.
1С использовалась только read-only; Base64/binary payload в Google Sheets не записывался.
E2 не начат и может быть начат только отдельной командой владельца проекта.

## Files Changed Today

- `09_DOCUMENTS/CURRENT_ITERATION.md` — зафиксировано официальное закрытие E1 Release.

## Expected Result Of Next Session

Следующая сессия начнёт E2 только после отдельной команды владельца проекта.

## Session Bootstrap

При открытии новой сессии сначала полностью прочитать CURRENT_ITERATION.md.

Считать его единственным источником оперативного состояния проекта.

Не возвращаться к архитектурным исследованиям, если они не указаны в этом документе.
