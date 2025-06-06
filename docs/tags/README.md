Теги в маркеті
===============

Додавання тегів
-----------------

При додаванні нового тега обов'язковими є поля:
* `name` - назва тегу
* `name_en` - переклад назви

Поле `code` можна додавати опціонально. Головне, щоб воно було формату alphanumeric.

```doctest
POST /tags
{
   "data": {
       "code": "NT1",
       "name": "Новий",
       "name_en": "New"
   }
}


201 Created
{
   "data": {
       "code": "NT1",
       "name": "Новий",
       "name_en": "New",
   }
}

```

Автоматична генерація `code`:

```doctest
POST /tags
{
   "data": {
       "name": "Хіт продажу",
       "name_en": "Hit sale"
   }
}


201 Created
{
   "data": {
       "code": "hit-sale",
       "name": "Хіт продажу",
       "name_en": "Hit sale",
   }
}

```

Поля `code`, `name` і `name_en` мають бути унікальні для кожного тегу. Тому при додаванні нового тегу з таким самим полем, буде помилка:

```doctest
POST /tags
{
   "data": {
       "name": "Хіт продажу",
       "name_en": "Hit sale"
   }
}


400 BadRequest
{
   "errors": [
        "Duplicate value for 'name': 'Хіт продажу'"
   ]
}

```


Отримання тегів
---------------

```doctest
GET /tags
{}


200 OK
{
   "data": [
       {
           "code": "NT1",
           "name": "Новий",
           "name_en": "New tag"
       },
       {
           "code": "hit-sale",
           "name": "Хіт продажу",
           "name_en": "Hit sale"
       },
   ]
}

```

Отримання тегу по `code`:

```doctest
GET /tags/hit-sale
{}


200 OK
{
   "data": {
       "code": "hit-sale",
       "name": "Хіт продажу",
       "name_en": "Hit sale",
   }
}

```

Редагування тегів
-----------------
```doctest
PATCH /tags/NT1
{
   "data": {
       "name_en": "New tag"
   }
}


200 OK
{
   "data": {
       "code": "NT1",
       "name": "Новий",
       "name_en": "New tag"
   }
}

```

Видалення тегу 
------------------

Якщо тег непотрібний чи вже неактуальний, то є можливість видалення за допомогою DELETE ендпоінта:

```doctest
DELETE /tags/NT1
{}


200 OK
{
   "result": "success"
}

```

Видаляти тег можна тільки, якщо він не використовується в жодній категорії/профілі:

```doctest
DELETE /tags/hit-sale
{}


400 BadRequest
{
   "errors": [
        "Tag `hit-sale` is used in categories ['15240000-107114-40996564', ...]"
   ]
}

```

Використаня тегів
==================

```doctest
PATCH /categories/15240000-107114-40996564
{
    "data": {
       "tags": ["NT1", "hit-sale"]
   }
}


200 OK
{
   "data": {
       "id": "15240000-107114-40996564",
       "classification": {
            "scheme": "ДК021",
            "description": "Рибні консерви та інші рибні страви і пресерви",
            "id": "15240000-2"
       },
       "title": "Консерви рибні",
       ...
       "tags": ["NT1", "hit-sale"]
   }
}

```

При цьому:
* Легко оновлювати переклади —> зміни в одному місці відобразяться всюди.
* Легке масштабування —> Можна додати додаткові поля в тег (опис, категорія, активність тощо), не змінюючи всі об’єкти.
