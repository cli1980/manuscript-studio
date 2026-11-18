"""Portable source-bound heading components and explicit number presentation."""

import re
import unicodedata

from markdown_it import MarkdownIt


def require(condition, message):
    if not condition:
        raise ValueError(message)


SMALL = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
         "sixteen seventeen eighteen nineteen").split()
TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()
ROMAN = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
         (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))


def number_text(number, form):
    require(isinstance(number, int) and not isinstance(number, bool) and 1 <= number <= 3999,
            "Opening numbers must be integers from 1 through 3999.")
    if form == "arabic":
        return str(number)
    if form in ("roman-upper", "roman-lower"):
        result, remaining = "", number
        for value, symbol in ROMAN:
            count, remaining = divmod(remaining, value)
            result += symbol * count
        return result if form == "roman-upper" else result.lower()

    def cardinal(n):
        if n < 20:
            return SMALL[n]
        if n < 100:
            return TENS[n // 10] + ("-" + SMALL[n % 10] if n % 10 else "")
        base = 1000 if n >= 1000 else 100
        return cardinal(n // base) + (" thousand" if base == 1000 else " hundred") + (
            " " + cardinal(n % base) if n % base else "")

    result = cardinal(number)
    if form == "ordinal-words":
        match = re.search(r"[a-z]+$", result)
        last = match.group()
        ordinal = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth",
                   "nine": "ninth", "twelve": "twelfth"}.get(last)
        result = result[:match.start()] + (ordinal or (last[:-1] + "ieth" if last.endswith("y") else last + "th"))
    else:
        require(form == "words", "Unsupported opening number representation.")
    return result


def source_number(label, number):
    """Verify the supplied ordinal against its source label, never unit order."""
    text = re.sub(r"^(chapter|part|book)\s*(the\s+)?", "", label.strip(), flags=re.I).strip(" .:").lower()
    normalized = lambda s: re.sub(r"[\s-]+", " ", s.lower().replace(" and ", " ")).strip()
    if text.isdecimal():
        return int(text) == number
    if any(normalized(text) == normalized(number_text(number, form))
           for form in ("roman-upper", "words", "ordinal-words")):
        return True
    match = re.fullmatch(r"第?([零〇一二三四五六七八九十百千两\d]+)[章部卷篇]?", text)
    if not match:
        return False
    digits = dict(zip("零〇一二三四五六七八九两", (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2)))
    chinese = match[1]
    if not any(char in "十百千" for char in chinese):
        return int("".join(str(int(char) if char.isdecimal() else digits[char]) for char in chinese)) == number
    value, digit, previous_scale = 0, 0, 10000
    for char in chinese:
        if char in "十百千":
            scale = {"十": 10, "百": 100, "千": 1000}[char]
            if scale >= previous_scale:
                return False
            previous_scale = scale
            value += (digit or 1) * scale
            digit = 0
        else:
            digit = int(char) if char.isdecimal() else digits[char]
    return value + digit == number


def plain_text(markdown):
    result = []
    for token in MarkdownIt("commonmark").parseInline(markdown)[0].children or []:
        if token.type == "text":
            result.append(token.content)
        elif token.type in ("softbreak", "hardbreak"):
            result.append(" " if token.type == "softbreak" else "\n")
        else:
            require(token.type in ("em_open", "em_close", "strong_open", "strong_close"),
                    "Opening components support source text/emphasis only.")
    return "".join(result)


def fields(opening):
    return {kind: " ".join(component["text"] for source in opening["sources"]
                          for component in source["components"] if component["kind"] == kind)
            for kind in ("number", "title", "subtitle")}


def display_number(opening, settings):
    label = fields(opening)["number"]
    if settings["number_format"] != "source" and label:
        value = number_text(opening["number"], settings["number_format"])
        if settings["number_case"] == "title" and settings["number_format"] in ("words", "ordinal-words"):
            value = value.title()
        label = settings["number_template"].replace("{number}", value)
        if settings["number_case"] == "upper":
            label = label.upper()
        elif settings["number_case"] == "lower":
            label = label.lower()
    return label


def validate(proposal, *, catalogs=None, units=None):
    settings = proposal["design_system"]
    styles = {style["id"] for style in settings["styles"]}
    basis = {unit["chapter_id"]: unit["sha256"] for unit in proposal["basis"]["preparation"]["units"]}
    order = list(basis)
    structure = proposal["opening_structure"]
    ids, claimed, members = set(), set(), set()
    chapters = {}
    for kind in ("chapter", "part"):
        config = settings["chapter_openings"] if kind == "chapter" else settings["part_openings"]["heading"]
        for name, value in config.items():
            if name.endswith("_style_id") and value is not None:
                require(value in styles, f"Unknown {kind} opening style: {value}")
        template = config["number_template"]
        require(template.count("{number}") == 1 and "{" not in template.replace("{number}", "")
                and "}" not in template.replace("{number}", "") and not any(c in template for c in "\r\n\t"),
                "Number templates need exactly one {number} token and single-line literal text.")
        require(config["ornament_text"] is None or config["ornament_position"] != "between"
                or config["layout"] == "separated",
                "Between-number/title ornaments require separated layout.")
        require(config["layout"] != "preserve-source" or config["number_format"] == "source",
                "Choose an explicit layout before converting source chapter/part numbers.")
        require(not any(c in config["separator"] for c in "\r\n\t")
                and not any(c in (config["ornament_text"] or "") for c in "\r\n\t"),
                "Opening separators and ornaments must be single-line text.")
        require(kind != "part" or config["start"] != "continuous", "Part openings need a page or recto start.")
        require(config["start"] != "recto" or settings["page"]["blank_policy"] == "allow-declared-recto-blanks",
                "Recto opening starts require allow-declared-recto-blanks.")
    for opening in structure:
        require(opening["id"] not in ids, "Duplicate opening ID.")
        ids.add(opening["id"])
        children = opening["chapter_ids"]
        require(len(children) == len(set(children)) and set(children) <= basis.keys(), "Unknown/duplicate opening member.")
        require([order.index(child) for child in children] == sorted(order.index(child) for child in children),
                "Part chapters must follow source order.")
        if opening["kind"] == "chapter":
            require(len(children) == 1 and children[0] not in chapters, "One chapter opening per unit is allowed.")
            chapters[children[0]] = opening
        else:
            require(not members.intersection(children), "Parts cannot overlap or nest.")
            members.update(children)
        source_units = {source["chapter_id"] for source in opening["sources"]}
        require(len(source_units) == 1, "An opening heading block must belong to one source unit.")
        source_id = next(iter(source_units))
        require(source_id in basis, "Unknown opening source unit.")
        indices = [source["paragraph_index"] for source in opening["sources"]]
        require(indices == list(range(indices[0], indices[0] + len(indices))), "Opening sources must be contiguous and ordered.")
        if opening["kind"] == "chapter":
            require(source_id == children[0], "Chapter headings must bind their own unit.")
        else:
            require(indices[0] == 1 and (source_id == children[0] or order.index(source_id) + 1 == order.index(children[0])),
                    "Part headings must lead their first chapter or the immediately preceding unit.")
        for source in opening["sources"]:
            key = (source_id, source["paragraph_index"])
            require(key not in claimed, "Overlapping opening source paragraphs.")
            claimed.add(key)
            require(source["chapter_sha256"] == basis[source_id], "Stale opening unit hash.")
            require(any(c["kind"] != "literal" for c in source["components"]), "Opening paragraphs need semantic content.")
            require(all(c["kind"] != "literal" or all(char.isspace() or unicodedata.category(char)[0] in "PS"
                                                     for char in c["text"]) for c in source["components"]),
                    "Literal opening components may contain separators, not hidden words or numbers.")
            if catalogs is not None:
                catalog = catalogs[source_id]
                require(source["paragraph_index"] <= len(catalog), "Opening paragraph is out of bounds.")
                paragraph = catalog[source["paragraph_index"] - 1]
                require(paragraph["paragraph_sha256"] == source["paragraph_sha256"], "Stale opening paragraph hash.")
                require("".join(c["text"] for c in source["components"]) == plain_text(paragraph["markdown"]),
                        "Opening components must account for the exact complete source paragraph.")
        values = fields(opening)
        require(bool(values["number"]) == (opening["number"] is not None), "Opening number and source label must agree.")
        if opening["number"] is not None:
            require(source_number(values["number"], opening["number"]), "Opening ordinal does not match its source label.")
        require(values["number"] or values["title"], "Openings need a source number or title.")
        config = settings["chapter_openings"] if opening["kind"] == "chapter" else settings["part_openings"]["heading"]
        require(config["layout"] != "title-only" or values["title"], "Title-only layout needs an actual source title.")
        if units is not None:
            require(all(units[child]["role"] in ("chapter", "standalone") for child in children),
                    "Front/back matter cannot be numbered as chapters or part members.")
            require(units[source_id]["role"] in ("chapter", "standalone"),
                    "Part/chapter heading sources cannot consume front/back matter.")
    for child, opening in chapters.items():
        first = opening["sources"][0]["paragraph_index"]
        parts = [part for part in structure if part["kind"] == "part" and part["chapter_ids"][0] == child
                 and part["sources"][0]["chapter_id"] == child]
        require(first == 1 or len(parts) == 1 and first > parts[0]["sources"][-1]["paragraph_index"],
                "A chapter heading must lead its unit, after any explicit part material.")
    for part in (o for o in structure if o["kind"] == "part"):
        require(set(part["chapter_ids"]) <= chapters.keys(), "Part members need explicit chapter opening records.")
        start, end = order.index(part["chapter_ids"][0]), order.index(part["chapter_ids"][-1])
        require(not any(child in chapters and child not in part["chapter_ids"] for child in order[start:end + 1]),
                "A part cannot skip intervening chapter openings.")
        source_id = part["sources"][0]["chapter_id"]
        require(source_id == part["chapter_ids"][0] or source_id not in chapters and source_id not in members,
                "A dedicated part source unit cannot also be a chapter or another part member.")
    role_keys = {(o["chapter_id"], o["paragraph_index"]) for role in proposal["text_roles"] for o in role["occurrences"]}
    require(not claimed.intersection(role_keys), "Opening headings cannot also have competing text-role style assignments.")
    if units is not None and settings["chapter_openings"]["layout"] != "preserve-source":
        part_units = {o["sources"][0]["chapter_id"] for o in structure if o["kind"] == "part"
                      and o["sources"][0]["chapter_id"] != o["chapter_ids"][0]}
        require({key for key, unit in units.items() if unit["role"] == "chapter"} - part_units <= chapters.keys(),
                "Non-preserve chapter layout requires explicit coverage of every chapter.")
