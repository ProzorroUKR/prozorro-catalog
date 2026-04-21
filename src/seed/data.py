"""
Seed data: categories, products and their builders for office-supply test data.
"""

import random
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Kyiv")

MARKET_ADMINISTRATOR = {
    "name": 'Тестова центральна закупівельна організація "МЕДИЧНА"',
    "address": {
        "countryName": "Україна",
        "locality": "Київ",
        "postalCode": "02200",
        "region": "Київська область",
        "streetAddress": "вулиця Ушинського, 40",
    },
    "contactPoint": {
        "email": "czo.moza@gmail.com",
        "faxNumber": "0445550055",
        "name": "Надія Бігун",
        "telephone": "380509995906",
        "url": "http://czo.moz.gov.ua/",
    },
    "identifier": {
        "id": "42574629",
        "legalName": 'Тестова центральна закупівельна організація "МЕДИЧНА"',
        "scheme": "UA-EDR",
    },
    "kind": "central",
}

LOCALIZATION_CRITERIA_ID = "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.LOCAL_ORIGIN_LEVEL"
TECHNICAL_CRITERIA_ID = "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.TECHNICAL_FEATURES"

LEGISLATION = [
    {
        "version": "2024-04-19",
        "type": "NATIONAL_LEGISLATION",
        "identifier": {
            "uri": "https://zakon.rada.gov.ua/laws/show/922-19#Text",
            "id": "922-VIII",
            "legalName": 'Закон України "Про публічні закупівлі"',
        },
        "article": "22.2.3",
    }
]

LOCALIZATION_LEGISLATION = [
    {
        "version": "2021-12-16",
        "type": "NATIONAL_LEGISLATION",
        "article": "1.4.1",
        "identifier": {
            "uri": "https://zakon.rada.gov.ua/laws/show/1977-20",
            "id": "1977-IX",
            "legalName": 'Про внесення змін до Закону України "Про публічні закупівлі" '
            "щодо створення передумов для сталого розвитку та модернізації вітчизняної промисловості",
        },
    }
]


def now_iso():
    return datetime.now(TZ).isoformat()


def make_rev():
    return f"2-{uuid4().hex}"


def make_ean13():
    digits = [random.randint(0, 9) for _ in range(12)]
    checksum = (10 - sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits)) % 10) % 10
    digits.append(checksum)
    return "".join(str(d) for d in digits)


def make_localization_criterion():
    return {
        "title": "Створення передумов для сталого розвитку та модернізації вітчизняної промисловості",
        "description": "Ступінь локалізації виробництва",
        "classification": {"scheme": "ESPD211", "id": LOCALIZATION_CRITERIA_ID},
        "legislation": LOCALIZATION_LEGISLATION,
        "source": "tenderer",
        "id": uuid4().hex,
        "requirementGroups": [
            {
                "description": "Підтверджується наявність складових вітчизняного виробництва",
                "id": uuid4().hex,
                "requirements": [
                    {
                        "title": "Ступінь локалізації виробництва товару",
                        "dataType": "number",
                        "minValue": 25.0,
                        "unit": {"name": "відсоток", "code": "P1", "currency": "UAH", "valueAddedTaxIncluded": False},
                        "isArchived": False,
                        "id": uuid4().hex,
                    }
                ],
            },
            {
                "description": "За відсутності складових вітчизняного виробництва",
                "id": uuid4().hex,
                "requirements": [
                    {
                        "title": "Країна походження товару",
                        "dataSchema": "ISO 3166-1 alpha-2",
                        "dataType": "string",
                        "expectedMinItems": 1,
                        "expectedValues": [
                            "AM",
                            "AU",
                            "CA",
                            "AT",
                            "BE",
                            "BG",
                            "HR",
                            "CY",
                            "EE",
                            "CZ",
                            "DK",
                            "FI",
                            "FR",
                            "GR",
                            "ES",
                            "NL",
                            "IE",
                            "LT",
                            "LU",
                            "LV",
                            "MT",
                            "DE",
                            "PL",
                            "PT",
                            "RO",
                            "SK",
                            "SI",
                            "SE",
                            "HU",
                            "IT",
                            "IL",
                            "MD",
                            "ME",
                            "HK",
                            "IS",
                            "JP",
                            "KR",
                            "LI",
                            "NZ",
                            "NO",
                            "SG",
                            "CH",
                            "TW",
                            "GB",
                            "US",
                        ],
                        "isArchived": False,
                        "id": uuid4().hex,
                    }
                ],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Category 1: Папір офісний
# ---------------------------------------------------------------------------
PAPER_REQUIREMENTS = [
    {
        "title": "Формат",
        "dataType": "string",
        "expectedValues": ["A4", "A3", "A5"],
        "expectedMinItems": 1,
        "expectedMaxItems": 1,
    },
    {
        "title": "Щільність",
        "dataType": "integer",
        "minValue": 60,
        "maxValue": 300,
        "unit": {"code": "GM", "name": "грам на квадратний метр", "currency": "UAH", "valueAddedTaxIncluded": False},
    },
    {
        "title": "Білизна",
        "dataType": "integer",
        "minValue": 80,
        "maxValue": 175,
        "unit": {"code": "P1", "name": "відсоток", "currency": "UAH", "valueAddedTaxIncluded": False},
    },
    {
        "title": "Виробник",
        "dataType": "string",
        "expectedValues": [
            "Mondi",
            "Navigator",
            "Xerox",
            "HP",
            "Double A",
            "Maestro",
            "IQ",
            "Svetocopy",
            "Ballet",
            "Zoom",
        ],
        "expectedMinItems": 1,
        "expectedMaxItems": 1,
    },
    {
        "title": "Кількість аркушів в пачці",
        "dataType": "integer",
        "minValue": 100,
        "maxValue": 1000,
        "unit": {"code": "ST", "name": "аркуш", "currency": "UAH", "valueAddedTaxIncluded": False},
    },
    {
        "title": "Клас якості",
        "dataType": "string",
        "expectedValues": ["A", "B", "C"],
        "expectedMinItems": 1,
        "expectedMaxItems": 1,
    },
]

PAPER_BRANDS_PRODUCTS = [
    ("Mondi", "Папір офісний Mondi IQ Economy A4 80г/м² 500 арк.", 80, 146, 500, "C"),
    ("Mondi", "Папір офісний Mondi IQ Allround A4 80г/м² 500 арк.", 80, 162, 500, "B"),
    ("Mondi", "Папір офісний Mondi Color Copy A4 100г/м² 500 арк.", 100, 170, 500, "A"),
    ("Mondi", "Папір офісний Mondi IQ Premium A3 80г/м² 500 арк.", 80, 169, 500, "A"),
    ("Navigator", "Папір офісний Navigator Universal A4 80г/м² 500 арк.", 80, 169, 500, "A"),
    ("Navigator", "Папір офісний Navigator Eco-Logical A4 75г/м² 500 арк.", 75, 150, 500, "B"),
    ("Navigator", "Папір офісний Navigator Expression A4 90г/м² 500 арк.", 90, 169, 500, "A"),
    ("Xerox", "Папір офісний Xerox Performer A4 80г/м² 500 арк.", 80, 146, 500, "C"),
    ("Xerox", "Папір офісний Xerox Business A4 80г/м² 500 арк.", 80, 164, 500, "B"),
    ("Xerox", "Папір офісний Xerox Premier A4 80г/м² 500 арк.", 80, 170, 500, "A"),
    ("Xerox", "Папір офісний Xerox Performer A3 80г/м² 500 арк.", 80, 146, 500, "C"),
    ("HP", "Папір офісний HP Home & Office A4 80г/м² 500 арк.", 80, 146, 500, "C"),
    ("HP", "Папір офісний HP Premium A4 80г/м² 500 арк.", 80, 170, 500, "A"),
    ("HP", "Папір офісний HP Copy A4 80г/м² 500 арк.", 80, 146, 500, "C"),
    ("Double A", "Папір офісний Double A Premium A4 80г/м² 500 арк.", 80, 175, 500, "A"),
    ("Double A", "Папір офісний Double A A4 70г/м² 500 арк.", 70, 162, 500, "B"),
    ("Maestro", "Папір офісний Maestro Standard A4 80г/м² 500 арк.", 80, 146, 500, "C"),
    ("Maestro", "Папір офісний Maestro Extra A4 80г/м² 500 арк.", 80, 169, 500, "A"),
    ("IQ", "Папір офісний IQ Economy A4 80г/м² 500 арк.", 80, 146, 500, "C"),
    ("Svetocopy", "Папір офісний Svetocopy A4 80г/м² 500 арк.", 80, 146, 500, "C"),
    ("Ballet", "Папір офісний Ballet Brilliant A4 80г/м² 500 арк.", 80, 168, 500, "A"),
    ("Zoom", "Папір офісний Zoom A4 80г/м² 500 арк.", 80, 146, 500, "C"),
    ("Mondi", "Папір офісний Mondi IQ Economy A4 80г/м² 250 арк.", 80, 146, 250, "C"),
    ("Navigator", "Папір офісний Navigator Presentation A4 100г/м² 250 арк.", 100, 170, 250, "A"),
    ("Xerox", "Папір офісний Xerox Colotech+ A4 120г/м² 250 арк.", 120, 170, 250, "A"),
    ("Mondi", "Папір офісний Mondi IQ Allround A5 80г/м² 500 арк.", 80, 162, 500, "B"),
    ("HP", "Папір офісний HP Printing A4 80г/м² 500 арк.", 80, 161, 500, "B"),
    ("Xerox", "Папір офісний Xerox Colotech+ A3 100г/м² 500 арк.", 100, 170, 500, "A"),
    ("Double A", "Папір офісний Double A Everyday A4 70г/м² 500 арк.", 70, 150, 500, "B"),
    ("Navigator", "Папір офісний Navigator Office Card A4 160г/м² 250 арк.", 160, 170, 250, "A"),
    ("Mondi", "Папір офісний Mondi Color Copy A3 200г/м² 250 арк.", 200, 170, 250, "A"),
    ("Ballet", "Папір офісний Ballet Classic A4 80г/м² 500 арк.", 80, 153, 500, "B"),
    ("Zoom", "Папір офісний Zoom Extra A4 80г/м² 500 арк.", 80, 160, 500, "B"),
    ("IQ", "Папір офісний IQ Allround A4 80г/м² 500 арк.", 80, 162, 500, "B"),
    ("Mondi", "Папір офісний Mondi IQ Smart A4 90г/м² 500 арк.", 90, 165, 500, "B"),
    ("Mondi", "Папір офісний Mondi Color Copy SRA3 90г/м² 500 арк.", 90, 170, 500, "A"),
    ("Mondi", "Папір офісний Mondi IQ Economy+ A4 80г/м² 500 арк.", 80, 155, 500, "B"),
    ("Navigator", "Папір офісний Navigator Home Pack A4 80г/м² 500 арк.", 80, 161, 500, "B"),
    ("Navigator", "Папір офісний Navigator Premium A4 90г/м² 500 арк.", 90, 170, 500, "A"),
    ("Xerox", "Папір офісний Xerox Recycled+ A4 80г/м² 500 арк.", 80, 140, 500, "C"),
    ("HP", "Папір офісний HP Office A4 80г/м² 500 арк.", 80, 161, 500, "B"),
    ("HP", "Папір офісний HP Premium+ A4 90г/м² 300 арк.", 90, 170, 300, "A"),
    ("Double A", "Папір офісний Double A Premium A3 80г/м² 500 арк.", 80, 175, 500, "A"),
    ("Ballet", "Папір офісний Ballet Universal A4 75г/м² 500 арк.", 75, 146, 500, "C"),
    ("Zoom", "Папір офісний Zoom A4 80г/м² 250 арк.", 80, 146, 250, "C"),
    ("Svetocopy", "Папір офісний Svetocopy ECO A4 80г/м² 500 арк.", 80, 140, 500, "C"),
    ("Maestro", "Папір офісний Maestro Universal A4 80г/м² 500 арк.", 80, 155, 500, "B"),
    ("Rey", "Папір офісний Rey Office A4 80г/м² 500 арк.", 80, 161, 500, "B"),
    ("Rey", "Папір офісний Rey Text & Graphics A4 90г/м² 500 арк.", 90, 170, 500, "A"),
    ("Svetocopy", "Папір офісний Svetocopy Classic A4 70г/м² 500 арк.", 70, 140, 500, "C"),
]


# ---------------------------------------------------------------------------
# Category 2: Канцелярське приладдя
# ---------------------------------------------------------------------------
STATIONERY_REQUIREMENTS = [
    {
        "title": "Тип",
        "dataType": "string",
        "expectedValues": [
            "ручка кулькова",
            "ручка гелева",
            "ручка-ролер",
            "олівець простий",
            "олівець механічний",
            "маркер перманентний",
            "маркер для дошки",
            "текстовий маркер",
        ],
        "expectedMinItems": 1,
        "expectedMaxItems": 1,
    },
    {
        "title": "Колір чорнила",
        "dataType": "string",
        "expectedValues": [
            "чорний",
            "синій",
            "червоний",
            "зелений",
            "фіолетовий",
            "жовтий",
            "помаранчевий",
            "рожевий",
        ],
        "expectedMinItems": 1,
        "expectedMaxItems": 1,
    },
    {
        "title": "Товщина лінії",
        "dataType": "number",
        "minValue": 0.2,
        "maxValue": 5.0,
        "unit": {"code": "MMT", "name": "міліметр", "currency": "UAH", "valueAddedTaxIncluded": False},
    },
    {
        "title": "Наявність ґумового грипа",
        "dataType": "boolean",
    },
]

STATIONERY_PRODUCTS = [
    ("Ручка кулькова BIC Cristal Original 0.4 мм синя", "ручка кулькова", "синій", 0.4, True),
    ("Ручка кулькова BIC Cristal Original 0.4 мм чорна", "ручка кулькова", "чорний", 0.4, True),
    ("Ручка кулькова BIC Orange Fine 0.3 мм синя", "ручка кулькова", "синій", 0.3, False),
    ("Ручка кулькова Pilot BPS-GP Fine 0.7 мм синя", "ручка кулькова", "синій", 0.7, True),
    ("Ручка кулькова Pilot BPS-GP Fine 0.7 мм чорна", "ручка кулькова", "чорний", 0.7, True),
    ("Ручка кулькова Uni Lakubo SG-100 0.5 мм синя", "ручка кулькова", "синій", 0.5, True),
    ("Ручка кулькова Economix Standard 0.5 мм синя", "ручка кулькова", "синій", 0.5, False),
    ("Ручка кулькова Economix Standard 0.5 мм червона", "ручка кулькова", "червоний", 0.5, False),
    ("Ручка гелева Pilot G-2 0.5 мм чорна", "ручка гелева", "чорний", 0.5, True),
    ("Ручка гелева Pilot G-2 0.5 мм синя", "ручка гелева", "синій", 0.5, True),
    ("Ручка гелева Pilot G-1 0.5 мм червона", "ручка гелева", "червоний", 0.5, True),
    ("Ручка гелева Uni Signo UM-120 0.7 мм синя", "ручка гелева", "синій", 0.7, True),
    ("Ручка гелева Pentel EnerGel 0.5 мм чорна", "ручка гелева", "чорний", 0.5, True),
    ("Ручка-ролер Schneider Topball 845 0.3 мм чорна", "ручка-ролер", "чорний", 0.3, True),
    ("Ручка-ролер Schneider Topball 845 0.3 мм синя", "ручка-ролер", "синій", 0.3, True),
    ("Ручка-ролер Uni-Ball Eye UB-150 0.5 мм синя", "ручка-ролер", "синій", 0.5, False),
    ("Олівець простий Koh-I-Noor 1500 HB", "олівець простий", "чорний", 0.5, False),
    ("Олівець простий Faber-Castell 1111 HB", "олівець простий", "чорний", 0.5, False),
    ("Олівець простий Staedtler Norica 132 HB", "олівець простий", "чорний", 0.5, False),
    ("Олівець механічний Pilot H-185 0.5 мм", "олівець механічний", "чорний", 0.5, True),
    ("Олівець механічний Pentel P205 0.5 мм", "олівець механічний", "чорний", 0.5, True),
    ("Олівець механічний Rotring Tikky 0.5 мм", "олівець механічний", "чорний", 0.5, True),
    ("Маркер перманентний Edding 300 1.5 мм чорний", "маркер перманентний", "чорний", 1.5, False),
    ("Маркер перманентний Edding 300 1.5 мм синій", "маркер перманентний", "синій", 1.5, False),
    ("Маркер перманентний Edding 300 1.5 мм червоний", "маркер перманентний", "червоний", 1.5, False),
    ("Маркер для дошки Kores XW2 3 мм чорний", "маркер для дошки", "чорний", 3.0, False),
    ("Маркер для дошки Kores XW2 3 мм синій", "маркер для дошки", "синій", 3.0, False),
    ("Маркер для дошки Kores XW2 3 мм червоний", "маркер для дошки", "червоний", 3.0, False),
    ("Маркер для дошки Kores XW2 3 мм зелений", "маркер для дошки", "зелений", 3.0, False),
    ("Текстовий маркер Stabilo Boss Original жовтий", "текстовий маркер", "жовтий", 5.0, False),
    ("Текстовий маркер Stabilo Boss Original зелений", "текстовий маркер", "зелений", 5.0, False),
    ("Текстовий маркер Stabilo Boss Original помаранчевий", "текстовий маркер", "помаранчевий", 5.0, False),
    ("Текстовий маркер Stabilo Boss Original рожевий", "текстовий маркер", "рожевий", 5.0, False),
    ("Текстовий маркер Centropen 8552 жовтий", "текстовий маркер", "жовтий", 4.6, False),
    ("Ручка кулькова BIC Cristal Up 0.4 мм синя", "ручка кулькова", "синій", 0.4, False),
    ("Ручка кулькова Schneider Slider Edge 0.7 мм синя", "ручка кулькова", "синій", 0.7, True),
    ("Ручка кулькова Schneider Slider Edge 0.7 мм чорна", "ручка кулькова", "чорний", 0.7, True),
    ("Ручка кулькова Zebra Z-1 0.7 мм синя", "ручка кулькова", "синій", 0.7, False),
    ("Ручка гелева Pilot G-2 0.7 мм синя", "ручка гелева", "синій", 0.7, True),
    ("Ручка гелева Pilot G-2 0.7 мм червона", "ручка гелева", "червоний", 0.7, True),
    ("Ручка гелева Pentel EnerGel 0.7 мм синя", "ручка гелева", "синій", 0.7, True),
    ("Ручка гелева Uni Signo UM-120 0.5 мм чорна", "ручка гелева", "чорний", 0.5, True),
    ("Ручка-ролер Uni-Ball Eye UB-157 0.7 мм чорна", "ручка-ролер", "чорний", 0.7, False),
    ("Ручка-ролер Pilot Hi-Tecpoint V5 0.5 мм синя", "ручка-ролер", "синій", 0.5, False),
    ("Олівець простий Koh-I-Noor 1500 2B", "олівець простий", "чорний", 0.7, False),
    ("Олівець механічний Staedtler 925 0.5 мм", "олівець механічний", "чорний", 0.5, True),
    ("Маркер перманентний Staedtler Lumocolor 317 1 мм чорний", "маркер перманентний", "чорний", 1.0, False),
    ("Маркер для дошки Staedtler Lumocolor 341 2 мм чорний", "маркер для дошки", "чорний", 2.0, False),
    ("Текстовий маркер Stabilo Boss Original блакитний", "текстовий маркер", "синій", 5.0, False),
    ("Текстовий маркер Schneider Job 1 мм жовтий", "текстовий маркер", "жовтий", 1.0, False),
]


# ---------------------------------------------------------------------------
# Category 3: Картриджі для принтерів
# ---------------------------------------------------------------------------
CARTRIDGE_REQUIREMENTS = [
    {
        "title": "Тип друку",
        "dataType": "string",
        "expectedValues": ["лазерний", "струменевий"],
        "expectedMinItems": 1,
        "expectedMaxItems": 1,
    },
    {
        "title": "Колір",
        "dataType": "string",
        "expectedValues": ["чорний", "блакитний", "пурпуровий", "жовтий"],
        "expectedMinItems": 1,
        "expectedMaxItems": 1,
    },
    {
        "title": "Ресурс друку",
        "dataType": "integer",
        "minValue": 100,
        "maxValue": 50000,
        "unit": {"code": "ST", "name": "аркуш", "currency": "UAH", "valueAddedTaxIncluded": False},
    },
    {
        "title": "Сумісність з оригінальним картриджем",
        "dataType": "boolean",
        "expectedValue": True,
    },
]

CARTRIDGE_PRODUCTS = [
    ("Картридж HP CF217A (17A) для HP LaserJet Pro M102/M130", "лазерний", "чорний", 1600),
    ("Картридж HP CF226A (26A) для HP LaserJet Pro M402/M426", "лазерний", "чорний", 3100),
    ("Картридж HP CF226X (26X) для HP LaserJet Pro M402/M426", "лазерний", "чорний", 9000),
    ("Картридж HP CE285A (85A) для HP LaserJet P1102", "лазерний", "чорний", 1600),
    ("Картридж HP CE278A (78A) для HP LaserJet P1566/P1606", "лазерний", "чорний", 2100),
    ("Картридж HP CF283A (83A) для HP LaserJet Pro M125/M127", "лазерний", "чорний", 1500),
    ("Картридж HP W2070A (117A) чорний для HP Color Laser 150", "лазерний", "чорний", 1000),
    ("Картридж HP W2071A (117A) блакитний для HP Color Laser 150", "лазерний", "блакитний", 700),
    ("Картридж HP W2072A (117A) жовтий для HP Color Laser 150", "лазерний", "жовтий", 700),
    ("Картридж HP W2073A (117A) пурпуровий для HP Color Laser 150", "лазерний", "пурпуровий", 700),
    ("Картридж Canon 725 для Canon LBP6000/LBP6020/MF3010", "лазерний", "чорний", 1600),
    ("Картридж Canon 728 для Canon MF4410/MF4430/MF4450", "лазерний", "чорний", 2100),
    ("Картридж Canon 737 для Canon MF211/MF212w/MF216n", "лазерний", "чорний", 2400),
    ("Картридж Canon 054 Black для Canon LBP621/LBP623/MF641", "лазерний", "чорний", 1500),
    ("Картридж Canon 054 Cyan для Canon LBP621/LBP623/MF641", "лазерний", "блакитний", 1200),
    ("Картридж Canon 054 Yellow для Canon LBP621/LBP623/MF641", "лазерний", "жовтий", 1200),
    ("Картридж Canon 054 Magenta для Canon LBP621/LBP623/MF641", "лазерний", "пурпуровий", 1200),
    ("Картридж Samsung MLT-D111S для Samsung Xpress M2020/M2070", "лазерний", "чорний", 1000),
    ("Картридж Samsung MLT-D111L для Samsung Xpress M2020/M2070", "лазерний", "чорний", 1800),
    ("Картридж Brother TN-2375 для Brother HL-L2300D/DCP-L2500D", "лазерний", "чорний", 2600),
    ("Картридж Brother TN-2335 для Brother HL-L2300D/DCP-L2500D", "лазерний", "чорний", 1200),
    ("Картридж Xerox 106R02773 для Xerox Phaser 3020/WC 3025", "лазерний", "чорний", 1500),
    ("Картридж HP 305 (3YM61AE) чорний для HP DeskJet 2710/2720", "струменевий", "чорний", 120),
    ("Картридж HP 305 (3YM60AE) кольоровий блакитний для HP DeskJet 2710", "струменевий", "блакитний", 100),
    ("Картридж HP 305XL (3YM62AE) чорний для HP DeskJet 2710/2720", "струменевий", "чорний", 240),
    ("Картридж HP 652 (F6V25AE) чорний для HP DeskJet 1115/2135", "струменевий", "чорний", 360),
    ("Картридж Canon PG-445 для Canon PIXMA MG2440/MG2540", "струменевий", "чорний", 180),
    ("Картридж Canon CL-446 блакитний для Canon PIXMA MG2440/MG2540", "струменевий", "блакитний", 180),
    ("Картридж Canon PG-445XL для Canon PIXMA MG2440/MG2540", "струменевий", "чорний", 400),
    ("Картридж Epson T6641 Black для Epson L100/L200/L300", "струменевий", "чорний", 4000),
    ("Картридж Epson T6642 Cyan для Epson L100/L200/L300", "струменевий", "блакитний", 6500),
    ("Картридж Epson T6643 Magenta для Epson L100/L200/L300", "струменевий", "пурпуровий", 6500),
    ("Картридж Epson T6644 Yellow для Epson L100/L200/L300", "струменевий", "жовтий", 6500),
    ("Картридж HP CF230A (30A) для HP LaserJet Pro M203/M227", "лазерний", "чорний", 1600),
    ("Картридж HP CF230X (30X) для HP LaserJet Pro M203/M227", "лазерний", "чорний", 3500),
    ("Картридж HP W1350A (135A) для HP LaserJet M209/M234", "лазерний", "чорний", 1100),
    ("Картридж Canon 052 для Canon LBP212/LBP214/MF421", "лазерний", "чорний", 3100),
    ("Картридж Canon 052H для Canon LBP212/LBP214/MF421", "лазерний", "чорний", 9200),
    ("Картридж Brother TN-1075 для Brother HL-1110/1112", "лазерний", "чорний", 1000),
    ("Картридж Brother TN-2080 для Brother HL-2130/DCP-7055", "лазерний", "чорний", 700),
    ("Картридж Samsung MLT-D205L для Samsung ML-3310/SCX-4833", "лазерний", "чорний", 5000),
    ("Картридж Kyocera TK-1150 для Kyocera M2135dn/M2635dn", "лазерний", "чорний", 3000),
    ("Картридж Kyocera TK-1200 для Kyocera M2235dn/M2735dn", "лазерний", "чорний", 3000),
    ("Картридж HP 303 (T6N99AE) чорний для HP ENVY Photo 6220", "струменевий", "чорний", 200),
    ("Картридж HP 303XL (T6N04AE) чорний для HP ENVY Photo 6220", "струменевий", "чорний", 600),
    ("Картридж HP 123 (F6V16AE) чорний для HP DeskJet 3630", "струменевий", "чорний", 120),
    ("Картридж Canon PG-440 для Canon PIXMA MG2140/MG3140", "струменевий", "чорний", 180),
    ("Картридж Canon CL-441 кольоровий для Canon PIXMA MG2140/MG3140", "струменевий", "блакитний", 180),
    ("Картридж Epson T6641XL Black для Epson L800/L805", "струменевий", "чорний", 7500),
    ("Картридж Canon GI-490 BK для Canon PIXMA G1400/G2400", "струменевий", "чорний", 6000),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_requirements(raw_reqs):
    """Add id and isArchived to each requirement definition."""
    reqs = []
    for r in raw_reqs:
        req = dict(r)
        req["id"] = uuid4().hex
        req["isArchived"] = False
        reqs.append(req)
    return reqs


def build_category(cat_id, title, classification, unit_code, unit_name, raw_requirements):
    requirements = build_requirements(raw_requirements)
    technical_criterion = {
        "title": "Технічні, якісні та кількісні характеристики предмету закупівлі",
        "description": "Характеристики товарів",
        "classification": {"scheme": "ESPD211", "id": TECHNICAL_CRITERIA_ID},
        "legislation": LEGISLATION,
        "source": "tenderer",
        "id": uuid4().hex,
        "requirementGroups": [
            {
                "description": "Підтверджується, що",
                "id": uuid4().hex,
                "requirements": requirements,
            }
        ],
    }
    localization_criterion = make_localization_criterion()

    return {
        "_id": cat_id,
        "_rev": make_rev(),
        "title": title,
        "classification": classification,
        "unit": {"code": unit_code, "name": unit_name, "currency": "UAH", "valueAddedTaxIncluded": False},
        "description": f"Категорія: {title}",
        "status": "active",
        "marketAdministrator": MARKET_ADMINISTRATOR,
        "additionalClassifications": [],
        "images": [],
        "criteria": [technical_criterion, localization_criterion],
        "dateModified": now_iso(),
        "owner": "test_owner",
        "access": {"token": uuid4().hex, "owner": "test_owner"},
        "agreementID": uuid4().hex[:32],
    }


def build_product(title, classification, category_id, requirement_responses):
    ts = now_iso()
    return {
        "_id": uuid4().hex,
        "_rev": make_rev(),
        "title": title,
        "description": title,
        "classification": classification,
        "identifier": {"id": make_ean13(), "scheme": "EAN-13"},
        "status": "active",
        "relatedCategory": category_id,
        "requirementResponses": requirement_responses,
        "marketAdministrator": MARKET_ADMINISTRATOR,
        "dateCreated": ts,
        "dateModified": ts,
        "owner": "test_owner",
    }


def make_paper_responses(category, brand, density, whiteness, sheets, quality_class):
    tech_reqs = category["criteria"][0]["requirementGroups"][0]["requirements"]
    local_reqs = category["criteria"][1]["requirementGroups"][0]["requirements"]
    format_val = "A3" if "A3" in brand or "A3" in str(density) else ("A5" if "A5" in brand else "A4")
    # detect format from product title later, for now pick based on brand param trick
    responses = [
        {"requirement": tech_reqs[0]["title"], "values": [format_val]},
        {"requirement": tech_reqs[1]["title"], "value": density},
        {"requirement": tech_reqs[2]["title"], "value": whiteness},
        {"requirement": tech_reqs[3]["title"], "values": [brand]},
        {"requirement": tech_reqs[4]["title"], "value": sheets},
        {"requirement": tech_reqs[5]["title"], "values": [quality_class]},
        {"requirement": local_reqs[0]["title"], "value": round(random.uniform(25.0, 80.0), 1)},
    ]
    return responses


def make_stationery_responses(category, item_type, color, thickness, has_grip):
    tech_reqs = category["criteria"][0]["requirementGroups"][0]["requirements"]
    local_reqs = category["criteria"][1]["requirementGroups"][0]["requirements"]
    responses = [
        {"requirement": tech_reqs[0]["title"], "values": [item_type]},
        {"requirement": tech_reqs[1]["title"], "values": [color]},
        {"requirement": tech_reqs[2]["title"], "value": thickness},
        {"requirement": tech_reqs[3]["title"], "value": has_grip},
        {"requirement": local_reqs[0]["title"], "value": round(random.uniform(25.0, 70.0), 1)},
    ]
    return responses


def make_cartridge_responses(category, print_type, color, page_yield):
    tech_reqs = category["criteria"][0]["requirementGroups"][0]["requirements"]
    local_reqs = category["criteria"][1]["requirementGroups"][0]["requirements"]
    responses = [
        {"requirement": tech_reqs[0]["title"], "values": [print_type]},
        {"requirement": tech_reqs[1]["title"], "values": [color]},
        {"requirement": tech_reqs[2]["title"], "value": page_yield},
        {"requirement": tech_reqs[3]["title"], "value": True},
        {"requirement": local_reqs[0]["title"], "value": round(random.uniform(25.0, 60.0), 1)},
    ]
    return responses


def detect_format(title):
    if "A3" in title:
        return "A3"
    if "A5" in title:
        return "A5"
    return "A4"
