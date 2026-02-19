import base64
import requests

url = "https://news.google.com/rss/articles/CBMingFBVV95cUxQNnNrekw3QXM3UGQtYzZncU1rd1lKeUotZWJ4amYzN3BwWWFDQ1FXRERGR0tDaXBWdjlUTFNXbklISU9RWDZfcDJ3VDlSWFlpblpIUDhuVlNWa2ZfZThfNnRyTVBDOHN5VFh2eDJrdl91Y0NuR09EMW94UWhZMXo3ZXZhVEhoYWJta3Jyb3NRWEthcnJUNVdHRDQzRVhId9IBowFBVV95cUxPdWpVV3ljSDVuNmV6VWFmWF8wNUcySmhLT2Z4YzNjYmdlbThyTk5RemItOXRfQi1PZzV6bG5ISEZRUE5ZLXM0bndvVmdXYlA5cV9mY3VWRkRsSnpuekJWdkZuRk91YVNMTlNyaUxYZDVwbklIbjZxdUZoNndyemxyVHpfRTNVNVpVRlU1cmw5RkpPOEktVGE5c0hRaUlfbms3R1l3?oc=5"

# Google News uses a specific decoding, but usually just fetching the URL with cookies handles the consent.
# Let's see if we can just get the final URL by bypassing the consent redirect.
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"})
# We need to accept cookies or set a cookie
s.cookies.set("CONSENT", "YES+cb.20210720-07-p0.en+FX+410", domain=".google.com")

try:
    r = s.get(url, allow_redirects=True)
    print("Final URL:", r.url)
except Exception as e:
    print(e)
