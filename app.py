from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import asyncio
from curl_cffi.requests import AsyncSession
from scraper import PracujScraper
from storage import AzureTableManager
import os
from dotenv import load_dotenv
from auth import AuthManager, create_password_hash # Importujemy nasz moduł

app = Flask(__name__)

load_dotenv()

# Konfiguracja (na Azure pobierana ze zmiennych środowiskowych)
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if not AZURE_STORAGE_CONNECTION_STRING:
    raise ValueError("Brak AZURE_STORAGE_CONNECTION_STRING w konfiguracji środowiskowej!")

app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("Brak FLASK_SECRET_KEY w konfiguracji środowiskowej!")


storage_manager = AzureTableManager(AZURE_STORAGE_CONNECTION_STRING)
auth_manager = AuthManager(AZURE_STORAGE_CONNECTION_STRING)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = auth_manager.verify_user(email, password)
        if user:
            session['user'] = user # Zapisujemy dane użytkownika w sesji
            return redirect(url_for('index'))
        
        return render_template('login.html', error="Błędny login lub hasło")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])

@app.route('/scrape', methods=['POST'])
async def scrape():
    if 'user' not in session:
        return jsonify({"error": "Brak autoryzacji"}), 401
    data = request.json
    keywords = list(set([k.strip() for k in data.get('keywords', '').split('\n') if k.strip()]))
    
    # Symulacja grupy użytkownika (później pobierane z modułu logowania)
    user_group = session['user']['group'] # Domyślnie HR
    
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