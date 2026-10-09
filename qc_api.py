# ============================================================================
# Copyright © 2026 Valrik Thakur (@valriks)
#
# Created & Developed by: Valrik Thakur
# Brand / Network: VTH NETWORK (@vthchannel)
#
# This source code is proprietary content created by Valrik Thakur.
# Unauthorized removal, modification, replacement, or concealment of the
# original author/brand credits is strictly prohibited.
#
# Redistribution, resale, rebranding, or claiming this work as your own
# without explicit permission from the author is prohibited.
#
# Any authorized use or modification must retain this copyright notice
# and the original author/brand credits.
#
# Created by Valrik Thakur | @valriks
# Powered by VTH NETWORK | @vthchannel
# ============================================================================

import ssl
import certifi
import aiohttp
from config import QC_API_URL
from db import api_logs

KEYS = {'s2': '', 's3': '', 'smm': ''}

def set_key(server, key):
    KEYS[server] = (key or '').strip()

def headers(server):
    return {'X-API-Key': KEYS.get(server, ''), 'Content-Type': 'application/json'}

class QCError(Exception):
    def __init__(self, status, message, data=None):
        self.status = status
        self.message = message
        self.data = data or {}

async def request(server, method, path, *, params=None, json=None):
    key = KEYS.get(server, '')
    if not key:
        raise QCError(503, f'QuickCodes {server} API key is not configured')
    url = QC_API_URL + path
    timeout = aiohttp.ClientTimeout(total=65)
    async with aiohttp.ClientSession(timeout=timeout, connector=aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where()))) as session:
        try:
            async with session.request(method, url, headers=headers(server), params=params, json=json) as r:
                data = await r.json(content_type=None)
                status = r.status
        except Exception as e:
            raise QCError(503, f'QuickCodes API unavailable: {e}')
    if not isinstance(data, dict) or not data.get('ok'):
        raise QCError(status, (data or {}).get('message', 'QuickCodes API error') if isinstance(data, dict) else 'Invalid API response', data if isinstance(data, dict) else {})
    return data

async def balance(server):
    return await request(server, 'GET', '/v1/balance')

async def s2_countries():
    return await request('s2', 'GET', '/v1/s2/countries')

async def s2_buy(code):
    return await request('s2', 'POST', '/v1/s2/buy', json={'country_code': code})

async def s2_code(order):
    return await request('s2', 'GET', f'/v1/s2/code/{order}')

async def s3_services(q=None, limit=50, offset=0):
    params = {'limit': limit, 'offset': offset}
    if q:
        params['q'] = q
    return await request('s3', 'GET', '/v1/s3/services', params=params)

async def s3_countries(service):
    return await request('s3', 'GET', '/v1/s3/countries', params={'service': service})

async def s3_offers(service, country):
    return await request('s3', 'GET', '/v1/s3/offers', params={'service': service, 'country': country})

async def s3_buy(service, country, operator):
    return await request('s3', 'POST', '/v1/s3/buy', json={'service': service, 'country': country, 'operator': operator})

async def s3_status(order):
    return await request('s3', 'GET', f'/v1/s3/status/{order}')

async def s3_cancel(order):
    return await request('s3', 'POST', f'/v1/s3/cancel/{order}')

async def smm_services(q=None, app=None, category=None, limit=100, offset=0):
    params = {'limit': limit, 'offset': offset}
    if q:
        params['q'] = q
    if app:
        params['app'] = app
    if category:
        params['category'] = category
    return await request('smm', 'GET', '/v1/smm/services', params=params)

async def smm_order(service, link, quantity=None, comments=None):
    payload = {'service': service, 'link': link}
    if quantity is not None:
        payload['quantity'] = quantity
    if comments:
        payload['comments'] = comments
    return await request('smm', 'POST', '/v1/smm/order', json=payload)

async def smm_status(order):
    return await request('smm', 'GET', f'/v1/smm/order/{order}')

async def smm_orders(limit=20):
    return await request('smm', 'GET', '/v1/smm/orders', params={'limit': limit})

async def smm_refill(order):
    return await request('smm', 'POST', f'/v1/smm/refill/{order}')
