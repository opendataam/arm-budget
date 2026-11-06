"""Static reference data in three languages (hy / en / ru).

Small, stable lists that are not published by the site as data: report titles,
periods, revenue types, the upper levels of the economic classification. The
Armenian names of the economic classification levels are taken from the
guidelines linked from the forms (annexes 16, 17 and 19 to the order of the
Minister of Finance and Economy of 9 January 2007 N 5-Ն, data/raw/documents).
"""

from __future__ import annotations

LANGUAGES = [
    ("hy", "Armenian", "Հայերեն"),
    ("en", "English", "English"),
    ("ru", "Russian", "Русский"),
]

# report -> (title hy, en, ru, fact table)
REPORTS = {
    "expenditure": ("Ծախսեր", "Expenditures", "Расходы", "fact_expenditure"),
    "revenue": ("Եկամուտներ", "Revenues", "Доходы", "fact_revenue"),
    "deficit": ("Դեֆիցիտ", "Deficit (sources of financing)", "Дефицит (источники финансирования)", "fact_deficit"),
}

# period -> (months, sort, hy, en, ru); hy = captions of the plan columns of the site
PERIODS = {
    "q1": (3, 1, "1 եռամս.", "Q1 (January-March)", "I квартал (январь-март)"),
    "h1": (6, 2, "Կիսամ.", "H1 (January-June)", "I полугодие (январь-июнь)"),
    "m9": (9, 3, "9 ամիս", "9 months (January-September)", "9 месяцев (январь-сентябрь)"),
    "year": (12, 4, "Տարի", "Year", "Год"),
}

REVENUE_TYPES = {
    0: ("Եկամուտներ", "All revenues", "Все доходы"),
    1: ("Հարկեր և տուրքեր", "Taxes and duties", "Налоги и пошлины"),
    2: ("Պաշտոնական դրամաշնորհներ", "Official grants", "Официальные гранты"),
    3: ("Այլ եկամուտներ", "Other revenues", "Прочие доходы"),
}

FUNCTIONAL_LEVELS = {2: (1, "section"), 4: (2, "group"), 6: (3, "class")}

# Upper levels of the economic classification of expenditures: code -> (level, hy, en, ru).
# level 1 = class (first digit of the article), 2 = category (2 digits), 3 = group (3 digits).
ECONOMIC_LEVELS = {
    "4": (1, "ԸՆԹԱՑԻԿ ԾԱԽՍԵՐ", "Current expenditures", "Текущие расходы"),
    "5": (1, "ՈՉ ՖԻՆԱՆՍԱԿԱՆ ԱԿՏԻՎՆԵՐԻ ԳԾՈՎ ԾԱԽՍԵՐ", "Expenditures on non-financial assets", "Расходы по нефинансовым активам"),
    "6": (1, "ՈՉ ՖԻՆԱՆՍԱԿԱՆ ԱԿՏԻՎՆԵՐԻ ԻՐԱՑՈՒՄԻՑ ՄՈՒՏՔԵՐ", "Receipts from the sale of non-financial assets",
          "Поступления от реализации нефинансовых активов"),
    "7": (1, "ԱՅԼ", "Other (technical articles)", "Прочее (технические статьи)"),
    "41": (2, "ԱՇԽԱՏԱՆՔԻ ՎԱՐՁԱՏՐՈՒԹՅՈՒՆ", "Compensation of employees", "Оплата труда"),
    "42": (2, "ԾԱՌԱՅՈՒԹՅՈՒՆՆԵՐԻ ԵՎ ԱՊՐԱՆՔՆԵՐԻ ՁԵՌՔԲԵՐՈՒՄ", "Purchase of services and goods", "Приобретение услуг и товаров"),
    "43": (2, "ՀԻՄՆԱԿԱՆ ՄԻՋՈՑՆԵՐԻ ՍՊԱՌՈՒՄ", "Consumption of fixed capital", "Потребление основного капитала"),
    "44": (2, "ՏՈԿՈՍԱՎՃԱՐՆԵՐ", "Interest", "Проценты"),
    "45": (2, "ՍՈՒԲՍԻԴԻԱՆԵՐ", "Subsidies", "Субсидии"),
    "46": (2, "ԴՐԱՄԱՇՆՈՐՀՆԵՐ", "Grants", "Гранты"),
    "47": (2, "ՍՈՑԻԱԼԱԿԱՆ ՆՊԱՍՏՆԵՐ ԵՎ ԿԵՆՍԱԹՈՇԱԿՆԵՐ", "Social benefits and pensions", "Социальные пособия и пенсии"),
    "48": (2, "ԱՅԼ ԾԱԽՍԵՐ", "Other expenditures", "Прочие расходы"),
    "51": (2, "ՀԻՄՆԱԿԱՆ ՄԻՋՈՑՆԵՐ", "Fixed assets", "Основные средства"),
    "52": (2, "ՊԱՇԱՐՆԵՐ", "Inventories", "Запасы"),
    "53": (2, "ԲԱՐՁՐԱՐԺԵՔ ԱԿՏԻՎՆԵՐ", "Valuables", "Ценности"),
    "54": (2, "ՉԱՐՏԱԴՐՎԱԾ ԱԿՏԻՎՆԵՐ", "Non-produced assets", "Непроизведенные активы"),
    "411": (3, "ԴՐԱՄՈՎ ՎՃԱՐՎՈՂ ԱՇԽԱՏԱՎԱՐՁԵՐ ԵՎ ՀԱՎԵԼԱՎՃԱՐՆԵՐ", "Wages and salaries in cash", "Заработная плата и надбавки в денежной форме"),
    "412": (3, "ԲՆԵՂԵՆ ԱՇԽԱՏԱՎԱՐՁԵՐ ԵՎ ՀԱՎԵԼԱՎՃԱՐՆԵՐ", "Wages and salaries in kind", "Заработная плата и надбавки в натуральной форме"),
    "413": (3, "ՓԱՍՏԱՑԻ ՍՈՑԻԱԼԱԿԱՆ ԱՊԱՀՈՎՈՒԹՅԱՆ ՎՃԱՐՆԵՐ", "Actual social contributions", "Фактические отчисления на социальное обеспечение"),
    "421": (3, "ՇԱՐՈՒՆԱԿԱԿԱՆ ԾԱԽՍԵՐ", "Continuous costs (utilities, communications, insurance, rent)",
            "Текущие эксплуатационные расходы (коммунальные услуги, связь, страхование, аренда)"),
    "422": (3, "ԳՈՐԾՈՒՂՈՒՄՆԵՐԻ ԵՎ ՇՐՋԱԳԱՅՈՒԹՅՈՒՆՆԵՐԻ ԾԱԽՍԵՐ", "Business trips and travel", "Командировочные и транспортные расходы"),
    "423": (3, "ՊԱՅՄԱՆԱԳՐԱՅԻՆ ԱՅԼ ԾԱՌԱՅՈՒԹՅՈՒՆՆԵՐԻ ՁԵՌՔԲԵՐՈՒՄ", "Purchase of other contractual services",
            "Приобретение прочих услуг по договорам"),
    "424": (3, "ԱՅԼ ՄԱՍՆԱԳԻՏԱԿԱՆ ԾԱՌԱՅՈՒԹՅՈՒՆՆԵՐԻ ՁԵՌՔԲԵՐՈՒՄ", "Purchase of other specialised services",
            "Приобретение прочих специализированных услуг"),
    "425": (3, "ԸՆԹԱՑԻԿ ՆՈՐՈԳՈՒՄ ԵՎ ՊԱՀՊԱՆՈՒՄ (ԾԱՌԱՅՈՒԹՅՈՒՆՆԵՐ ԵՎ ՆՅՈՒԹԵՐ)",
            "Current repair and maintenance (services and materials)", "Текущий ремонт и содержание (услуги и материалы)"),
    "426": (3, "ՆՅՈՒԹԵՐ (ԱՊՐԱՆՔՆԵՐ)", "Materials (goods)", "Материалы (товары)"),
    "441": (3, "ՆԵՐՔԻՆ ՏՈԿՈՍԱՎՃԱՐՆԵՐ", "Domestic interest", "Внутренние проценты"),
    "442": (3, "ԱՐՏԱՔԻՆ ՏՈԿՈՍԱՎՃԱՐՆԵՐ", "Foreign interest", "Внешние проценты"),
    "443": (3, "ՓՈԽԱՌՈՒԹՅՈՒՆՆԵՐԻ ՀԵՏ ԿԱՊՎԱԾ ՎՃԱՐՆԵՐ", "Payments related to borrowing", "Платежи, связанные с заимствованиями"),
    "451": (3, "ՍՈՒԲՍԻԴԻԱՆԵՐ ՊԵՏԱԿԱՆ ԿԱԶՄԱԿԵՐՊՈՒԹՅՈՒՆՆԵՐԻՆ", "Subsidies to public corporations", "Субсидии государственным организациям"),
    "452": (3, "ՍՈՒԲՍԻԴԻԱՆԵՐ ՈՉ ՊԵՏԱԿԱՆ ԿԱԶՄԱԿԵՐՊՈՒԹՅՈՒՆՆԵՐԻՆ", "Subsidies to non-state organisations", "Субсидии негосударственным организациям"),
    "461": (3, "ԴՐԱՄԱՇՆՈՐՀՆԵՐ ՕՏԱՐԵՐԿՐՅԱ ԿԱՌԱՎԱՐՈՒԹՅՈՒՆՆԵՐԻՆ", "Grants to foreign governments", "Гранты иностранным правительствам"),
    "462": (3, "ԴՐԱՄԱՇՆՈՐՀՆԵՐ ՄԻՋԱԶԳԱՅԻՆ ԿԱԶՄԱԿԵՐՊՈՒԹՅՈՒՆՆԵՐԻՆ", "Grants to international organisations", "Гранты международным организациям"),
    "463": (3, "ԸՆԹԱՑԻԿ ԴՐԱՄԱՇՆՈՐՀՆԵՐ ՊԵՏԱԿԱՆ ՀԱՏՎԱԾԻ ԱՅԼ ՄԱԿԱՐԴԱԿՆԵՐԻՆ", "Current grants to other levels of general government",
            "Текущие гранты другим уровням государственного сектора"),
    "465": (3, "ԿԱՊԻՏԱԼ ԴՐԱՄԱՇՆՈՐՀՆԵՐ ՊԵՏԱԿԱՆ ՀԱՏՎԱԾԻ ԱՅԼ ՄԱԿԱՐԴԱԿՆԵՐԻՆ", "Capital grants to other levels of general government",
            "Капитальные гранты другим уровням государственного сектора"),
    "471": (3, "ՍՈՑԻԱԼԱԿԱՆ ԱՊԱՀՈՎՈՒԹՅԱՆ ՆՊԱՍՏՆԵՐ", "Social security benefits", "Пособия по социальному обеспечению"),
    "472": (3, "ՍՈՑԻԱԼԱԿԱՆ ՕԳՆՈՒԹՅԱՆ ԴՐԱՄԱԿԱՆ ԱՐՏԱՀԱՅՏՈՒԹՅԱՄԲ ՆՊԱՍՏՆԵՐ (ԲՅՈՒՋԵԻՑ)", "Social assistance benefits in cash (from the budget)",
            "Пособия по социальной помощи в денежной форме (из бюджета)"),
    "474": (3, "ԿԵՆՍԱԹՈՇԱԿՆԵՐ", "Pensions", "Пенсии"),
    "475": (3, "ՍՈՑԻԱԼԱԿԱՆ ԱՊԱՀՈՎՈՒԹՅԱՆ ՄԻՋՈՑԱՌՈՒՄՆԵՐԻ ԻՐԱԿԱՆԱՑՄԱՆ ՆՊԱՏԱԿՈՎ ԱՇԽԱՏՈՂՆԵՐԻՆ ՍՈՑԻԱԼԱԿԱՆ ՓԱԹԵԹՈՎ ԱՊԱՀՈՎՈՒՄ",
            "Social package for employees (social security measures)", "Обеспечение работников социальным пакетом (меры социального обеспечения)"),
    "481": (3, "ՆՎԻՐԱՏՎՈՒԹՅՈՒՆՆԵՐ ՈՉ ԿԱՌԱՎԱՐՉԱԿԱՆ (ՀԱՍԱՐԱԿԱԿԱՆ) ԿԱԶՄԱԿԵՐՊՈՒԹՅՈՒՆՆԵՐԻՆ", "Donations to non-governmental (public) organisations",
            "Пожертвования неправительственным (общественным) организациям"),
    "482": (3, "ՀԱՐԿԵՐ, ՊԱՐՏԱԴԻՐ ՎՃԱՐՆԵՐ ԵՎ ՏՈՒՅԺԵՐ, ՈՐՈՆՔ ԿԱՌԱՎԱՐՄԱՆ ՏԱՐԲԵՐ ՄԱԿԱՐԴԱԿՆԵՐԻ ԿՈՂՄԻՑ ԿԻՐԱՌՎՈՒՄ ԵՆ ՄԻՄՅԱՆՑ ՆԿԱՏՄԱՄԲ",
            "Taxes, compulsory fees and penalties imposed by one level of government on another",
            "Налоги, обязательные платежи и штрафы, применяемые разными уровнями управления друг к другу"),
    "483": (3, "ԴԱՏԱՐԱՆՆԵՐԻ ԿՈՂՄԻՑ ՆՇԱՆԱԿՎԱԾ ՏՈՒՅԺԵՐ ԵՎ ՏՈՒԳԱՆՔՆԵՐ", "Penalties and fines imposed by courts", "Пени и штрафы, назначенные судами"),
    "484": (3, "ԲՆԱԿԱՆ ԱՂԵՏՆԵՐԻՑ ԿԱՄ ԱՅԼ ԲՆԱԿԱՆ ՊԱՏՃԱՌՆԵՐՈՎ ԱՌԱՋԱՑԱԾ ՎՆԱՍՆԵՐԻ ԿԱՄ ՎՆԱՍՎԱԾՔՆԵՐԻ ՎԵՐԱԿԱՆԳՆՈՒՄ",
            "Restoration of damage caused by natural disasters or other natural causes",
            "Восстановление ущерба от стихийных бедствий и других природных причин"),
    "485": (3, "ԿԱՌԱՎԱՐՄԱՆ ՄԱՐՄԻՆՆԵՐԻ ԳՈՐԾՈՒՆԵՈՒԹՅԱՆ ՀԵՏԵՎԱՆՔՈՎ ԱՌԱՋԱՑԱԾ ՎՆԱՍՆԵՐԻ ԿԱՄ ՎՆԱՍՎԱԾՔՆԵՐԻ ՎԵՐԱԿԱՆԳՆՈՒՄ",
            "Restoration of damage caused by the activities of government bodies",
            "Возмещение ущерба, причиненного деятельностью органов управления"),
    "486": (3, "ԱՅԼ ԾԱԽՍԵՐ", "Other expenditures", "Прочие расходы"),
    "489": (3, "ՊԱՀՈՒՍՏԱՅԻՆ ՄԻՋՈՑՆԵՐ (ՖՈՆԴ)", "Reserve funds", "Резервные средства (фонд)"),
    "511": (3, "ՇԵՆՔԵՐ ԵՎ ՇԻՆՈՒԹՅՈՒՆՆԵՐ", "Buildings and structures", "Здания и сооружения"),
    "512": (3, "ՄԵՔԵՆԱՆԵՐ ԵՎ ՍԱՐՔԱՎՈՐՈՒՄՆԵՐ", "Machinery and equipment", "Машины и оборудование"),
    "513": (3, "ԱՅԼ ՀԻՄՆԱԿԱՆ ՄԻՋՈՑՆԵՐ", "Other fixed assets", "Прочие основные средства"),
    "521": (3, "ՌԱԶՄԱՎԱՐԱԿԱՆ ՊԱՇԱՐՆԵՐ", "Strategic stocks", "Стратегические запасы"),
    "522": (3, "ԱՐՏԱԴՐԱԿԱՆ ՊԱՇԱՐՆԵՐ", "Production stocks", "Производственные запасы"),
    "523": (3, "ՎԵՐԱՎԱՃԱՌՔԻ ՀԱՄԱՐ ՆԱԽԱՏԵՍՎԱԾ ԱՊՐԱՆՔՆԵՐ", "Goods for resale", "Товары для перепродажи"),
    "524": (3, "ՍՊԱՌՄԱՆ ՆՊԱՏԱԿՈՎ ՊԱՀՎՈՂ ՊԱՇԱՐՆԵՐ", "Stocks held for consumption", "Запасы для потребления"),
    "541": (3, "ՀՈՂ", "Land", "Земля"),
    "542": (3, "ԸՆԴԵՐՔԱՅԻՆ ԱԿՏԻՎՆԵՐ", "Subsoil assets", "Активы недр"),
    "543": (3, "ԱՅԼ ԲՆԱԿԱՆ ԾԱԳՈՒՄ ՈՒՆԵՑՈՂ ԱԿՏԻՎՆԵՐ", "Other naturally occurring assets", "Прочие активы природного происхождения"),
    "544": (3, "ՈՉ ՆՅՈՒԹԱԿԱՆ ՉԱՐՏԱԴՐՎԱԾ ԱԿՏԻՎՆԵՐ", "Intangible non-produced assets", "Нематериальные непроизведенные активы"),
}
ECONOMIC_LEVEL_NAMES = {1: "class", 2: "category", 3: "group"}

# dimension key -> (dimension table, translation context)
DIMS = {
    "func_section": ("dim_functional", "functional"),
    "func_group": ("dim_functional", "functional"),
    "func_class": ("dim_functional", "functional"),
    "program": ("dim_program", "program"),
    "department": ("dim_department", "department"),
    "economic": ("dim_economic", "economic"),
    "rev_section": ("dim_revenue_section", "revenue"),
    "rev_group": ("dim_revenue_group", "revenue"),
    "rev_account": ("dim_revenue_account", "revenue"),
}

# Documents linked from the forms: file -> (en, ru) titles
DOCUMENTS = {
    "16.pdf": (("Guidelines on the application of the classification: current expenditures (class 400000). "
               "Annex 16 to the order of the Minister of Finance and Economy of 9 January 2007 N 5-N"),
               ("Указания по применению классификации: текущие расходы (класс 400000). "
               "Приложение 16 к приказу министра финансов и экономики от 9 января 2007 г. N 5-Н")),
    "17.pdf": (("Guidelines on the application of the classification: expenditures on non-financial assets (class 500000). "
               "Annex 17 to the order of the Minister of Finance and Economy of 9 January 2007 N 5-N"),
               ("Указания по применению классификации: расходы по нефинансовым активам (класс 500000). "
               "Приложение 17 к приказу министра финансов и экономики от 9 января 2007 г. N 5-Н")),
    "19.pdf": (("Guidelines on the application of the classification: current revenues (class 700000). "
               "Annex 19 to the order of the Minister of Finance and Economy of 9 January 2007 N 5-N"),
               ("Указания по применению классификации: текущие доходы (класс 700000). "
               "Приложение 19 к приказу министра финансов и экономики от 9 января 2007 г. N 5-Н")),
}
