"""Browser UI verification using isolated responses, never production data.
Run Vite, then: python frontend/tests/ui_smoke.py
Requires the locally available Playwright Python package and Chromium.
"""
import csv
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts'
OUT.mkdir(exist_ok=True)
products = list(csv.DictReader((ROOT / 'data/catalogue.csv').open(encoding='utf-8')))
for item in products: item['stock'] = int(item['stock'])
dealers = list(csv.DictReader((ROOT / 'data/dealers.csv').open(encoding='utf-8')))
for index, dealer in enumerate(dealers): dealer['id'] = index + 1
forecast = list(csv.DictReader((ROOT / 'ml/forecast.csv').open(encoding='utf-8')))
for item in forecast: item['forecast_units'] = float(item['forecast_units'])
# Test-only responses with the same fields as the backend contract.
reorders = [dict(sku=item['sku'], current_stock=item['stock'], lead_time_weeks=2,
                 lead_time_demand=90, safety_stock=20, reorder_point=110,
                 reorder_qty=max(0, 110-item['stock'])) for item in products[:8]]
part = products[0]
order = dict(order_number='UI-TEST-001', dealer_id=1, status='DRAFT', created_at='2026-10-14T10:00:00+0530',
             updated_at='2026-10-14T10:00:00+0530', subtotal='1239.00', tax_total='223.02', grand_total='1462.02',
             items=[dict(sku=part['sku'],name=part['name'],quantity=1,unit_price='1239.00',line_subtotal='1239.00',line_tax='223.02',line_total='1462.02')])
requests = []
fail_inventory = False

def api(route):
    global fail_inventory
    req = route.request
    parsed = urlparse(req.url)
    path, query = parsed.path, parse_qs(parsed.query)
    body = req.post_data_json if req.post_data else None
    requests.append(dict(path=path, method=req.method, body=body, query=query))
    status = 200
    if path == '/api/health/': data = {'status':'ok'}
    elif path == '/api/products/' and req.method == 'GET':
        items = products
        term = query.get('search',[''])[0].lower()
        if term: items = [x for x in items if term in (x['sku']+' '+x['name']+' '+x['brand']).lower()]
        if 'category' in query: items = [x for x in items if x['category']==query['category'][0]]
        if 'vehicle' in query: items = [x for x in items if query['vehicle'][0].lower() in x['vehicle_fitment'].lower()]
        size, page = int(query.get('page_size',[20])[0]), int(query.get('page',[1])[0])
        data = dict(count=len(items),results=items[(page-1)*size:page*size])
    elif path == '/api/products/' and req.method == 'POST':
        products.insert(0,{**body,'stock':0}); data=products[0]; status=201
    elif path.startswith('/api/products/') and req.method == 'PATCH':
        item=next(x for x in products if x['sku']==path.split('/')[3]); item.update(body); data=item
    elif path.startswith('/api/inventory/'):
        assert isinstance(body['quantity'],int), 'Inventory quantity contract changed'
        if fail_inventory:
            data={'error':{'message':'Invalid inventory','details':[{'field':'quantity','error':'Test validation error'}]}};status=400
        else:
            item=next(x for x in products if x['sku']==path.split('/')[3]);item['stock']=body['quantity']; data={'sku':item['sku'],'quantity':item['stock']}
    elif path == '/api/dealers/' and req.method == 'GET':
        size,page=int(query.get('page_size',[25])[0]),int(query.get('page',[1])[0]);data=dict(count=len(dealers),results=dealers[(page-1)*size:page*size])
    elif path == '/api/dealers/': dealers.append({**body,'id':len(dealers)+1});data=dealers[-1];status=201
    elif path == '/api/orders/' and req.method == 'GET': data={'count':1,'results':[order] if query.get('status',[order['status']])[0]==order['status'] else []}
    elif path == '/api/orders/' and req.method == 'POST': data=order;status=201
    elif path == '/api/orders/UI-TEST-001/': data=order
    elif path.startswith('/api/orders/UI-TEST-001/'):
        action=path.split('/')[4];order['status']={'confirm':'CONFIRMED','dispatch':'DISPATCHED','deliver':'DELIVERED','cancel':'CANCELLED'}[action];data=order
    elif path == '/api/reorder-suggestions/': data={'results':reorders}
    elif path.startswith('/api/forecast/'): data={'sku':path.split('/')[3],'forecast':forecast[:4]}
    elif path == '/api/assistant/chat/': data={'reply':'Test response: stock verified.','cited_skus':[part['sku']],'tool_calls':[],'actions':[]}
    elif path == '/api/sync/supplier/': data={'created':1,'updated':2}
    else: raise AssertionError(f'Unexpected API request: {req.method} {path}')
    route.fulfill(status=status,json=data)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    context.route('**/api/**',api)
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    checks=[]
    routes=['/','/products','/dealers','/orders','/assistant','/forecasting']
    for theme in ['light','dark']:
        for width in [1440,768,375]:
            page.set_viewport_size({'width':width,'height':1000})
            for route in routes:
                page.goto('http://127.0.0.1:5173'+route)
                page.get_by_label('Color theme').select_option(theme)
                page.locator('main h1, main h3').first.wait_for()
                page.wait_for_timeout(250)
                page.get_by_label('Color theme').evaluate('(node) => node.blur()')
                assert page.evaluate('document.documentElement.dataset.theme') == theme
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'Overflow {route} {width} {theme}'
                assert page.locator('main').inner_text().strip()
                checks.append(f'{route} {width}px {theme}: rendered without overflow')
                if width==1440 or (width==375 and route in ['/','/assistant']):
                    name='overview' if route=='/' else route[1:]
                    page.screenshot(path=str(OUT/f'{name}-{theme}-{width}.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto('http://127.0.0.1:5173/products')
    page.get_by_label('Color theme').select_option('dark')
    page.reload()
    assert page.get_by_label('Color theme').input_value()=='dark'
    assert page.evaluate('document.documentElement.dataset.theme')=='dark'
    page.get_by_label('Color theme').select_option('system')
    page.emulate_media(color_scheme='light');page.wait_for_function("document.documentElement.dataset.theme === 'light'")
    page.emulate_media(color_scheme='dark');page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
    checks.append('Theme persistence and live system preference: pass')
    page.get_by_label('Collapse sidebar').click()
    assert page.locator('.desktop-sidebar').bounding_box()['width']==72
    page.get_by_label('Expand sidebar').click()
    # Global search follows the existing catalogue API, including on the same route.
    page.get_by_label('Search product catalogue').fill(part['sku'])
    page.get_by_label('Search product catalogue').press('Enter')
    page.wait_for_timeout(250)
    assert page.get_by_label('Search by SKU, part name, or brand').input_value()==part['sku']
    page.get_by_role('button',name='Adjust',exact=True).first.click()
    dialog=page.get_by_role('dialog')
    dialog.get_by_label('New Stock Count (Units) *').fill('42')
    fail_inventory=True
    dialog.get_by_role('button',name='Save Stock Count').click()
    assert dialog.get_by_role('alert').inner_text().find('quantity: Test validation error')>=0
    fail_inventory=False
    dialog.get_by_role('button',name='Save Stock Count').click()
    page.wait_for_timeout(150)
    assert page.get_by_role('status').filter(has_text='Stock updated').count()==1
    assert any(x['path'].startswith('/api/inventory/') and x['body']['quantity']==42 for x in requests)
    page.get_by_role('button',name='Edit',exact=True).first.click()
    dialog=page.get_by_role('dialog')
    assert dialog.get_by_label('SKU Code *').get_attribute('readonly') is not None
    dialog.get_by_label('Product Name *').fill('Updated browser test part')
    dialog.get_by_role('button',name='Save product').click()
    page.wait_for_timeout(150)
    assert any(x['method']=='PATCH' for x in requests)
    page.get_by_role('button',name='Add Product',exact=True).click()
    dialog=page.get_by_role('dialog')
    # Focus stays inside the dialog and Escape restores the opening control.
    first=dialog.locator('button, input, select, textarea').first
    first.focus();page.keyboard.press('Shift+Tab')
    assert dialog.evaluate('(node)=>node.contains(document.activeElement)')
    page.keyboard.press('Escape')
    assert page.get_by_role('dialog').count()==0
    assert page.get_by_role('button',name='Add Product',exact=True).evaluate('(node)=>document.activeElement===node')
    checks.append('Catalogue search, inventory payload, validation, product editing, modal keyboard access: pass')
    page.get_by_role('button',name='Add Product',exact=True).click()
    dialog=page.get_by_role('dialog')
    dialog.get_by_label('SKU Code *').fill('UI-PART-001')
    dialog.get_by_label('Brand *').fill('UI test brand')
    dialog.get_by_label('Product Name *').fill('Browser test product')
    dialog.get_by_label('Price (₹ INR, excluding GST) *').fill('99.50')
    dialog.get_by_role('button',name='Save product').click()
    page.wait_for_timeout(150)
    assert any(x['path']=='/api/products/' and x['method']=='POST' for x in requests)
    page.goto('http://127.0.0.1:5173/products')
    page.get_by_label('Product category',exact=True).select_option('Brakes')
    page.wait_for_timeout(150)
    assert any(x['query'].get('category')==['Brakes'] for x in requests)
    page.get_by_label('Product category',exact=True).select_option('All Categories')
    page.get_by_role('button',name='Next',exact=True).click()
    page.wait_for_timeout(150)
    assert any(x['query'].get('page')==['2'] and x['path']=='/api/products/' for x in requests)
    checks.append('Product creation, category filtering and pagination: pass')
    page.goto('http://127.0.0.1:5173/dealers')
    page.get_by_label('Search dealers on this page').fill('ABC Motors')
    assert page.locator('tbody tr').count()==1
    page.get_by_role('button',name='Add Dealer',exact=True).click()
    dialog=page.get_by_role('dialog')
    dialog.get_by_label('Dealer Code *').fill('UI-TEST')
    dialog.get_by_label('Dealer Name / Firm *').fill('Browser Test Dealer')
    dialog.get_by_role('button',name='Register Dealer').click()
    page.wait_for_timeout(150)
    assert any(x['path']=='/api/dealers/' and x['method']=='POST' for x in requests)
    checks.append('Dealer search and creation: pass')
    page.goto('http://127.0.0.1:5173/orders?order=UI-TEST-001')
    dialog=page.get_by_role('dialog')
    dialog.get_by_role('button',name='Confirm & Deduct Stock',exact=True).click()
    dialog.get_by_role('button',name='Dispatch Order',exact=True).click()
    dialog.get_by_role('button',name='Mark as Delivered',exact=True).click()
    dialog.get_by_text('Delivered',exact=True).wait_for()
    dialog.get_by_role('button',name='Close',exact=True).click()
    page.get_by_role('button',name='New Draft Order').click()
    dialog=page.get_by_role('dialog')
    dialog.get_by_label('Item 1 SKU').fill(part['sku'])
    dialog.get_by_role('button',name='Save Draft Order').click()
    page.wait_for_timeout(150)
    assert any(x['path']=='/api/orders/' and x['method']=='POST' for x in requests)
    checks.append('Order deep link, confirmation, dispatch, delivery, draft creation: pass')
    page.get_by_role('dialog').get_by_role('button',name='Close',exact=True).click()
    order['status']='DRAFT'
    page.goto('http://127.0.0.1:5173/orders?order=UI-TEST-001')
    page.get_by_role('dialog').get_by_role('button',name='Cancel Draft',exact=True).click()
    page.get_by_role('dialog').get_by_text('Cancelled',exact=True).wait_for()
    checks.append('Draft cancellation: pass')
    page.goto('http://127.0.0.1:5173/assistant')
    page.get_by_label('Message to assistant').fill('Check stock')
    page.get_by_role('button',name='Send',exact=True).click()
    page.get_by_text('Test response: stock verified.',exact=True).wait_for()
    checks.append('Dealer assistant request and response: pass')
    # Every form and detail panel must also fit the narrow viewport in both themes.
    for theme in ['light','dark']:
        page.set_viewport_size({'width':375,'height':900})
        for path,action in [('/products','Add Product'),('/dealers','Add Dealer'),('/orders','New Draft Order')]:
            page.goto('http://127.0.0.1:5173'+path)
            page.get_by_label('Color theme').select_option(theme)
            page.get_by_role('button',name=action,exact=True).click()
            dialog=page.get_by_role('dialog')
            assert dialog.bounding_box()['width']<=375
            assert dialog.evaluate('(node)=>node.scrollWidth <= node.clientWidth'),f'Dialog overflow: {path} {theme}'
            page.screenshot(path=str(OUT/f'{path[1:]}-dialog-{theme}.png'),full_page=True)
            page.keyboard.press('Escape')
        page.goto('http://127.0.0.1:5173/orders?order=UI-TEST-001')
        assert page.get_by_role('dialog').bounding_box()['width']<=375
        page.keyboard.press('Escape')
    checks.append('Create and order-detail dialogs at 375px in both themes: pass')
    page.set_viewport_size({'width':375,'height':900})
    page.get_by_label('Open navigation').click()
    page.get_by_role('dialog').get_by_role('link',name='Orders',exact=True).click()
    assert page.get_by_role('dialog').count()==0
    assert page.url.endswith('/orders')
    checks.append('Mobile navigation drawer: pass')
    page.goto('http://127.0.0.1:5173/products')
    page.emulate_media(reduced_motion='no-preference')
    page.get_by_role('button',name='Add Product',exact=True).click()
    assert page.locator('.modal-container').evaluate("node => getComputedStyle(node).animationName")=='page-in'
    page.get_by_label('Close dialog').click()
    page.wait_for_function("!document.querySelector('[role=dialog]')")
    page.emulate_media(reduced_motion='reduce')
    page.get_by_role('button',name='Add Product',exact=True).click()
    assert page.locator('.modal-container').evaluate("node => getComputedStyle(node).animationName")=='none'
    page.keyboard.press('Escape')
    checks.append('Modal entrance/exit and reduced-motion behavior: pass')
    assert not errors,errors
    report={'checks':checks,'console_errors':errors,'request_count':len(requests),'data_mode':'isolated browser test responses; no backend mutations'}
    (OUT/'ui-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    browser.close()

