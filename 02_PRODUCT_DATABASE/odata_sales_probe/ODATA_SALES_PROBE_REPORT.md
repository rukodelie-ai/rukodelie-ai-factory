# ODATA SALES PROBE REPORT
**Дата:** 2026-07-01
**Хост:** `1c.rukodelie.kz:9780`
**Кандидатов найдено:** 1077 (330 приоритетных + 747 вспомогательных)

---

## 1. Можно ли через OData получить продажи?

✅ Да — сущности с датой, номенклатурой и количеством найдены.

---

## 2. Наиболее вероятные сущности продаж (приоритетные)

- `Document_Halyk_ЗаказыКлиентов` [DATE, NOM, QTY, SUM, CLIENT, CHANNEL, DOCREF]
- `Catalog_Halyk_Профили` [DATE, NOM, SUM, CLIENT, CHANNEL, DOCREF]
- `Catalog_Kaspi_Профили` [DATE, NOM, SUM, CLIENT, CHANNEL, DOCREF]
- `Document_Kaspi_ЗаказыКлиентов` [DATE, NOM, QTY, CLIENT, CHANNEL, DOCREF]
- `Document_РеализацияТоваровУслуг` [DATE, NOM, SUM, CLIENT, CHANNEL, DOCREF]
- `Catalog_Halyk_КарточкаТовара` [DATE, NOM, QTY, SUM, DOCREF]
- `Catalog_Kaspi_КарточкаТовара` [DATE, NOM, QTY, SUM, DOCREF]
- `Catalog_Ozon_Аккаунты` [DATE, NOM, CLIENT, CHANNEL, DOCREF]
- `Document_ВводОстатков_ОптовыеПродажи` [DATE, NOM, QTY, SUM, DOCREF]
- `Document_ВводОстатков_РозничныеПродажи` [DATE, NOM, QTY, SUM, DOCREF]

---

## 3. Где строки продаж / состав заказа?

Искать в сущностях с суффиксом `_Товары`, `_ТоварыУслуги`, `_ТабличнаяЧасть`
или в `AccumulationRegister_*` с полем Номенклатура.

- `Catalog_Номенклатура`
- `Document_ЗаказКлиента`
- `Catalog_ВидыНоменклатуры`
- `Document_ЗаявкаНаВозвратТоваровОтКлиента`
- `Document_РеализацияТоваровУслуг`

---

## 4–8. Где ключевые поля?

| Поле | Есть? | Топ-сущности |
|------|-------|-------------|
| Дата продажи | ✅ | `Document_ЗаказКлиента`, `Document_ЗаявкаНаВозвратТоваровОтКлиента`, `Document_РеализацияТоваровУслуг` |
| Номенклатура | ✅ | `Catalog_Номенклатура`, `Document_ЗаказКлиента`, `Catalog_ВидыНоменклатуры` |
| Количество | ✅ | `Catalog_Номенклатура`, `Catalog_ВидыНоменклатуры`, `Document_Halyk_ЗаказыКлиентов` |
| Сумма | ✅ | `Document_ЗаказКлиента`, `Document_ЗаявкаНаВозвратТоваровОтКлиента`, `Document_РеализацияТоваровУслуг` |
| Клиент/Контрагент | ✅ | `Catalog_Номенклатура`, `Document_ЗаказКлиента`, `Catalog_ВидыНоменклатуры` |

---

## 9. Разделение по каналам продаж

### Kaspi.kz (61 сущностей)
- `Catalog_Kaspi_Профили`
- `Document_Kaspi_ЗаказыКлиентов`
- `Catalog_Kaspi_КарточкаТовара`
- `Catalog_Kaspi_Отзывы`
- `Document_Kaspi_ПоставкаТоваров`
- `Document_Kaspi_ВозвратТоваровПриДоставке`
- `Document_Kaspi_ДетальнаяИнформацияПоОперациям`
- `Document_Kaspi_ДетальнаяИнформацияПоОперациям_Операции`
- `Document_Kaspi_ДетальнаяИнформацияПоОперациям_ПлатежиПериоды`
- `Document_Kaspi_ДетальнаяИнформацияПоОперациям_ПлатежиРасшифровка`
- `ExchangePlan_Kaspi_ПланОбмена`
- `Document_Kaspi_ПоставкаТоваров_ЗаказыКлиентов`
- `Catalog_Kaspi_ТочкиПродаж`
- `Document_Kaspi_ВозвратТоваровПриДоставке_ЗаказыКлиентов`
- `Document_Kaspi_ВыгрузкаТоваровВМагазин`
- `Document_Kaspi_ДетальнаяИнформацияПоОперациям_Платежи`
- `Document_Kaspi_ДетальнаяИнформацияПоОперациям_ПлатежиКомпенсацииДоставки`
- `InformationRegister_Kaspi_ЖурналСобытий`
- `InformationRegister_Kaspi_ИсторияЗаказовКлиентов`
- `Catalog_Kaspi_Категории`
- `Catalog_Kaspi_СлужбыДоставки`
- `Document_Kaspi_ВыгрузкаТоваровВМагазин_КарточкиТоваров`
- `Document_Kaspi_ВыгрузкаТоваровВМагазин_Ошибки`
- `Document_Kaspi_ДетальнаяИнформацияПоОперациям_Реализации`
- `Document_Kaspi_ДетальнаяИнформацияПоОперациям_РеализацииКомпенсацииДоставки`
- `Document_Kaspi_ЗаказыКлиентов_Товары`
- `Document_Kaspi_ЗаявкиНаПродлениеПодписки`
- `ExchangePlan_Kaspi_ПланОбмена_СписокНоменклатуры`
- `InformationRegister_Kaspi_ТоварыПоПредзаказуНаСкладах`
- `InformationRegister_Kaspi_ИсторияВыгрузкиДокументов`
- `InformationRegister_Kaspi_ИсторияСинхронизаций`
- `InformationRegister_Kaspi_ИсторияТоваров`
- `InformationRegister_Kaspi_СтоимостьДоставкиПоКатегориямТоваров`
- `InformationRegister_Kaspi_РеализацияТоваровПоТочкамПродаж`
- `Catalog_Kaspi_КарточкаТовара_images`
- `Catalog_Kaspi_КарточкаТовара_errors`
- `Catalog_Kaspi_КарточкаТовара_Предзаказ`
- `InformationRegister_Kaspi_НастройкиИнтеграции`
- `Catalog_Kaspi_Отзывы_galleryImages`
- `Catalog_Kaspi_ПользовательскоеОписаниеСобытий`
- `InformationRegister_Kaspi_УведомленияПользователей`
- `Catalog_Kaspi_Профили_СобытияПользователей`
- `Catalog_Kaspi_СписокГородов`
- `Catalog_Kaspi_ТочкиПродаж_Склады`
- `Catalog_Kaspi_ТочкиПродаж_ДополнительныеПараметрыЗаполнения`
- `Catalog_Kaspi_ХарактеристикиКатегории`
- `Catalog_Kaspi_ХарактеристикиКатегории_attributevalues`
- `Catalog_Kaspi_ХарактеристикиКатегории_Категории`
- `InformationRegister_Kaspi_АвторизацияЯндекс`
- `Document_Kaspi_ДетальнаяИнформацияПоОперациям_Возвраты`
- `Document_Kaspi_ЗаказыКлиентов_Ошибки`
- `Document_Kaspi_ЗаказыКлиентов_История`
- `Document_Kaspi_ЗаказыКлиентов_Изображения`
- `ExchangePlan_Kaspi_ПланОбмена_СписокСкладов`
- `ExchangePlan_Kaspi_ПланОбмена_СписокСтатусов`
- `InformationRegister_Kaspi_ИсторияОбновленияОстатковТоваров`
- `InformationRegister_Kaspi_ХарактеристикиТоваров`
- `AccumulationRegister_Kaspi_ВыручкаИСебестоимостьПродаж`
- `InformationRegister_Kaspi_ОтгрузкаЗаказовЧерезПоставки`
- `InformationRegister_Kaspi_ПодтвержденияОплатыЗаказов`
- `Constant_МультимаркетKZ_ИспользованиеМаркетплейсаKaspi`

### Ozon (46 сущностей)
- `Catalog_Ozon_Аккаунты`
- `Catalog_Ozon_СертификатыНоменклатуры`
- `InformationRegister_Ozon_ЗаказыFBS`
- `InformationRegister_Ozon_ДанныеВесовыхТоваров`
- `Catalog_Ozon_МетодыДоставки`
- `Catalog_Ozon_СертификатыНоменклатуры_Товары`
- `Catalog_Ozon_Уведомления`
- `InformationRegister_Ozon_ВозвратыFBS`
- `InformationRegister_Ozon_ВыкупТоваров`
- `InformationRegister_Ozon_ЖурналСобытий`
- `InformationRegister_Ozon_ОграниченияВыгружаемыхОстатковТоваров`
- `InformationRegister_Ozon_РаспределениеОстатковПоСкладамOzon`
- `InformationRegister_Ozon_СозданныеОтчеты`
- `InformationRegister_Ozon_СостояниеУведомлений`
- `InformationRegister_Ozon_ПроблемыОбмена`
- `Catalog_Ozon_Склады`
- `Catalog_Ozon_Склады_РабочиеДни`
- `InformationRegister_Ozon_НастройкиРегламентныхЗаданий`
- `InformationRegister_Ozon_СоответствиеЗначенийХарактеристик`
- `Catalog_Ozon_Аккаунты_СтатусНастроек`
- `Catalog_Ozon_ЗначенияХарактеристик`
- `Catalog_Ozon_КатегорииТоваров`
- `Catalog_Ozon_КатегорииТоваров_Характеристики`
- `Catalog_Ozon_КатегорииУведомлений`
- `Catalog_Ozon_ОписательныеКатегорииТоваров`
- `Catalog_Ozon_ОписательныеКатегорииТоваров_Характеристики`
- `Catalog_Ozon_СертификатыНоменклатуры_Файлы`
- `Catalog_Ozon_СсылкиНаДокументы`
- `Catalog_Ozon_СсылкиНаСправочники`
- `Catalog_Ozon_ТипыСертификатов`
- `Catalog_Ozon_ТипыСоответствияТребованиям`
- `Catalog_Ozon_Характеристики`
- `InformationRegister_Ozon_ОбновленияУведомлений`
- `InformationRegister_Ozon_АктуальностьЗначенийХарактеристик`
- `InformationRegister_Ozon_АктуальностьОстатковТоваров`
- `InformationRegister_Ozon_ДатыАктуальностиСправочнойИнформации`
- `InformationRegister_Ozon_СоответствиеДопУслуг`
- `InformationRegister_Ozon_СоответствиеОсновныхРеквизитовТовара`
- `InformationRegister_Ozon_СоответствиеТоваров`
- `InformationRegister_Ozon_ЗадачиЗагрузкиКодовАктивации`
- `InformationRegister_Ozon_ЗаявкиНаСкидку`
- `InformationRegister_Ozon_PerformanceAPIAccessToken`
- `InformationRegister_Ozon_ЗадачиИмпортаНовыхТоваров`
- `InformationRegister_Ozon_ЗначенияХарактеристикПоКатегориям`
- `InformationRegister_Ozon_Константы`
- `Constant_МультимаркетKZ_ИспользованиеМаркетплейсаOzon`

### Halyk (54 сущностей)
- `Document_Halyk_ЗаказыКлиентов`
- `Catalog_Halyk_Профили`
- `Catalog_Halyk_КарточкаТовара`
- `Catalog_Halyk_Отзывы`
- `Document_Halyk_ВозвратТоваровПриДоставке`
- `Document_Halyk_ДетальнаяИнформацияПоОперациям_Операции`
- `Document_Halyk_ДетальнаяИнформацияПоОперациям_ПлатежиПериоды`
- `Document_Halyk_ДетальнаяИнформацияПоОперациям_ПлатежиРасшифровка`
- `Document_Halyk_ПоставкаТоваров`
- `Catalog_Halyk_ТочкиПродаж`
- `Document_Halyk_ВыгрузкаТоваровВМагазин`
- `Document_Halyk_ДетальнаяИнформацияПоОперациям_Платежи`
- `InformationRegister_Halyk_ЖурналСобытий`
- `InformationRegister_Halyk_ИсторияЗаказовКлиентов`
- `Catalog_Halyk_Категории`
- `Catalog_Halyk_СлужбыДоставки`
- `Document_Halyk_ВозвратТоваровПриДоставке_ЗаказыКлиентов`
- `Document_Halyk_ВыгрузкаТоваровВМагазин_КарточкиТоваров`
- `Document_Halyk_ВыгрузкаТоваровВМагазин_Ошибки`
- `Document_Halyk_ДетальнаяИнформацияПоОперациям`
- `Document_Halyk_ЗаказыКлиентов_Товары`
- `Document_Halyk_ПоставкаТоваров_ЗаказыКлиентов`
- `InformationRegister_Halyk_ИсторияСинхронизаций`
- `InformationRegister_Halyk_ИсторияВыгрузкиДокументов`
- `InformationRegister_Halyk_ИсторияОбновленияОстатковТоваров`
- `InformationRegister_Halyk_ИсторияТоваров`
- `Catalog_Halyk_КарточкаТовара_images`
- `Catalog_Halyk_КарточкаТовара_errors`
- `Catalog_Halyk_КарточкаТовара_Предзаказ`
- `Catalog_Halyk_Отзывы_galleryImages`
- `Catalog_Halyk_ПользовательскоеОписаниеСобытий`
- `Catalog_Halyk_Производители`
- `Catalog_Halyk_Профили_СобытияПользователей`
- `Catalog_Halyk_СписокГородов`
- `Catalog_Halyk_ТочкиПродаж_Склады`
- `Catalog_Halyk_ТочкиПродаж_ДополнительныеПараметрыЗаполнения`
- `Catalog_Halyk_ХарактеристикиКатегории`
- `Catalog_Halyk_ХарактеристикиКатегории_attributevalues`
- `Catalog_Halyk_ХарактеристикиКатегории_Категории`
- `Document_Halyk_ДетальнаяИнформацияПоОперациям_Реализации`
- `Document_Halyk_ДетальнаяИнформацияПоОперациям_Возвраты`
- `Document_Halyk_ЗаказыКлиентов_Ошибки`
- `Document_Halyk_ЗаказыКлиентов_История`
- `Document_Halyk_ЗаказыКлиентов_Изображения`
- `InformationRegister_Halyk_АвторизацияЯндекс`
- `InformationRegister_Halyk_УведомленияПользователей`
- `InformationRegister_Halyk_НастройкиИнтеграции`
- `InformationRegister_Halyk_РеализацияТоваровПоТочкамПродаж`
- `InformationRegister_Halyk_ТокенАвторизации`
- `InformationRegister_Halyk_ХарактеристикиТоваров`
- `InformationRegister_Halyk_ПодтвержденияОплатыЗаказов`
- `InformationRegister_Halyk_ОтгрузкаЗаказовЧерезПоставки`
- `AccumulationRegister_Halyk_ВыручкаИСебестоимостьПродаж`
- `Constant_МультимаркетKZ_ИспользованиеМаркетплейсаHalyk`

### Сайт / iq_ (16 сущностей)
- `BusinessProcess_iq_ПродажаТоваровИнтернетМагазина`
- `BusinessProcess_iq_ПродажаТоваровИнтернетМагазина_РезультатыСогласования`
- `InformationRegister_iq_ВремяРезервированияТоваровВЧеке`
- `Catalog_iq_СпособыДоставкиТоваров`
- `Document_iq_НазначениеТоваровДня`
- `InformationRegister_iq_СостоянияЗаказов`
- `Document_iq_НазначениеТоваровДня_ТоварыДня`
- `Document_iq_ПроведениеАкций_Товары`
- `Catalog_iq_РекомендуемыеТовары`
- `InformationRegister_iq_ВесОбъемТоваров`
- `Catalog_iq_ОписаниеТовара`
- `Catalog_iq_СпособыДоставкиТоваров_Тарифы`
- `Catalog_iq_СостоянияЗаказа`
- `Catalog_iq_СпособыОплатыЗаказа`
- `InformationRegister_iq_КатегорииТоваров`
- `InformationRegister_iq_ФильтрыТоваровИнтернетМагазина`

---

## 10. Достаточно ли данных для ТОП товаров?

| Период | Возможно? | Условие |
|--------|-----------|---------|
| Год | ✅ | Нужны дата + номенклатура + количество |
| Полгода | ✅ | То же |
| Квартал | ✅ | То же |
| Месяц | ✅ | То же |

---

## 11. Что нужно для сравнения с ручным ТОП-100

1. Получить от владельца Excel/CSV с ТОП-100 из 1С (артикул + количество продаж)
2. Из OData запросить `AccumulationRegister_*` (продажи) за тот же период
3. Соединить по полю Номенклатура.Ref_Key или Артикул
4. Сравнить ранги: совпадают ли ТОП-10, ТОП-50, ТОП-100

---

## 12. Вопросы для Артёма / Евгения

1. **Основной регистр продаж:** Какой регистр накопления используется для учёта
   розничных и оптовых продаж? (`ПродажиОбороты`, `РеализацияТоваров`, другое?)
2. **Документ реализации:** Как называется основной документ продажи —
   `Document_РеализацияТоваровУслуг` или `Document_ЧекККМ` (для розницы)?
3. **Kaspi:** Продажи через Kaspi проходят отдельным документом или
   попадают в общий регистр продаж?
4. **Период данных:** С какой даты в 1С хранятся данные о продажах?
   (нужно для ТОП за год/полгода)
5. **Виртуальные таблицы:** Доступны ли через OData виртуальные таблицы
   `AccumulationRegister_*_Оборот` или `AccumulationRegister_*_ОстаткиИОбороты`?
   (они дают агрегаты без перебора строк)

---

## Следующий шаг

После ответов Артёма: создать `catalog/odata_sales_reader.py` — скрипт,
который запросит первые 10 записей из ключевого регистра продаж и покажет реальные данные.