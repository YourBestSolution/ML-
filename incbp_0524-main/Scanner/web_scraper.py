import os
import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

url = "https://incab.ru/useful-information/documents/#!technical_notes"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
}

docs_folder = os.path.join(os.path.dirname(__file__), "docs")
os.makedirs(docs_folder, exist_ok=True)

response = requests.get(url, headers=headers)
html = response.content

soup = BeautifulSoup(html, 'html.parser')
library_page = soup.find('div', class_='library-page')
links = library_page.find_all('a')

def clean_filename(text):
    text = text.replace('— ', '').replace('(скачать .pdf)', '').strip()
    text = text.replace('\r', '').replace('\n', '')
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    text = text[:100]
    return text

for link in links:
    href = link.get('href')
    text = link.get_text()
    
    if not href:
        continue
    
    if not href.startswith('http'):
        href = urljoin(url, href)
    
    parsed_url = urlparse(href)
    if 'incab.ru' not in parsed_url.netloc:
        continue
    
    if href.endswith('.pdf'):
        filename = clean_filename(text) + '.pdf'
        file_path = os.path.join(docs_folder, filename)
        if os.path.exists(file_path):
            continue
        print(f"DL {href} | {filename}")
        pdf_response = requests.get(href, headers=headers)
        with open(file_path, 'wb') as file:
            file.write(pdf_response.content)
    else:
        filename = clean_filename(text) + '.txt'
        file_path = os.path.join(docs_folder, filename)
        if os.path.exists(file_path):
            continue
        print(f"DL {href} | {filename}")
        page_response = requests.get(href, headers=headers)
        page_soup = BeautifulSoup(page_response.content, 'html.parser')
        content_text = page_soup.find('div', class_='col-xs-12 singularContent')
        if content_text:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content_text.get_text(separator='\n', strip=True))

print("Скачивание завершено.")
