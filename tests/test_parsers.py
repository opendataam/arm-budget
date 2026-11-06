"""Tests of the parsers and of the code resolution (no network)."""

from decimal import Decimal
from pathlib import Path

from arm_budget import config
from arm_budget.parsers.common import clean_label, is_total_label, norm_key, parse_date, parse_decimal, parse_number, parse_percent
from arm_budget.parsers.contracts import parse_contracts
from arm_budget.parsers.deficit import classify
from arm_budget.parsers.forms import parse_form, parse_sidebar
from arm_budget.parsers.grid import js_unescape, parse_grid
from arm_budget.parsers.xls_export import parse_title
from arm_budget.resolve import Classifier, needed_probes, resolve
from arm_budget.translit import partner_name
from arm_budget.tree import build_tree, value_fields

FIX = Path(__file__).parent / "fixtures"


def test_numbers():
    assert parse_number("1,234.50") == 1234.5
    assert parse_number("(60,216,913.42)") == -60216913.42
    assert parse_number("") is None
    assert parse_decimal("857299630.7701") == Decimal("857299630.7701")
    assert parse_decimal("(1,023,125.90)") == Decimal("-1023125.90")
    assert parse_percent("(27)%") == -27
    assert parse_percent("84%") == 84
    assert parse_date("15/01/26").isoformat() == "2026-01-15"


def test_labels():
    assert clean_label("պտուղն\nերից ") == "պտուղներից"
    assert clean_label(" - Հող\n") == "- Հող"
    assert norm_key("Օրենսդիր և  գործադիր մարմիններ, պետական կառավարում") == norm_key(
        "Օրենսդիր և գործադիր մարմիններ պետական կառավարում")
    assert norm_key("- Էներգետիկ ծառայություններ") == norm_key("Էներգետիկ ծառայություններ")
    assert norm_key("դաuվող") == norm_key("դասվող")  # Latin look-alike letters
    assert is_total_label("  Ը  Ն  Դ  Ա  Մ  Ե  Ն  Ը    այդ թվում")
    assert js_unescape(r"a\'b\\c") == "a'b\\c"


def test_grid_and_tree():
    grid = parse_grid((FIX / "tree.html").read_text(encoding="utf-8"))
    assert grid.header.startswith("Արդյունք")
    assert [c.field for c in grid.group_columns] == ["c2", "c3", "c4"]
    assert len(value_fields(grid)) == 12
    total, nodes = build_tree(grid)
    assert total.level == -1 and total.raw["year_plan"] == "120"
    assert [n.level for n in nodes] == [0, 1, 2, 1, 2, 2]
    leaves = [n for n in nodes if n.level == 2]
    assert sum(n.value("year_plan") for n in leaves) == 120
    assert leaves[0].parent.label == "Այլ մարմիններ"


def _dims():
    return (
        config.Dimension("func_section", "grp", 1, "Բաժին", "dim_functional"),
        config.Dimension("department", "mid", 2, "Գերատեսչական դասակարգում", "dim_department"),
        config.Dimension("economic", "sub", 3, "Հոդված", "dim_economic"),
    )


def test_resolve_by_name_and_probe():
    grid = parse_grid((FIX / "tree.html").read_text(encoding="utf-8"))
    _, nodes = build_tree(grid)
    lists = {
        "func_section": Classifier("func_section", [("02", "ՊԱՇՏՊԱՆՈՒԹՅՈՒՆ")]),
        "department": Classifier("department", [("301020", "Այլ մարմիններ"), ("301021", "Այլ մարմիններ")]),
        "economic": Classifier("economic", [("4221", "Գործուղումների և շրջագայությունների ծախսեր"),
                                            ("4229", "Գործուղումների և շրջագայությունների ծախսեր")]),
    }
    dims = _dims()
    stats = resolve(nodes, dims, lists, {})
    assert stats == {"name": 1, "unresolved": 5}
    want = needed_probes(nodes, dims, lists, set())
    assert ("department", "301020") in want and ("economic", "4229") in want
    # probe: the same query filtered by economic article 4229 returns only the last line
    probe_html = (FIX / "tree.html").read_text(encoding="utf-8")
    probe = parse_grid(probe_html)
    probe.records = [r for r in probe.records if r.recid in (1, 2, 5, 7)]
    stats = resolve(nodes, dims, lists, {("economic", "4229"): probe})
    leaves = [n for n in nodes if n.level == 2]
    assert leaves[2].code == "4229" and leaves[2].method == "probe"


def test_form_and_sidebar():
    html = """<form name=Pages method="post" action="param.php"><input type="hidden" name="page" value="site_b" >
    <a href="#" class="active">Ծախսեր  3,752,208,931.30</a>
    <tr><td colspan="1"><label class="formLeftBlock">ԲՅՈՒՋԵՆ ԸՍՏ ՏԱՐԵԹՎԻ&nbsp;&nbsp;</label><div class="formRightBlock"><select id=SITE_YEAR name=SITE_YEAR style="WIDTH:140px;">
    <option value="1"  selected>2026</option>
    <option value="2" >2025</option>
    </select></div></td></tr>
    <div align="right"><font size="+0.5"> <a href="xml\\16.pdf">ԴԱՍԱԿԱՐԳՄԱՆ ԿԻՐԱՌՄԱՆ ՑՈՒՑՈՒՄՆԵՐ` ԸՆԹԱՑԻԿ ԾԱԽՍԵՐ </a></div>
    <button type="button" class="btn btn-info" data-toggle="collapse" data-target="#midDIV" style="width:300px;">Գերատեսչական դասակարգում</button>
    <div class="multiselect" ><label><input type="checkbox" name="mid[]" value="-" />ԲՈԼՈՐԸ</label><label><input type="checkbox" name="mid[]" value="101001" />Հանրապետության նախագահի աշխատակազմ</label></div>
    """
    fp = parse_form(html)
    assert fp.page == "site_b"
    assert fp.year_options() == {1: 2026, 2: 2025}
    assert fp.selected("SITE_YEAR") == "1"
    assert [(o.value, o.label) for o in fp.lists["mid"]] == [("101001", "Հանրապետության նախագահի աշխատակազմ")]
    assert fp.list_titles["mid"] == "Գերատեսչական դասակարգում"
    assert fp.documents == [("xml/16.pdf", "ԴԱՍԱԿԱՐԳՄԱՆ ԿԻՐԱՌՄԱՆ ՑՈՒՑՈՒՄՆԵՐ` ԸՆԹԱՑԻԿ ԾԱԽՍԵՐ")]
    side = parse_sidebar("{ id: 'site_b.0', text: 'Ծախսեր  3,752,208,931.30', img: 'icon-page', parent: 'sites' },")
    assert side == [{"page": "site_b", "label": "Ծախսեր", "total_kamd": 3752208931.3}]


def test_contracts():
    html = """<table class="account"><td class="td00">Գործընկեր</td><td class="td00">Պայմ.սկիզբ</td><td class="td00">Պայմ.ավարտ</td><td class="td00">Պայմ.գումարը</td><td class="td00">Վճարված գումար</td>
<tr><td class="td0L">-Տելեկոմ Արմենիա- ԲԲԸ</td><td class="td0L">26/02/26</td><td class="td0L">30/12/26</td><td class="td0R">980.00</td><td class="td0R">197.35</td></tr>
<tr><td COLSPAN=5><button type="button" class="btn btn-info" data-toggle="collapse" data-target="#DIV1" style="width:300px;">Ֆայլեր</button><div class="collapse " id="DIV1"><img src="css/images/pdfs-24.png" border=0 width="15px">&nbsp;<a target="_blank" href="https://armeps.am/ppcm/public/contracts/download-attachment?id=77e6">FILE1</a>&nbsp;&nbsp;<a target="_blank" href="xml\\storage\\135672426-8781.pdf">FILE2</a>&nbsp;</td></div></tr>
</table>"""
    header, items = parse_contracts(html, "https://budget.minfin.am:82")
    assert header[0] == "Գործընկեր"
    assert len(items) == 1
    c = items[0]
    assert c.partner == "-Տելեկոմ Արմենիա- ԲԲԸ" and c.amount == 980.0 and c.paid == 197.35
    assert c.start_date.isoformat() == "2026-02-26"
    assert c.files[1][0] == "https://budget.minfin.am:82/xml/storage/135672426-8781.pdf"


def test_deficit_structure():
    labels = ["ԸՆԴԱՄԵՆԸ", "այդ թվում`", "Ա. Ներքին աղբյուրներ-ընդամենը", "այդ թվում`", "1. Փոխառու միջոցներ",
              "1.1 Արժեթղթերի թողարկումից", "ՀՀ Ֆինանսների նախարարություն", "որից`", "   Գանձապետական պարտատոմսեր",
              "2.3. Ելքերի ֆինանսավորման", "Բ. Արտաքին աղբյուրներ-ընդամենը", "1. Փոխառու զուտ միջոցներ"]
    lines = classify(labels)
    kinds = [(ln.kind, ln.item_code) for ln in lines]
    assert kinds[0] == ("total", "TOTAL")
    assert kinds[2] == ("source", "A") and kinds[4] == ("item", "A.1") and kinds[5] == ("subitem", "A.1.1")
    assert kinds[6] == ("detail", None) and lines[6].parent == 6
    assert lines[8].note == "որից" and lines[8].indent == 3
    assert kinds[9] == ("subitem", "A.2.3")
    assert kinds[10] == ("source", "B") and kinds[11] == ("item", "B.1") and lines[11].parent == 11


def test_export_title():
    xml = """<Workbook><Worksheet ss:Name="Sheet1"><Table><Row></Row><Row><Cell><Data ss:Type="String">ԲՅՈՒՋԵ ԾԱԽՍԵՐ  առ 04/11/26  -  հազ. դրամներով</Data></Cell></Row></Table></Worksheet></Workbook>"""
    title, d = parse_title(xml)
    assert d.isoformat() == "2026-11-04" and title.startswith("ԲՅՈՒՋԵ ԾԱԽՍԵՐ")


def test_partner_transliteration():
    assert partner_name("-Հայաստանի էլեկտրական ցանցեր- ՓԲԸ", "en") == '"Hayastani elektrakan tsantser" CJSC'
    assert partner_name("Արարատ Թորոսյան ԱՁ", "ru") == "Арарат Торосян ИП"
    assert partner_name("Երեւանի ավտոբուսներ ՓԲԸ", "en") == "Yerevani avtobusner CJSC"
