# Локалізація v3.0

Єдиний флоу для реєстрації виробника та публікації локалізованих товарів через ендпоінт краудсорсингу.

Флоу складається з двох незалежних частин:

1. **Реєстрація виробника** — одноразово, підтверджується документами і КЕП
2. **Подача заявки на товар** — для кожного нового товару, з документами і відповіддю на критерій локалізації

> Реєстрація постачальника (перший крок) описана в [docs/crowdsourcing/README.md](../crowdsourcing/README.md).
> Цей документ починається з кроку реєстрації виробника.


## Реєстрація виробника

Після реєстрації як постачальник, організація може підтвердити статус виробника.
Для цього створюється об'єкт `manufacturer` і завантажуються підтверджуючі документи.

### Крок 1 — Створити запис виробника

Документи можна передати одразу в тілі запиту або завантажувати окремо (крок 2).

```doctest
PUT /api/crowd-sourcing/contributors/111111111111111111111111/manufacturer
{
    "data": {
        "documents": [
            {
                "title": "Сертифікат ISO 9001.pdf",
                "url": "http://public-docs-sandbox.prozorro.gov.ua/get/abc123...",
                "hash": "md5:00000000000000000000000000000000",
                "format": "application/pdf",
                "documentType": "certificate"
            }
        ]
    }
}

201 Created
{
    "data": {
        "dateCreated": "2025-01-15T10:00:00+02:00",
        "dateModified": "2025-01-15T10:00:00+02:00",
        "documents": [
            {
                "id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "title": "Сертифікат ISO 9001.pdf",
                "documentType": "certificate",
                "datePublished": "2025-01-15T10:00:00+02:00",
                "dateModified": "2025-01-15T10:00:00+02:00"
            }
        ]
    }
}
```

**Ідемпотентність.** Якщо `manufacturer` вже існує (наприклад, запит відправлено двічі через
мережеву помилку), повторний PUT повертає успішну відповідь з поточним станом об'єкта.
`dateCreated` не перезаписується. Документи з повторного запиту ігноруються.

```doctest
PUT /api/crowd-sourcing/contributors/111111111111111111111111/manufacturer
{
    "data": {
        "documents": [...]
    }
}

200 OK
{
    "data": {
        "dateCreated": "2025-01-15T10:00:00+02:00",
        "dateModified": "2025-01-15T10:00:00+02:00",
        "documents": [
            ...існуючі документи без змін...
        ]
    }
}
```


### Крок 2 — Завантажити документи виробника

Необхідно завантажити всі 5 обов'язкових документів. Подача заявки на локалізований товар
буде заблокована доки не будуть присутні всі типи документів.

**Перелік обов'язкових документів:**

| # | Назва | documentType |
|---|-------|--------------|
| 1 | Сертифікат відповідності систем управління якістю | `qualityCertificate` |
| 2 | Звіт про виробництво та реалізацію (Форма 1-НПП) | `productionReport` |
| 3 | Додаток 4ДФ (Відомості про податки на доходи) | `taxReport` |
| 4 | Фінансова звітність (Баланс, Форма 2/2М) | `financialReport` |
| 5 | Файл КЕП | `manufacturerSignature` |

```doctest
POST /api/crowd-sourcing/contributors/111111111111111111111111/manufacturer/documents
{
    "data": {
        "title": "Сертифікат ISO 9001.pdf",
        "url": "http://public-docs-sandbox.prozorro.gov.ua/get/abc123...",
        "hash": "md5:00000000000000000000000000000000",
        "format": "application/pdf",
        "documentType": "qualityCertificate"
    }
}

201 Created
{
    "data": {
        "id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "title": "Сертифікат ISO 9001.pdf",
        "documentType": "qualityCertificate",
        "datePublished": "2025-01-15T10:05:00+02:00",
        "dateModified": "2025-01-15T10:05:00+02:00",
        "format": "application/pdf",
        "url": "http://public-docs-sandbox.prozorro.gov.ua/get/abc123..."
    }
}
```

Аналогічно завантажуються решта документів (`productionReport`, `taxReport`, `financialReport`, `manufacturerSignature`).

```doctest
POST /api/crowd-sourcing/contributors/111111111111111111111111/manufacturer/documents
{
    "data": {
        "title": "sign.p7s",
        "url": "http://public-docs-sandbox.prozorro.gov.ua/get/sign123...",
        "hash": "md5:00000000000000000000000000000000",
        "format": "application/pk7s",
        "documentType": "manufacturerSignature"
    }
}

201 Created
```

Після завантаження всіх 5 документів виробник може подавати заявки на локалізовані товари.


## Подача заявки на локалізований товар

Є два флоу залежно від того чи клієнт передає `status: draft` при POST.

**Перелік обов'язкових документів товару:**

| # | Назва | documentType | Обов'язково |
|---|-------|--------------|-------------|
| 1 | Калькуляція собівартості товару | `costCalculation` | ✓ |
| 2 | Протокол випробувань щодо безпечності зразка товару | `safetyTestReport` | ✓ |
| 3 | Сертифікат відповідності, типу або свідоцтво WMI | `typeCertificate` | ні |
| 4 | Довідка виробника з переліком технологічних операцій | `technologicalOperationsReport` | ✓ |
| 5 | Файл КЕП | `productSignature` | ✓ |

---

### Флоу A — одразу `pending` (backward compatible)

Документи передаються разом із заявкою. Валідація і активація відбуваються в рамках одного POST.

```doctest
POST /api/crowd-sourcing/contributors/111111111111111111111111/requests
{
    "data": {
        "product": {
            "title": "Глибинний насос в комплекті",
            "relatedCategory": "42120000-645406-425746299",
            "classification": {"id": "42120000-6", "description": "Насоси та компресори", "scheme": "ДК021"},
            "identifier": {"id": "98699057", "scheme": "EAN-13"},
            "requirementResponses": [
                {
                    "requirement": "Ступінь локалізації виробництва товару...",
                    "value": 35,
                    "classification": {"scheme": "ESPD211", "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"},
                    "unit": {"name": "відсоток", "code": "P1"}
                }
            ],
            "documents": [
                {"title": "Калькуляція.pdf", "url": "...", "hash": "md5:000...", "format": "application/pdf", "documentType": "costCalculation"},
                {"title": "Протокол.pdf", "url": "...", "hash": "md5:000...", "format": "application/pdf", "documentType": "safetyTestReport"},
                {"title": "Довідка.pdf", "url": "...", "hash": "md5:000...", "format": "application/pdf", "documentType": "technologicalOperationsReport"},
                {"title": "sign.p7s", "url": "...", "hash": "md5:000...", "format": "application/pk7s", "documentType": "productSignature"}
            ]
        }
    }
}

201 Created
{
    "data": {
        "id": "777777777777777777777777",
        "status": "accepted",
        "acception": {"date": "2025-01-15T11:00:00+02:00"},
        "product": {
            "id": "888888888888888888888888",
            "title": "Глибинний насос в комплекті",
            ...
        }
    }
}
```

---

### Флоу B — спочатку `draft`, потім подача

Використовується коли документи потрібно завантажувати поступово.

**Крок 1 — Створити заявку в статусі `draft`**

```doctest
POST /api/crowd-sourcing/contributors/111111111111111111111111/requests
{
    "data": {
        "status": "draft",
        "product": {
            "title": "Глибинний насос в комплекті",
            "relatedCategory": "42120000-645406-425746299",
            "classification": {"id": "42120000-6", "description": "Насоси та компресори", "scheme": "ДК021"},
            "identifier": {"id": "98699057", "scheme": "EAN-13"},
            "requirementResponses": [
                {
                    "requirement": "Ступінь локалізації виробництва товару...",
                    "value": 35,
                    "classification": {"scheme": "ESPD211", "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"},
                    "unit": {"name": "відсоток", "code": "P1"}
                }
            ]
        }
    }
}

201 Created
{
    "data": {
        "id": "777777777777777777777777",
        "status": "draft",
        "product": {"title": "Глибинний насос в комплекті", ...}
    }
}
```

**Крок 2 — Завантажити документи до продукту**

```doctest
POST /api/crowd-sourcing/requests/777777777777777777777777/product/documents
{
    "data": {
        "title": "Калькуляція собівартості.pdf",
        "url": "http://public-docs-sandbox.prozorro.gov.ua/get/calc123...",
        "hash": "md5:00000000000000000000000000000000",
        "format": "application/pdf",
        "documentType": "costCalculation"
    }
}

201 Created
```

Аналогічно для решти документів. Для оновлення існуючого — `PATCH /requests/{id}/product/documents/{doc_id}`.

> Ці ендпоінти доступні лише при `status = draft`. При будь-якому іншому статусі → `400`.

**Крок 3 — Подати заявку на розгляд**

```doctest
PATCH /api/crowd-sourcing/requests/777777777777777777777777
{
    "data": {
        "status": "pending"
    }
}

200 OK
{
    "data": {
        "id": "777777777777777777777777",
        "status": "accepted",
        "acception": {"date": "2025-01-15T11:10:00+02:00"},
        "product": {
            "id": "888888888888888888888888",
            "title": "Глибинний насос в комплекті",
            ...
        }
    }
}
```

> Якщо виробник не зареєстрований, документи виробника або товару неповні,
> або виробника забанено — перехід в `pending` відхиляється з відповідною помилкою.

### Автоматична активація

Тригер — **дворівнева** перевірка `requirementResponses`:
- `classification.id = "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"`
- І `unit.code = "P1"` (відсоток локалізації, числова відповідь)

Критерій `LOCAL_ORIGIN_LEVEL` має дві групи вимог — відсоток локалізації і країна походження.
Реагуємо лише на першу. Відповідь з кодом країни (`dataType: string`) тригером не є.

Якщо відповідна відповідь є і всі валідації пройдено — заявка переходить одразу в `accepted`. Продукт доступний в каталозі одразу після відповіді:

```doctest
GET /api/products/888888888888888888888888

200 OK
{
    "data": {
        "id": "888888888888888888888888",
        "title": "Глибинний насос в комплекті",
        "relatedCategory": "42120000-645406-425746299",
        "requirementResponses": [
            {
                "requirement": "Ступінь локалізації виробництва товару...",
                "value": 35,
                "classification": {"scheme": "ESPD211", "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"},
                "unit": {"name": "відсоток", "code": "P1"}
            }
        ],
        "documents": [
            {
                "id": "cccccccccccccccccccccccccccccccc",
                "title": "Калькуляція собівартості.pdf",
                "documentType": "costCalculation",
                "datePublished": "2025-01-15T11:00:00+02:00",
                "dateModified": "2025-01-15T11:00:00+02:00",
                "format": "application/pdf",
                "url": "http://public-docs-sandbox.prozorro.gov.ua/get/calc123..."
            },
            {
                "id": "dddddddddddddddddddddddddddddddd",
                "title": "Протокол випробувань.pdf",
                "documentType": "safetyTestReport",
                "datePublished": "2025-01-15T11:00:00+02:00",
                "dateModified": "2025-01-15T11:00:00+02:00",
                "format": "application/pdf",
                "url": "http://public-docs-sandbox.prozorro.gov.ua/get/safety123..."
            },
            {
                "id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                "title": "Довідка технологічних операцій.pdf",
                "documentType": "technologicalOperationsReport",
                "datePublished": "2025-01-15T11:00:00+02:00",
                "dateModified": "2025-01-15T11:00:00+02:00",
                "format": "application/pdf",
                "url": "http://public-docs-sandbox.prozorro.gov.ua/get/tech123..."
            },
            {
                "id": "ffffffffffffffffffffffffffffffff",
                "title": "sign.p7s",
                "documentType": "productSignature",
                "datePublished": "2025-01-15T11:00:00+02:00",
                "dateModified": "2025-01-15T11:00:00+02:00",
                "format": "application/pk7s",
                "url": "http://public-docs-sandbox.prozorro.gov.ua/get/prodsign123..."
            }
        ],
        "dateCreated": "2025-01-15T11:00:00+02:00",
        "dateModified": "2025-01-15T11:00:00+02:00"
    }
}
```


## Бан виробника

Бан накладається адміністратором Прозорро і блокує всі заявки контрибутора.
На відміну від попереднього механізму — не прив'язаний до категорії конкретного ЦЗО.

```doctest
POST /api/crowd-sourcing/contributors/111111111111111111111111/bans
{
    "data": {
        "reason": "rulesViolation",
        "description": "Подано недостовірні документи виробника",
        "administrator": {
            "identifier": {
                "id": "02426097",
                "legalName": "ДП \"ПРОЗОРРО\"",
                "scheme": "UA-EDR"
            }
        }
    }
}

201 Created
{
    "data": {
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "dateCreated": "2025-01-20T09:00:00+02:00",
        "dueDate": "2026-01-20T09:00:00+02:00",
        "reason": "rulesViolation",
        "description": "Подано недостовірні документи виробника",
        "administrator": {
            "identifier": {
                "id": "02426097",
                "legalName": "ДП \"ПРОЗОРРО\"",
                "scheme": "UA-EDR"
            }
        }
    }
}
```

Після накладення бану спроба подати заявку на локалізований товар повертає `403 Forbidden`.

### curl

```bash
curl -X POST \
  'https://market-api.prozorro.gov.ua/api/crowd-sourcing/contributors/111111111111111111111111/bans' \
  -u 'prozorro_admin_login:password' \
  -H 'Content-Type: application/json' \
  -d '{
    "data": {
      "reason": "rulesViolation",
      "description": "Подано недостовірні документи виробника",
      "administrator": {
        "identifier": {
          "id": "02426097",
          "legalName": "ДП \"ПРОЗОРРО\"",
          "scheme": "UA-EDR"
        }
      }
    }
  }'
```
