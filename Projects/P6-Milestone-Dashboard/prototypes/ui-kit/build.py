#!/usr/bin/env python3
"""Builds the single-file UI kit gallery from the module sources (D-32 Stage A).

    python3 prototypes/ui-kit/build.py

Inlines every <link>/<script src> that points into src/modules, turns the demo
iframe into srcdoc, and embeds each module's MODULE.md where index.html has
<!--@doc ui-xxx-->. Writes:
    prototypes/ui-kit/dist/ui-kit-gallery.html           open in any browser, no server
    prototypes/ui-kit/dist/ui-kit-gallery.fragment.html  same page without the
                                                         html/head/body wrapper (for publishing)
The dist files are generated: never edit them by hand.
No network, no third-party code: a dev-time copy of unchanged text, like modules_embed.py.
"""
import html
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent            # Projects/P6-Milestone-Dashboard
DIST = HERE / "dist"


def inline_assets(text: str, base: pathlib.Path) -> str:
    def css(m):
        path = (base / m.group(1)).resolve()
        return "<style>/* " + path.relative_to(ROOT).as_posix() + " */\n" + path.read_text() + "</style>"

    def js(m):
        path = (base / m.group(1)).resolve()
        body = path.read_text().replace("</script", "<\\/script")
        return "<script>/* " + path.relative_to(ROOT).as_posix() + " */\n" + body + "</script>"

    text = re.sub(r'<link rel="stylesheet" href="([^"]*src/modules/[^"]+\.css)">', css, text)
    text = re.sub(r'<script src="([^"]*src/modules/[^"]+\.js)"></script>', js, text)
    return text


def md_inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


def md_to_html(md: str) -> str:
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j]); j += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            i = j + 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            head, body = rows[0], [r for r in rows[2:]]
            t = "<table><thead><tr>" + "".join("<th>" + md_inline(c) + "</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join("<td>" + md_inline(c) + "</td>" for c in r) + "</tr>" for r in body)
            out.append(t + "</tbody></table>")
            continue
        m = re.match(r"^(#{1,3}) (.*)", ln)
        if m:
            out.append("<h%d>%s</h%d>" % (len(m.group(1)), md_inline(m.group(2)), len(m.group(1))))
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append("<li>" + md_inline(lines[i][2:]) + "</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif ln.strip():
            out.append("<p>" + md_inline(ln) + "</p>")
        i += 1
    return "\n".join(out)


def main():
    DIST.mkdir(exist_ok=True)
    demo = inline_assets((HERE / "demo-shell.html").read_text(), HERE)
    page = inline_assets((HERE / "index.html").read_text(), HERE)
    page = page.replace('src="demo-shell.html"', 'srcdoc="' + html.escape(demo, quote=True) + '"')

    def doc(m):
        md = (ROOT / "src" / "modules" / m.group(1) / "MODULE.md").read_text()
        return md_to_html(md)

    page = re.sub(r"<!--@doc (ui-[a-z-]+)-->", doc, page)
    (DIST / "ui-kit-gallery.html").write_text(page)

    title = re.search(r"<title>.*?</title>", page, re.S).group(0)
    styles = "".join(re.findall(r"<style>.*?</style>", page.split("</head>")[0], re.S))
    body = re.search(r"<body[^>]*>(.*)</body>", page, re.S).group(1)
    frag = title + "\n" + styles + '\n<div class="ui-root">' + body + "</div>\n"
    (DIST / "ui-kit-gallery.fragment.html").write_text(frag)
    print("wrote", (DIST / "ui-kit-gallery.html").relative_to(ROOT), "and the fragment")


if __name__ == "__main__":
    main()
