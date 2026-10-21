import sys, base64, json, time
sys.path.insert(0, sys.argv[1] + "/dev/tools")
import cdp
svg='<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30"><rect width="40" height="30" fill="red"/></svg>'
b=base64.b64encode(svg.encode()).decode()
with cdp.Browser(400, 300) as br:
    br.goto("file://" + sys.argv[2])
    js = """(async()=>{const r={};const t=async(k,css)=>{const d=document.createElement('div');d.style.cssText='width:40px;height:30px;background-image:'+css;document.body.append(d);
    r[k+'_parsed']=getComputedStyle(d).backgroundImage.slice(0,40);};
    const im=(k,src)=>new Promise(res=>{const i=new Image();i.onload=()=>{r[k]=i.naturalWidth;res()};i.onerror=()=>{r[k]='error';res()};i.src=src;});
    await im('img_ctrl','data:image/svg+xml;base64,B');await im('img_space','data: image/svg+xml;base64,B');await im('img_tab','data:ima\\tge/svg+xml;base64,B');
    await t('is_space','image-set("data: image/svg+xml;base64,B" 1x)');await t('uesc','u\\\\72l(https://beacon.example/a.png)');
    return JSON.stringify(r)})()""".replace("B", b)
    br.call("Runtime.evaluate", expression="document.body||document.write('<body></body>')")
    v = br.call("Runtime.evaluate", expression=js, awaitPromise=True, returnByValue=True)
    print(v)
