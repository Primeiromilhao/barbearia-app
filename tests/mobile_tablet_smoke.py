from playwright.sync_api import sync_playwright
BASE="https://primeiromilhao.github.io/barbearia-app/"
cases=[
("CLIENT_MOBILE",390,844,BASE,["[data-screen=\"welcome\"]","#regName","#regPhone"]),
("CLIENT_TABLET",820,1180,BASE,["[data-screen=\"welcome\"]"]),
("OWNER_MOBILE",390,844,BASE+"proprietario.html",["#ownerPhone","#ownerPassword","#ownerEnter"]),
("OWNER_TABLET",820,1180,BASE+"proprietario.html",["#ownerPhone","#ownerPassword","#ownerEnter"]),
]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for name,w,h,url,checks in cases:
        page=browser.new_page(viewport={"width":w,"height":h})
        page.goto(url,wait_until="domcontentloaded",timeout=15000)
        assert all(page.locator(s).count()>0 for s in checks),(name,"missing selector")
        overflow=page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
        assert not overflow,(name,"horizontal overflow",page.evaluate("document.documentElement.scrollWidth"),w)
        print(name+"=PASS",flush=True)
        page.close()
    browser.close()
print("MOBILE_TABLET_UI=PASS",flush=True)
