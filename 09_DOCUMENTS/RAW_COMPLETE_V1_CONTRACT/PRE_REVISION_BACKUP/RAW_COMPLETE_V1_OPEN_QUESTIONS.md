# RAW COMPLETE v1 — открытые вопросы

## Неблокирующие, но обязательные к фиксации в первом extraction report

1. **Ozon final count.** Получено 2 408 mappings минимум для 124 товаров, но большие URL дали IIS 404.15. Решение v1: малые batches; expected остаётся динамическим до полного успешного прохода.
2. **Variant attached-file count.** Есть 6 170 непустых image_Key, но полный EntitySet файлов не выгружен. Нельзя считать 6 170 окончательным числом файлов до dedup/entity validation.
3. **Palette count.** Metadata подтверждает поля Ref_Key, Description, Сортировка, Hex, Red, Green, Blue и DeletionMark. Наблюдалось 20 palette references; точное число уникальных referenced palette rows проверяется в test phase.
4. **Price snapshot row count.** Верхняя граница 91 140; фактическое число непустых комбинаций фиксирует первый полный run.
5. **File roles.** Основной product image определяется только прямым ФайлКартинки_Key. Роль остальных 445 файлов не угадывается и остаётся null/raw.
6. **Language.** Язык descriptions не опубликован отдельным реквизитом. v1 использует technical value und, а не AI-определение языка.
7. **Marketplace categories.** Kaspi/Ozon IDs сохраняются в собственных namespaces. Полный category path не строится без подтверждённого справочника.
8. **Package items.** Для единственного referenced package set найдено 0 child rows. Пустой лист сохраняется для доказательства, но значения не фабрикуются.
9. **Binary metadata coverage.** Механизм прямого составного ключа подтверждён; массовое чтение binary не является обязательным для RAW COMPLETE. Hash остаётся nullable.

## Полный реестр UNCONFIRMED_SOURCE

Эти nullable-поля существуют в контракте только как безопасные места для будущего подтверждения. В v1 они должны оставаться null, если точный реквизит не найден:

- RAW_CLASSIFICATIONS.full_path_raw;
- RAW_PRODUCT_CLASSIFICATIONS.is_primary_raw;
- RAW_PRICE_TYPES.currency_id_raw;
- RAW_PRODUCT_FILES.file_role_raw;
- RAW_VARIANT_FILES.file_role_raw;
- RAW_DESCRIPTIONS.language_code и active_status_raw;
- RAW_ATTRIBUTE_DEFINITIONS.unit_raw;
- RAW_ATTRIBUTE_VALUES.value_type_raw;
- RAW_MARKETPLACE_CONTENT.language_code;
- RAW_MARKETPLACE_IMAGES.image_reference_raw;
- RAW_PRODUCT_RELATIONS.source_variant_id, target_variant_id и relation_value_raw.

Technical value und для language_code допустим только как явно маркированное техническое значение и не считается исходным языком 1С.

## Решения, уже закрытые контрактом

- Отдельный country dictionary не создаётся без FK.
- Full movement/price history не загружается в Google Sheets; snapshots документированы.
- ABC/XYZ и segments исключены из Product Knowledge v1.
- Halyk/Beru/Wildberries не объявляются существующими sources.
- Base64 и бинарные файлы запрещены в таблице.
- Все вопросы выше не разрешают менять CURRENT RAW или подключать AI Seller.

## Блокирующие вопросы перед реализацией

Только один: владелец должен принять или отклонить этот контракт и имя новой таблицы. Технические counts выше закрываются механической test/full extraction и не требуют нового архитектурного решения.
