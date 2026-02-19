import base64

url = "https://news.google.com/rss/articles/CBMingFBVV95cUxQNnNrekw3QXM3UGQtYzZncU1rd1lKeUotZWJ4amYzN3BwWWFDQ1FXRERGR0tDaXBWdjlUTFNXbklISU9RWDZfcDJ3VDlSWFlpblpIUDhuVlNWa2ZfZThfNnRyTVBDOHN5VFh2eDJrdl91Y0NuR09EMW94UWhZMXo3ZXZhVEhoYWJta3Jyb3NRWEthcnJUNVdHRDQzRVhId9IBowFBVV95cUxPdWpVV3ljSDVuNmV6VWFmWF8wNUcySmhLT2Z4YzNjYmdlbThyTk5RemItOXRfQi1PZzV6bG5ISEZRUE5ZLXM0bndvVmdXYlA5cV9mY3VWRkRsSnpuekJWdkZuRk91YVNMTlNyaUxYZDVwbklIbjZxdUZoNndyemxyVHpfRTNVNVpVRlU1cmw5RkpPOEktVGE5c0hRaUlfbms3R1l3?oc=5"

# Let's try base64 decoding the part after articles/
encoded_part = url.split("articles/")[1].split("?")[0]
try:
    print(base64.urlsafe_b64decode(encoded_part + "==="))
except Exception as e:
    print("Base64 error:", e)

