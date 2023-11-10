КраудСорсінг товарів
====================

Реєстарція користувача
----------------------

```doctest
POST /crowd-sourcing/contributor
{
   "data": {
       "contributor": {
          "name": "Повна назва юридичної організації.",
          "identifier": {
            "scheme": "UA-EDR",
            "id": "40996564",
            "legalName": "Назва організації"
          },
          "address": {
            "countryName": "Україна",
            "streetAddress": "вул. Банкова, 11, корпус 1",
            "locality": "м. Київ",
            "region": "м. Київ",
            "postalCode": "01220"
          },
          "contactPoint": {
            "name": "прізвище, ім’я та по батькові (за наявності) контактної особи користувача",
            "telephone": "+0440000000",
            "email": "aa@aa.com"
          }
       },
       "documents": []
   }
}


201 Created
{
   "data": {
       "id": "111111111111111111111111",
       "dateCreated": "2023-12-01T00:00:00+03:00",
       "dateModified": "2023-12-01T00:00:00+03:00",
       "owner": "test.broker",
       "contributor": {
          ...
       },
       ...
   }
}

```

Документи до реєстарції
-----------------------

```doctest
POST /crowd-sourcing/contributor/111111111111111111111111/documents
{
  "data": {
    "title": "Document.pdf",
    "url": "http://public-docs-sandbox.prozorro.gov.ua/get/6d5acc9f6744445090ee6163719b792e?Signature=xpZcFTPGJQ8J6leBYaQWYeW0CyQyt1SG%2F6EugQxRyxlFu7XmMlj%2BasCkDKsxWXiGZUTnRU%2BOkiJsST%2B0myYDDw%3D%3D&KeyID=a8968c46",
    "hash": "md5:00000000000000000000000000000000",
    "format": "application/pdf"
  }
}

201 Created
```


Скасування реєстарції (Бан)
---------------------------
Здійснюєтся від імені ЦЗО. 
dueDate - опціональне, за відсутності бан постійний. 

```doctest
POST /crowd-sourcing/contributor/111111111111111111111111/bans
{
  "data": {
    "reason": "LANGUAGE",
    "description": "матюкався та розмовляв російською",
    "dueDate": "2024-02-29T00:00:01+02:00",
    "administrator": {
        "identifier": {
          "id": "42574629",
          "scheme": "UA-EDR",
          "legalName_en": "STATE ENTERPRISE \"MEDICAL PROCUREMENT OF UKRAINE\"",
          "legalName_uk": "ДЕРЖАВНЕ ПІДПРИЄМСТВО \"МЕДИЧНІ ЗАКУПІВЛІ УКРАЇНИ\""
        },
    },
    "documents": [
        {
            "title": "sign.p7s",
            "url": "http://public-docs-sandbox.prozorro.gov.ua/...",
            "hash": "md5:00000000000000000000000",
            "format": "application/pk7s",
        }
    ]
  }
}

201 Created
{
  "data": {
    "id": "666666666666666666666666",
    "dateCreated": "2023-02-24T00:00:01+02:00",
    "reason": "LANGUAGE",
    ....
  }
}
```


Створення заявки на додавання товару
-------------------------------------
```doctest
POST /crowd-sourcing/contributor/111111111111111111111111/requests
{
  "data": {
     "product": {
          "title": "Маски медичні IGAR тришарові на гумках 50 шт./уп.",
          "description": "Маски медичні IGAR тришарові на гумках 50 шт./уп. Гарантія від виробника.",
          "identifier": {
            "id": "463234567819",
            "scheme": "UPC"
          },
          "relatedCategory": "33190000-0000-10033300",
          "images": [
            {
              "sizes": "500x175",
              "url": "/static/images/619890.500x175.jpeg"
            }
          ],
          "additionalClassifications": [
            {
              "description": "Засоби індивідуального захисту (респіратори та маски) без клапану",
              "id": "5011020",
              "scheme": "KMU777"
            }
          ],
          "alternativeIdentifiers": [
            {
              "id": "0463234567819",
              "scheme": "EAN-13"
            }
          ],
          "classification": {
            "description": "Медичне обладнання та вироби медичного призначення різні",
            "id": "33190000-8",
            "scheme": "ДК021"
          },
          "requirementResponses": [
            {
              "value": "одноразова"
            },
            {
              "value": 3
            },
          ],
     },
     "documents": [],
  }
}



201 Created
{
  "data": {
     "id": "777777777777777777777777",
     "contributor_id": "111111111111111111111111",
     "owner": "test.broker",
     "dateCreated": "2023-02-24T00:00:01+02:00",
     "product": {
        "title": "Маски медичні IGAR тришарові на гумках 50 шт./уп.",
        "description": ...
     },
     ...
  }
}
```


Модерація товарів
-----------------
Під час прийняття запиту, товар буде додаватися в каталог.
ЦЗО отримує токен власника і інші деталі по товару у відповіді.


TODO: Category access_token ????

```doctest
POST /crowd-sourcing/requests/777777777777777777777777/accept
{
    "administrator": {
        "identifier": {
          "id": "42574629",
          "scheme": "UA-EDR",
          "legalName_en": "STATE ENTERPRISE \"MEDICAL PROCUREMENT OF UKRAINE\"",
          "legalName_uk": "ДЕРЖАВНЕ ПІДПРИЄМСТВО \"МЕДИЧНІ ЗАКУПІВЛІ УКРАЇНИ\""
        }
    }
}

200 OK
{
    "data": {
        "id": "777777777777777777777777",
        "dateCreated": "2023-02-24T00:00:01+02:00",
        "dateModified": "2023-03-09T17:19:45.908462+02:00",
        "acception": {
            "administrator": {
                "identifier": {
                  "id": "42574629",
                  "scheme": "UA-EDR",
                  "legalName_en": "STATE ENTERPRISE \"MEDICAL PROCUREMENT OF UKRAINE\"",
                  "legalName_uk": "ДЕРЖАВНЕ ПІДПРИЄМСТВО \"МЕДИЧНІ ЗАКУПІВЛІ УКРАЇНИ\""
                }
            }
            "date": "2023-03-09T17:19:45.908462+02:00",
        },
        "product": {
            "id": "888888888888888888888888",
            "dateCreated": "2023-03-09T17:19:45.908462+02:00",
            "owner": "test.broker",
            "title": "Маски медичні IGAR тришарові на гумках 50 шт./уп.",
            "description": ...
        },
    },
    "access": {
        "token": "999999999999999999999"
    }
}    

```
Після підтвердження продукт доступний в маркеті
```doctest
GET /products/888888888888888888888888

200 OK 
{
    "data": {
        "id": "888888888888888888888888",
        "dateCreated": "2023-02-25T00:00:01+02:00",
        "dateModified": "2023-02-25T00:00:01+02:00",
        "owner": "test.broker",
        "title": "Маски медичні IGAR тришарові на гумках 50 шт./уп.",
        "description": ...
    }
}
```


При відхиленні заявки товар відповідно не створюєтся. 
```doctest
POST /crowd-sourcing/requests/777777777777777777777777/reject
{
    "data": {
        "reason": "INVALID",
        "description": "Невірно заповнені дані",
        "administrator": {
            "identifier": {
              "id": "42574629",
              "scheme": "UA-EDR",
              "legalName_en": "STATE ENTERPRISE \"MEDICAL PROCUREMENT OF UKRAINE\"",
              "legalName_uk": "ДЕРЖАВНЕ ПІДПРИЄМСТВО \"МЕДИЧНІ ЗАКУПІВЛІ УКРАЇНИ\""
            }
        }
    }
}

200 OK
{
    "data": {
        "id": "777777777777777777777777",
        "dateCreated": "2023-02-24T00:00:01+02:00",
        "dateModified": "2023-03-09T17:19:45.908462+02:00",
        "rejection": {
            "reason": "INVALID",
            "description": "Невірно заповнені дані",
            "date": "2023-02-25T00:00:01+02:00",
            "reviewer": {
                "identifier": {
                  "id": "42574629",
                  "scheme": "UA-EDR",
                  "legalName_en": "STATE ENTERPRISE \"MEDICAL PROCUREMENT OF UKRAINE\"",
                  "legalName_uk": "ДЕРЖАВНЕ ПІДПРИЄМСТВО \"МЕДИЧНІ ЗАКУПІВЛІ УКРАЇНИ\""
                }
            }
        },
        "documents": [],
        "product": {
            "title": "Маски медичні IGAR тришарові на гумках 50 шт./уп.",
            "description": ...
        },
    }
}    

```


Оновлення
---------
При додаванні або модерації заявки, вона з'являєтся в кінці фіда заявок.

```doctest
GET /crowd-sourcing/requests
{
    "data": [
        {
            "dateModified": "2023-03-09T17:19:45.908462+02:00",
            "id": "777777777777777777777777"
        }
    ],
    "next_page": {
        "offset": "2023-03-09T17:19:45.908462+02:00",
        "path": "/api/crowd-sourcing/requests?offset=2023-03-09T17%3A19%3A45.908462%2B02%3A00&limit=1",
        "uri": "https://market-api.prozorro.gov.ua/api/crowd-sourcing/requests?offset=2023-03-09T17%3A19%3A45.908462%2B02%3A00&limit=1"
    },
    "prev_page": {
        "offset": "2023-03-09T17:19:45.908462+02:00",
        "path": "/api/crowd-sourcing/requests?offset=2023-03-09T17%3A19%3A45.908462%2B02%3A00&limit=1&descending=1",
        "uri": "https://market-api.prozorro.gov.ua/api/crowd-sourcing/requests?offset=2023-03-09T17%3A19%3A45.908462%2B02%3A00&limit=1&descending=1"
    }
}
```