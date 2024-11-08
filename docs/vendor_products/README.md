# Локалізація v2.0


## Загальний опис рішення

Локалізовані товари мають знаходитись в основих категоріях і профілях товарів. 
Такі товари будуть містити відповідь на критерій рівня локалізації та року проведення обрахунку, 
для того щоб потрапляти в спеціальні профілі. 
Причому потряплаяти в профілі вони будуть за звийчаним механізмом, аналогічно іншим товарам. 


## Створення категорій і профілів

ЦЗО додає критерій локалізації до існуючих категорій. 



### Створення критерію
```doctest
POST /api/categories/33120000-645406-425746299/criteria

{
   "data": {
        "title": "Створення передумов для сталого розвитку та модернізації вітчизняної промисловості",
        "description": "Товар включений до додаткового переліку, що затверджений Кабінетом Міністрів України, і має ступінь локалізації виробництва, який перевищує або дорівнює ступеню локалізації виробництва, встановленому на відповідний рік. Ці вимоги не застосовуються до закупівель, які підпадають під дію положень Закону України \"Про приєднання України до Угоди про державні закупівлі\", а також положень про державні закупівлі інших міжнародних договорів України, згода на обов’язковість яких надана Верховною Радою України.",
        "classification": {
            "scheme": "ESPD211",
            "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"
        },
        "legislation": [...],
        "source": "tenderer",
        "id": "1932744bcf3d4fb98cb976a94d984da1"
    }
}


201 Created
{
   "data": {
       "title": "Створення передумов для сталого розвитку та модернізації вітчизняної промисловості",
        "description": "Товар включений до додаткового переліку, що затверджений Кабінетом Міністрів України, і має ступінь локалізації виробництва, який перевищує або дорівнює ступеню локалізації виробництва, встановленому на відповідний рік. Ці вимоги не застосовуються до закупівель, які підпадають під дію положень Закону України \"Про приєднання України до Угоди про державні закупівлі\", а також положень про державні закупівлі інших міжнародних договорів України, згода на обов’язковість яких надана Верховною Радою України.",
        "classification": {
            "scheme": "ESPD211",
            "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"
        },
        "legislation": [...],
        "source": "tenderer",
        "requirementGroups": [],
        "id": "1932744bcf3d4fb98cb976a94d984da1"
   }
}
```

Створення requirementGroup
```doctest
POST /api/categories/33120000-645406-425746299/criteria/1932744bcf3d4fb98cb976a94d984da1/requirementGroups

{
   "data": {
        "description": "За наявності складових вітчизняного виробництва у собівартості товару, підтверджується, що",
        "id": "6339792b37114b26aed4fd2bd0d6afc6"
    }
}


201 Created
{
   "data": {
       "description": "За наявності складових вітчизняного виробництва у собівартості товару, підтверджується, що",
       "id": "6339792b37114b26aed4fd2bd0d6afc6"
   }
}
```

Створюєм requirement.
Ще трошки (дякуєм величним архітекторам джейсону)
```doctest
POST /api/categories/33120000-645406-425746299/criteria/1932744bcf3d4fb98cb976a94d984da1/requirementGroups/6339792b37114b26aed4fd2bd0d6afc6/requirements

{
   "data": {
        "title": "Ступінь локалізації виробництва товару, що є предметом закупівлі, перевищує або дорівнює ступеню локалізації виробництва, встановленому на відповідний рік",
        "dataType": "number",
        "minValue": 20,
        "unit": {
            "name": "Відсоток",
            "code": "P1"
        },
        "id": "ba81db2cafbd49f7ad68aa1c1c0f286d"
    }
}


201 Created
{
   "data": {
        "title": "Ступінь локалізації виробництва товару, що є предметом закупівлі, перевищує або дорівнює ступеню локалізації виробництва, встановленому на відповідний рік",
        "dataType": "number",
        "minValue": 20,
        "unit": {
            "name": "Відсоток",
            "code": "P1"
        },
        "id": "ba81db2cafbd49f7ad68aa1c1c0f286d"
    }
}
```

### Створення профілю

До категорій можуть бути створені нові або відредаговані старі профілі зі вказанням критерія локалізації. 
Також є сенс вказати додатковий критерій "Рік проведення оцінки ступеню локалізації", 
щоб подані локалізовані товари автоматично попадали у визначені профілі. 

Приклад критерії профілю
```doctest
GET /api/0/profiles/33120000-645406-425746299-000000

{
    "data": {
        "criteria": [
            {
                "title": "Створення передумов для сталого розвитку та модернізації вітчизняної промисловості",
                "description": "Товар включений до додаткового переліку, що затверджений Кабінетом Міністрів України, і має ступінь локалізації виробництва, який перевищує або дорівнює ступеню локалізації виробництва, встановленому на відповідний рік. Ці вимоги не застосовуються до закупівель, які підпадають під дію положень Закону України \"Про приєднання України до Угоди про державні закупівлі\", а також положень про державні закупівлі інших міжнародних договорів України, згода на обов’язковість яких надана Верховною Радою України.",
                "classification": {
                    "scheme": "ESPD211",
                    "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"
                },
                "legislation": [...],
                "source": "tenderer",
                "requirementGroups": [
                    {
                    "description": "За наявності складових вітчизняного виробництва у собівартості товару, підтверджується, що",
                    "requirements": [
                        {
                            "title": "Ступінь локалізації виробництва товару, що є предметом закупівлі, перевищує або дорівнює ступеню локалізації виробництва, встановленому на відповідний рік",
                            "dataType": "number",
                            "minValue": 20,
                            "unit": {
                                "name": "Відсоток",
                                "code": "P1"
                            },
                            "id": "ba81db2cafbd49f7ad68aa1c1c0f286d"
                        },
                        {
                            "title": "Рік проведення оцінки ступеню локалізації виробництва",
                            "dataType": "number",
                            "minValue": 2024,
                            "maxValue": 2024,
                            "unit": {
                                "name": "Рік",
                                "code": "ANN"
                            },
                            "id": "090cf60ed79d488c931efe6860458e96"
                        }
                    ],
                    "id": "6339792b37114b26aed4fd2bd0d6afc6"
                    }
                ],
                "id": "1932744bcf3d4fb98cb976a94d984da1"
            }
        ],
        "dateModified": "2024-10-18T00:25:35.234720+03:00",
        "dateCreated": "2023-12-29T18:46:11.937062+02:00",
        ...
    }
}
```



## Створення товарів в системі

### Реєстрація виробника

Виробник заповнює необхідні інформацію і документи на майданчику. Після чього майданчик реєструє його в маркеті.

Створення завки
```doctest
POST /vendors
{
    "data": {
        "vendor": {
            "name": "ПП ГО Постачальник 2",
            "address": {
                "countryName": "Україна",
                "locality": "рее",
                "postalCode": "77665",
                "region": "Київська область",
                "streetAddress": "Jaunystes 21-6"
            },
            "contactPoint": {
                "name": "Макаров Василb Петрович",
                "telephone": "380503333333",
                "email": "case12etender@i.ua"
            },
            "identifier": {
                "id": "00000506",
                "legalName": "ПП ГО Постачальник 2",
                "scheme": "UA-EDR"
            }
        },
        "categories": [
            {
                "id": "33120000-645406-425746299"
            }
        ]
    }
}


201 Created
{
   "data": {
       "id": "6089d44828794826aca4696f66062551",
       "owner": "e-tender.biz",
       "dateCreated": "2023-12-01T00:00:00+03:00",
       "dateModified": "2023-12-01T00:00:00+03:00",
       "isActivated": false,
       ...
   }
}
```

Додавання документів
```doctest
POST /vendors/6089d44828794826aca4696f66062551/documents
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

Активація виробника
```doctest
PATCH /vendors/6089d44828794826aca4696f66062551
{
  "data": {
    "isActivated": true
  }
}

201 Created
{
    "data": {
        "vendor": {...},
        "categories": [
            {
            "id": "33120000-645406-425746299"
            }
        ],
        "isActivated": true,
        "dateCreated": "2022-08-17T21:31:04.595315+03:00",
        "dateModified": "2022-08-17T21:44:03.803962+03:00",
        "status": "active",
        "documents": [...],
        "id": "6089d44828794826aca4696f66062551",
        "owner": "e-tender.biz"
    }
}
```

Після активації виробник вже може додавити товари. 

TODO: існуючим виробникам потрібно буде промігрувати категорії маючи надану таблицю відповідностей.


### Створення товару

- Товар створюється без "relatedProfiles" (заповнюються автоматично)
- Натомість включає відповіді на критерії локалізації


```doctest
POST /vendors/6089d44828794826aca4696f66062551/products

{
    "data": {
        "requirementResponses": [
            {
                "requirement": "Ступінь локалізації виробництва товару, що є предметом закупівлі, перевищує або дорівнює ступеню локалізації виробництва, встановленому на відповідний рік",
                "value": 25.29
            },
            {
                "requirement": "Рік проведення оцінки ступеню локалізації виробництва",
                "value": 2024
            }
        ],
        "title": "Глибинний насос комплекті",
        "relatedCategory": "33120000-645406-425746299",
        "description": "Глибинний насос в комплекті",
        "classification": {
            "id": "42120000-6",
            "description": "Насоси та компресори",
            "scheme": "ДК021"
        },
        "additionalClassifications": [],
        "identifier": {
            "id": "98699057",
            "scheme": "EAN-13"
        },
        "marketAdministrator": {...},  # TBD
        "vendor": {
            "id": "221064c6a98b4b21ba3853d354069f8b",
            "name": "Науково-інженерно-промислове товариство OK",
            "identifier": {
                "id": "33333333",
                "legalName": "Науково-інженерно-промислове товариство OK",
                "scheme": "UA-EDR"
            }
        }
    }
}



201 Created
{
  "data": {
     "id": "1bf56d5161a4471bb2543a7d958f5d3d",
     "owner": "test.broker",
     "dateCreated": "2023-02-24T00:00:01+02:00",
     ...
  }
}
```


Додавання документів до продукту

```doctest
POST /vendors/6089d44828794826aca4696f66062551/products/60891bf56d5161a4471bb2543a7d958f5d3d/documents
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






