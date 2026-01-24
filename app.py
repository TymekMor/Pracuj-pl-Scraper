from flask import Flask, render_template, jsonify, request
import asyncio
from curl_cffi.requests import AsyncSession
from scraper import PracujScraper
from storage import AzureTableManager
import os
from dotenv import load_dotenv
app = Flask(__name__)

# Konfiguracja (na Azure pobierana ze zmiennych środowiskowych)
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
storage_manager = AzureTableManager(AZURE_STORAGE_CONNECTION_STRING)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
async def scrape():
    data = request.json
    keywords = list(set([k.strip() for k in data.get('keywords', '').split('\n') if k.strip()]))
    
    # Symulacja grupy użytkownika (później pobierane z modułu logowania)
    user_group = data.get('group', 'HR') # Domyślnie HR
    
    scraper = PracujScraper()
    all_results = []
    
    async with AsyncSession() as client:
        tasks = [scraper.scrape_keyword(client, kw) for kw in keywords]
        results = await asyncio.gather(*tasks)
        for r in results:
            all_results.extend(r)
    
    # Zapis do bazy danych Azure
    try:
        storage_manager.save_offers(all_results, user_group)
    except Exception as e:
        print(f"Błąd zapisu do Azure Table Storage: {e}")

    # Mapowanie na polskie nazwy dla frontendu (zgodnie z Twoim poprzednim wymogiem)
    formatted_results = []
    for o in all_results:
        formatted_results.append({
            'Szukana fraza': o['Keyword'],
            'Stanowisko': o['Title'],
            'Firma': o['Company'],
            'Wynagrodzenie': o['Salary'],
            'Lokalizacja': o['Location'],
            'Link': o['Link'],
            'Wymagania (AI)': o['Requirements']
        })

    # Usuwanie duplikatów przed wysłaniem na frontend
    unique_results = {o['Link']: o for o in formatted_results}.values()
    return jsonify(list(unique_results))

if __name__ == "__main__":
    app.run(debug=True)