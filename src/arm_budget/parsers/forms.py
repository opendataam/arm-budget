"""Parser of the report form pages (param.php) and of the start page."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from .common import clean_label, parse_number

_SELECT = re.compile(r"<select\s+id=(\w+)\s+name=(\w+)[^>]*>(.*?)</select>", re.DOTALL | re.IGNORECASE)
_OPTION = re.compile(r'<option\s+value="([^"]*)"\s*(selected)?\s*>([^<]*)</option>', re.IGNORECASE)
_CHECKBOX = re.compile(r'<input type="checkbox" name="([^"\[]+)\[\]" value="([^"]*)"\s*(checked)?\s*/?>([^<]*)', re.IGNORECASE)
_BUTTON = re.compile(r'data-target="#(\w+)"[^>]*>([^<]*)</button>', re.IGNORECASE)
_LABEL = re.compile(r'<label class="formLeftBlock">([^<]*)</label>\s*<div class="formRightBlock"><select id=(\w+)', re.IGNORECASE)
_DOC_LINK = re.compile(r'<a href="(xml[\\/][^"]+\.pdf)">([^<]*)</a>', re.IGNORECASE)
_NAV = re.compile(r'<a href="#" class="active">([^<]*)</a>')
_POPUP = re.compile(r"PopupDoc\('(\w+)'")
_SIDEBAR = re.compile(r"\{\s*id:\s*'(site_\w+)\.0',\s*text:\s*'([^']*)'")


@dataclass
class Option:
    value: str
    label: str
    selected: bool = False


@dataclass
class FormPage:
    page: str | None
    title: str | None                                      # e.g. 'Ծախսեր  3,752,208,931.30'
    selects: dict[str, list[Option]] = field(default_factory=dict)
    select_labels: dict[str, str] = field(default_factory=dict)  # select id -> label shown on the left
    lists: dict[str, list[Option]] = field(default_factory=dict)  # checkbox lists, without the '-' (all) entry
    list_titles: dict[str, str] = field(default_factory=dict)     # list name -> button caption
    documents: list[tuple[str, str]] = field(default_factory=list)  # (relative url, title)
    result_popup: str | None = None                         # Popup.php page of the "get result" button

    def selected(self, select_id: str) -> str | None:
        for o in self.selects.get(select_id, []):
            if o.selected:
                return o.value
        return None

    def year_options(self) -> dict[int, int]:
        """SITE_YEAR option value -> calendar year."""
        return {int(o.value): int(o.label) for o in self.selects.get("SITE_YEAR", []) if o.label.strip().isdigit()}


def parse_form(text: str) -> FormPage:
    pm = re.search(r'name="page" value="(\w+)"', text)
    nav = _NAV.search(text)
    fp = FormPage(pm.group(1) if pm else None, clean_label(nav.group(1)) if nav else None)
    for sid, _name, body in _SELECT.findall(text):
        fp.selects[sid] = [Option(v, clean_label(lbl) or "", bool(sel)) for v, sel, lbl in _OPTION.findall(body)]
    for lbl, sid in _LABEL.findall(text):
        fp.select_labels[sid] = clean_label(lbl.replace("&nbsp;", " ")) or ""
    for name, value, checked, label in _CHECKBOX.findall(text):
        if value == "-":
            continue
        fp.lists.setdefault(name, []).append(Option(value, html.unescape(label), bool(checked)))
    for target, caption in _BUTTON.findall(text):
        name = target.removesuffix("DIV")
        fp.list_titles[name] = clean_label(caption) or ""
    fp.documents = [(u.replace("\\", "/"), clean_label(t) or "") for u, t in _DOC_LINK.findall(text)]
    m = _POPUP.search(text)
    fp.result_popup = m.group(1) if m else None
    return fp


def parse_sidebar(text: str) -> list[dict]:
    """Start page: [{'page': 'site_b', 'label': 'Ծախսեր', 'total': 3752208931.3}, ...]."""
    out = []
    for page, txt in _SIDEBAR.findall(text):
        m = re.match(r"\s*(.*?)\s+([\d,().-]+)\s*$", txt)
        label, total = (m.group(1), parse_number(m.group(2))) if m else (txt.strip(), None)
        out.append({"page": page, "label": label, "total_kamd": total})
    return out
