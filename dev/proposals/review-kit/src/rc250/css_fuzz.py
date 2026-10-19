import sys, base64
sys.path.insert(0, sys.argv[1] + "/system/scripts")
import export_page as E
S = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"><text>Walrus budget cut</text></svg>').decode()
G = base64.b64encode(b"GIF89a\x01\x00\x01\x00\x00\x00\x00!\xfe\x11Walrus budget cut\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;").decode()
X = "https://beacon.example/a.png"
V = {
 "escaped \\75rl(": f".p{{background:\\75rl({X})}}",
 "escaped \\75 rl( space": f".p{{background:\\75 rl({X})}}",
 "comment inside url": f".p{{background:url(/**/{X})}}",
 "comment between u/rl": f".p{{background:u/**/rl({X})}}",
 "upper URL(": f".p{{background:URL({X})}}",
 "image-set": f".p{{background:image-set('{X}' 1x)}}",
 "IMAGE-SET upper": f".p{{background:IMAGE-SET('{X}' 1x)}}",
 "image-set escaped": f".p{{background:imag\\65-set('{X}' 1x)}}",
 "-webkit-image-set": f".p{{background:-webkit-image-set('{X}' 1x)}}",
 "@import": f"@import '{X}';",
 "@imp\\6frt": f"@imp\\6frt '{X}';",
 "@import comment": f"@im/**/port '{X}';",
 "src()": f"@font-face{{font-family:a;src:src('{X}')}}",
 "font-face url": f"@font-face{{font-family:a;src:url({X})}}",
 "data svg newline": ".p{background:url('data:image/svg+xml;base64,\n" + S + "')}",
 "data svg percent mime": ".p{background:url('data:image/svg%2bxml;base64," + S + "')}",
 "data svg in url, escaped": ".p{background:url('data:image/svg\\2b xml;base64," + S + "')}",
 "data gif": ".p{background:url(data:image/gif;base64," + G + ")}",
 "data GIF upper": ".p{background:url(DATA:IMAGE/GIF;base64," + G + ")}",
 "data gif escaped": ".p{background:url(data:image/g\\69 f;base64," + G + ")}",
 "data webp": ".p{background:url(data:image/webp;base64,UklGRg==)}",
 "unclosed url end": f".p{{color:red}} .q{{background:url({X}",
 "unclosed url quote": f".p{{background:url(\"{X}",
 "unclosed string": ".p{content:'abc",
 "url inside string closed early": f".p{{background:url('#x') url({X}",
 "var()": f".p{{--a:url({X});background:var(--a)}}",
 "var() split": ".p{--a:ur;--b:l(" + X + ");}",
 "attr()": ".p::after{content:attr(title)}",
 "cross-fade": f".p{{background:cross-fade(url(#a),url({X}),50%)}}",
 "element()": ".p{background:-moz-element(#x)}",
 "paint()": ".p{background:paint(x)}",
 "@namespace": f"@namespace url({X});",
 "url fullwidth paren": f".p{{background:url（{X}）}}",
 "image()": f".p{{background:image('{X}')}}",
 "content string with url": ".p::after{content:'url(https://x)'}",
}
for k, v in V.items():
    print(("ACCEPTED " if E.safe_css_value(v, client=True) else "refused  "), k)
