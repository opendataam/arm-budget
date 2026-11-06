"""Transliteration of Armenian proper names (contract counterparties) to Latin and Cyrillic.

Counterparty names are company and person names, so they are transliterated rather
than translated; the abbreviation of the legal form is translated. The Latin scheme
follows the common Armenian passport / BGN-PCGN practice (ու -> u, initial ե -> ye,
initial ո -> vo, ղ -> gh, ց/ծ -> ts, ջ -> j); the Cyrillic scheme follows the usual
Russian rendering of Armenian names.
"""

from __future__ import annotations

import re

LAT = {
    "ա": "a", "բ": "b", "գ": "g", "դ": "d", "ե": "e", "զ": "z", "է": "e", "ը": "y", "թ": "t", "ժ": "zh",
    "ի": "i", "լ": "l", "խ": "kh", "ծ": "ts", "կ": "k", "հ": "h", "ձ": "dz", "ղ": "gh", "ճ": "ch", "մ": "m",
    "յ": "y", "ն": "n", "շ": "sh", "ո": "o", "չ": "ch", "պ": "p", "ջ": "j", "ռ": "r", "ս": "s", "վ": "v",
    "տ": "t", "ր": "r", "ց": "ts", "ւ": "v", "փ": "p", "ք": "k", "օ": "o", "ֆ": "f", "և": "ev",
}
CYR = {
    "ա": "а", "բ": "б", "գ": "г", "դ": "д", "ե": "е", "զ": "з", "է": "э", "ը": "ы", "թ": "т", "ժ": "ж",
    "ի": "и", "լ": "л", "խ": "х", "ծ": "ц", "կ": "к", "հ": "х", "ձ": "дз", "ղ": "г", "ճ": "ч", "մ": "м",
    "յ": "й", "ն": "н", "շ": "ш", "ո": "о", "չ": "ч", "պ": "п", "ջ": "дж", "ռ": "р", "ս": "с", "վ": "в",
    "տ": "т", "ր": "р", "ց": "ц", "ւ": "в", "փ": "п", "ք": "к", "օ": "о", "ֆ": "ф", "և": "ев",
}
INITIAL = {"lat": {"ե": "ye", "ո": "vo"}, "cyr": {"ե": "е", "ո": "во"}}
DIGRAPH = {"lat": {"ու": "u"}, "cyr": {"յու": "ю", "յա": "я", "ու": "у"}}

# legal forms: Armenian abbreviation -> (en, ru)
LEGAL_FORMS = {
    "ՓԲԸ": ("CJSC", "ЗАО"),
    "ԲԲԸ": ("OJSC", "ОАО"),
    "ՍՊԸ": ("LLC", "ООО"),
    "ԼՊԸ": ("ALC", "ОДО"),
    "ԱՁ": ("IE", "ИП"),
    "ՊՈԱԿ": ("SNCO", "ГНКО"),
    "ՀՈԱԿ": ("CNCO", "ОНКО"),
    "ՊՓԸ": ("SCJSC", "ГЗАО"),
    "ՀԿ": ("NGO", "ОО"),
    "ՀՀ": ("RA", "РА"),
    "ՀԻՄՆԱԴՐԱՄ": ("Foundation", "Фонд"),
}
_WORD = re.compile(r"[Ա-և]+")


def _translit_word(word: str, script: str) -> str:
    table = LAT if script == "lat" else CYR
    upper = word.isupper() and len(word) > 1
    title = word[0].isupper() and not upper
    w = word.lower()
    out = []
    i = 0
    while i < len(w):
        for n in (3, 2):
            chunk = w[i:i + n]
            if len(chunk) == n and chunk in DIGRAPH[script]:
                out.append(DIGRAPH[script][chunk])
                i += n
                break
        else:
            chunk = None
        if chunk is not None:
            continue
        ch = w[i]
        if i == 0 and ch in INITIAL[script]:
            out.append(INITIAL[script][ch])
        else:
            out.append(table.get(ch, ch))
        i += 1
    s = "".join(out)
    if upper:
        return s.upper()
    if title:
        return s[:1].upper() + s[1:]
    return s


def transliterate(text: str | None, script: str = "lat") -> str | None:
    """Transliterate the Armenian letters of ``text``; other characters are kept."""
    if text is None:
        return None
    return _WORD.sub(lambda m: _translit_word(m.group(0), script), text)


def partner_name(name: str | None, lang: str) -> str | None:
    """Counterparty name in ``lang`` ('en' or 'ru'): legal form translated, the rest transliterated.

    The site replaces quotation marks with dashes ('-Հայաստանի էլեկտրական ցանցեր- ՓԲԸ');
    they are restored as quotes.
    """
    if not name:
        return name
    s = name.strip()
    m = re.fullmatch(r"-\s*(.+?)\s*-\s*(.*)", s)
    if m:
        s = f"«{m.group(1)}» {m.group(2)}".strip()
    idx = 0 if lang == "en" else 1
    tokens = re.split(r"(\s+)", s)
    out = []
    for t in tokens:
        core = t.strip("«»\"'().,")
        if core in LEGAL_FORMS:
            out.append(t.replace(core, LEGAL_FORMS[core][idx]))
        else:
            out.append(transliterate(t, "lat" if lang == "en" else "cyr"))
    s = "".join(out)
    if lang == "en":
        s = s.replace("«", '"').replace("»", '"')
    return s
