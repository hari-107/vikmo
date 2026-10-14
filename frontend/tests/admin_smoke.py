"""Render and inspect the real Django admin login without a database mutation."""
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','dealerdesk.settings')
import django
django.setup()
from django.test import Client
from django.template.loader import get_template
assert str(get_template('admin/base_site.html').origin.name)==str(ROOT/'templates/admin/base_site.html')
response=Client().get('/admin/login/?next=/admin/')
assert response.status_code==200
html=response.content.decode()
assert 'csrfmiddlewaretoken' in html
assert 'action="/admin/login/?next=/admin/"' in html
admin_static=Path(django.__file__).parent/'contrib/admin/static'
errors=[]
def route_handler(route):
    from urllib.parse import urlparse
    path=urlparse(route.request.url).path
    if path.startswith('/admin/login'): route.fulfill(status=200,content_type='text/html; charset=utf-8',body=html)
    elif path.startswith('/static/admin/'):
        path=admin_static/path.removeprefix('/static/')
        route.fulfill(path=str(path),content_type='text/css' if path.suffix=='.css' else 'application/javascript' if path.suffix=='.js' else 'image/svg+xml')
    elif path.startswith('/static/dealerdesk/'):
        path=ROOT/'core/static'/path.removeprefix('/static/')
        route.fulfill(path=str(path),content_type='text/css' if path.suffix=='.css' else 'application/javascript')
    else: route.abort()
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context()
    context.route('**/*',route_handler)
    page=context.new_page()
    page.on('pageerror',lambda e:errors.append(str(e)))
    checks=[]
    for theme in ['light','dark']:
        for width in [1440,768,375]:
            page.set_viewport_size({'width':width,'height':900})
            page.goto('http://127.0.0.1:5173/admin/login/?next=/admin/')
            page.get_by_label('Color theme').select_option(theme)
            assert page.evaluate('document.documentElement.dataset.theme')==theme
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            password=page.locator('#id_password')
            page.get_by_role('button',name='Show password',exact=True).click();assert password.get_attribute('type')=='text'
            page.get_by_role('button',name='Hide password',exact=True).click();assert password.get_attribute('type')=='password'
            page.screenshot(path=str(ROOT/'artifacts'/f'admin-login-{theme}-{width}.png'),full_page=True)
            checks.append(f'Django admin login {theme} {width}px: pass')
    page.get_by_label('Color theme').select_option('system')
    page.emulate_media(color_scheme='dark');page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
    assert not errors,errors
    report=dict(checks=checks,console_errors=errors,csrf_form_preserved=True,mode='Django Client GET and browser-rendered template; no database changes')
    (ROOT/'artifacts/admin-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    browser.close()
