# Translation glossary (hy → en / ru)

Conventions used in `data/translations/*.csv`. Keep new translations consistent with them.

## File format

* UTF-8 CSV with the columns `hy,en,ru`; standard CSV quoting (`"` doubled inside quoted fields).
* `hy` is the key: the Armenian text exactly as in the source (the build compares it by letters and digits only,
  so punctuation and case differences do not matter, but do not edit it).
* `en` and `ru` must both be filled.
* The Armenian text is authoritative; translations are machine-assisted (LLM) and reviewed for consistency.

## Style

* Translate the meaning; do not transliterate common words. Proper names of people and places are
  transliterated (Yerevan / Ереван, Gyumri / Гюмри, Syunik / Сюник, Vayots Dzor / Вайоц Дзор).
* Use sentence case, even when the Armenian source is in capitals (`ԱՌՈՂՋԱՊԱՀՈՒԹՅՈՒՆ` → `Health` / `Здравоохранение`).
* Keep numbers, years, codes, Latin abbreviations (KfW, IT, EU) and quoted names; quotes in English `"…"`,
  in Russian `«…»`.
* Typos and encoding artefacts of the source (Latin `u` instead of Armenian `ս`, words glued together because
  the source dropped punctuation, truncated endings) are translated by their evident meaning; a truncated
  name stays truncated (`…`).
* Program/measure names are usually noun phrases describing an activity: translate as a noun phrase
  (`… ապահովում` → `Provision of …` / `Обеспечение …`; `… կառուցում` → `Construction of …` / `Строительство …`).

## Terms

| hy | en | ru |
|---|---|---|
| ՀՀ (Հայաստանի Հանրապետություն) | RA (Republic of Armenia) | РА (Республика Армения) |
| ՀՀ կառավարություն | Government of the RA | Правительство РА |
| նախարարություն | Ministry | министерство |
| ՀՀ ֆինանսների նախարարություն | Ministry of Finance of the RA | Министерство финансов РА |
| կոմիտե | Committee | комитет |
| ծառայություն | Service | служба |
| աշխատակազմ | Office (staff) | аппарат |
| ՀՀ վարչապետի աշխատակազմ | Office of the Prime Minister of the RA | Аппарат премьер-министра РА |
| մարզպետի աշխատակազմ | Office of the Governor of … Province | Аппарат губернатора … области |
| մարզ | province (marz) | область (марз) |
| Երևանի քաղաքապետարան | Yerevan Municipality | Мэрия Еревана |
| համայնք | community (municipality) | община |
| հանձնաժողով | Commission | комиссия |
| տեսչական մարմին | Inspection Body | инспекционный орган |
| Այլ մարմիններ | Other bodies | Прочие органы |
| ՊՈԱԿ (պետական ոչ առևտրային կազմակերպություն) | SNCO (state non-commercial organisation) | ГНКО (государственная некоммерческая организация) |
| ՀՈԱԿ | CNCO (community non-commercial organisation) | ОНКО (общинная некоммерческая организация) |
| ՓԲԸ / ԲԲԸ / ՍՊԸ | CJSC / OJSC / LLC | ЗАО / ОАО / ООО |
| ծրագիր | program | программа |
| միջոցառում | measure | мероприятие |
| ծրագրի կառավարում | program management | управление программой |
| դրամաշնորհ | grant | грант |
| սուբսիդիա | subsidy | субсидия |
| տրանսֆերտ | transfer | трансферт |
| նպաստ | benefit (allowance) | пособие |
| կենսաթոշակ | pension | пенсия |
| վարկ / փոխառություն | loan / borrowing | кредит / заимствование |
| պահուստային ֆոնդ | reserve fund | резервный фонд |
| կապիտալ վերանորոգում | capital repair | капитальный ремонт |
| ընթացիկ նորոգում և պահպանում | current repair and maintenance | текущий ремонт и содержание |
| ԱԱՀ (ավելացված արժեքի հարկ) | VAT | НДС |
| ակցիզային հարկ | excise tax | акцизный налог |
| շահութահարկ | profit tax | налог на прибыль |
| եկամտային հարկ | income tax | подоходный налог |
| շրջանառության հարկ | turnover tax | налог с оборота |
| գույքահարկ / հողի հարկ | property tax / land tax | налог на имущество / земельный налог |
| մաքսատուրք | customs duty | таможенная пошлина |
| պետական տուրք | state duty | государственная пошлина |
| բնապահպանական վճար | environmental fee | природоохранный платеж |
| ռոյալթի | royalty | роялти |
| տուգանք / տույժ | fine / penalty | штраф / пеня |
| իրավաբանական անձ / ֆիզիկական անձ | legal person / natural person | юридическое лицо / физическое лицо |
| անհատ ձեռնարկատեր | individual entrepreneur | индивидуальный предприниматель |
| ԵԱՏՄ (Եվրասիական տնտեսական միություն) | EAEU (Eurasian Economic Union) | ЕАЭС (Евразийский экономический союз) |
| ԱՏԳ ԱԱ | CN FEA (Commodity Nomenclature of Foreign Economic Activity) | ТН ВЭД |
| Ազգային ժողով | National Assembly | Национальное Собрание |
| Սահմանադրական դատարան | Constitutional Court | Конституционный суд |
| Դատական դեպարտամենտ | Judicial Department | Судебный департамент |
| Դատախազություն | Prosecutor's Office | Прокуратура |
| Հաշվեքննիչ պալատ | Audit Chamber | Счетная палата |
| Մարդու իրավունքների պաշտպան | Human Rights Defender | Защитник прав человека |
| Կենտրոնական ընտրական հանձնաժողով | Central Electoral Commission | Центральная избирательная комиссия |
| Պետական եկամուտների կոմիտե | State Revenue Committee | Комитет государственных доходов |
| Ազգային անվտանգության ծառայություն | National Security Service | Служба национальной безопасности |
| Քննչական կոմիտե | Investigative Committee | Следственный комитет |
| Վիճակագրական կոմիտե | Statistical Committee | Статистический комитет |
| Կադաստրի կոմիտե | Cadastre Committee | Комитет кадастра |
| Կոռուպցիայի կանխարգելման հանձնաժողով | Corruption Prevention Commission | Комиссия по предотвращению коррупции |

## Functional classification (COFOG)

Section names follow the standard COFOG wording.

| hy | en | ru |
|---|---|---|
| ԸՆԴՀԱՆՈՒՐ ԲՆՈՒՅԹԻ ՀԱՆՐԱՅԻՆ ԾԱՌԱՅՈՒԹՅՈՒՆՆԵՐ | General public services | Общегосударственные услуги |
| ՊԱՇՏՊԱՆՈՒԹՅՈՒՆ | Defence | Оборона |
| ՀԱՍԱՐԱԿԱԿԱՆ ԿԱՐԳ, ԱՆՎՏԱՆԳՈՒԹՅՈՒՆ ԵՎ ԴԱՏԱԿԱՆ ԳՈՐԾՈՒՆԵՈՒԹՅՈՒՆ | Public order, safety and judicial activity | Общественный порядок, безопасность и судебная деятельность |
| ՏՆՏԵՍԱԿԱՆ ՀԱՐԱԲԵՐՈՒԹՅՈՒՆՆԵՐ | Economic affairs | Экономические отношения |
| ՇՐՋԱԿԱ ՄԻՋԱՎԱՅՐԻ ՊԱՇՏՊԱՆՈՒԹՅՈՒՆ | Environmental protection | Охрана окружающей среды |
| ԲՆԱԿԱՐԱՆԱՅԻՆ ՇԻՆԱՐԱՐՈՒԹՅՈՒՆ ԵՎ ԿՈՄՈՒՆԱԼ ԾԱՌԱՅՈՒԹՅՈՒՆՆԵՐ | Housing construction and community amenities | Жилищное строительство и коммунальные услуги |
| ԱՌՈՂՋԱՊԱՀՈՒԹՅՈՒՆ | Health | Здравоохранение |
| ՀԱՆԳԻՍՏ, ՄՇԱԿՈՒՅԹ ԵՎ ԿՐՈՆ | Recreation, culture and religion | Отдых, культура и религия |
| ԿՐԹՈՒԹՅՈՒՆ | Education | Образование |
| ՍՈՑԻԱԼԱԿԱՆ ՊԱՇՏՊԱՆՈՒԹՅՈՒՆ | Social protection | Социальная защита |
| ՀԻՄՆԱԿԱՆ ԲԱԺԻՆՆԵՐԻՆ ՉԴԱՍՎՈՂ ՊԱՀՈՒՍՏԱՅԻՆ ՖՈՆԴԵՐ | Reserve funds not classified under the main sections | Резервные фонды, не отнесенные к основным разделам |
| (այլ դասերին չպատկանող) | (not elsewhere classified) | (не отнесенные к другим категориям) |
