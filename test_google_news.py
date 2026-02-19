import asyncio
import httpx
from bs4 import BeautifulSoup
import base64

url = "https://news.google.com/rss/articles/CBMingFBVV95cUxQNnNrekw3QXM3UGQtYzZncU1rd1lKeUotZWJ4amYzN3BwWWFDQ1FXRERGR0tDaXBWdjlUTFNXbklISU9RWDZfcDJ3VDlSWFlpblpIUDhuVlNWa2ZfZThfNnRyTVBDOHN5VFh2eDJrdl91Y0NuR09EMW94UWhZMXo3ZXZhVEhoYWJta3Jyb3NRWEthcnJUNVdHRDQzRVhId9IBowFBVV95cUxPdWpVV3ljSDVuNmV6VWFmWF8wNUcySmhLT2Z4YzNjYmdlbThyTk5RemItOXRfQi1PZzV6bG5ISEZRUE5ZLXM0bndvVmdXYlA5cV9mY3VWRkRsSnpuekJWdkZuRk91YVNMTlNyaUxYZDVwbklIbjZxdUZoNndyemxyVHpfRTNVNVpVRlU1cmw5RkpPOEktVGE5c0hRaUlfbms3R1l3?oc=5"

async def test():
    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Safari/537.36"}) as client:
        r = await client.get(url)
        print("Final URL:", r.url)
        print("Title:", BeautifulSoup(r.text, "lxml").title.text)

asyncio.run(test())
