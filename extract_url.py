import httpx
import re

js = httpx.get('https://autoflow-ai-ebon.vercel.app/assets/index-BJ5I4xeY.js').text
if "localhost:8000" in js:
    print("Found localhost:8000!")
if "autoflow-ai-production" in js:
    print("Found railway url!")
