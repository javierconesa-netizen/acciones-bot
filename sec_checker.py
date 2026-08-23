import os
import requests
import json

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

CIKS = {
    "0000021344": "Coca-Cola",
    "0001065280": "Netflix",
    "0000353278": "Novo Nordisk",
    "0001824317": "Archer Aviation",
    "0001046184": "Taiwan Semiconductor",
    "0001801193": "Opendoor Technologies",
    "0001045810": "NVIDIA",
    "0001923483": "IREN Limited",
    "0001683416": "Gossamer Bio",
    "0001780312": "AST SpaceMobile",
    "0000102312": "US Energy / Big Sky",
    "0001362747": "Ondas",
    "0001819994": "Rocket Lab USA",
    "0001652044": "Alphabet (Google)",
    "0000064463": "Soluna Holdings",
    "0002011037": "Rezolve AI",
    "0001948777": "SEALSQ Corp"
}

SEEN_FILE = 'seen_filings.json'

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r') as f:
            return json.load(f)
    return []

def save_seen(seen):
    with open(SEEN_FILE, 'w') as f:
        json.dump(seen, f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def check_sec():
    seen = load_seen()
    new_seen = list(seen)
    headers = {'User-Agent': 'MiInversorBot usuario@correo.com'}
    
    for cik, name in CIKS.items():
        padded_cik = cik.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                recent = data['filings']['recent']
                
                for i in range(min(3, len(recent['accessionNumber']))):
                    acc_num = recent['accessionNumber'][i]
                    form = recent['form'][i]
                    filed_date = recent['filingDate'][i]
                    doc_name = recent['primaryDocument'][i]
                    
                    identifier = f"{cik}_{acc_num}"
                    
                    if identifier not in seen:
                        clean_acc = acc_num.replace('-', '')
                        link = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{clean_acc}/{doc_name}"
                        msg = f"🚨 *Nuevo SEC Filing*\n*Empresa:* {name}\n*Formulario:* {form}\n*Fecha:* {filed_date}\n[Ver Documento]({link})"
                        send_telegram(msg)
                        new_seen.append(identifier)
        except Exception as e:
            print(f"Error con {name}: {e}")
                    
    save_seen(new_seen[-200:])

if __name__ == "__main__":
    check_sec()
