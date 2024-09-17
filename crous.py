import os
import json
import requests
from bs4 import BeautifulSoup
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = '7347653967:AAFN55SYOSTgMIA61QktcAnpjMX8uYXJG_k'
URL = "https://trouverunlogement.lescrous.fr/tools/36/search"
SEEN_APARTMENTS_FILE = 'seen_apartments.json'

def load_seen_apartments():
    # Crée le fichier s'il n'existe pas
    if not os.path.exists(SEEN_APARTMENTS_FILE):
        with open(SEEN_APARTMENTS_FILE, 'w') as f:
            json.dump([], f)
    with open(SEEN_APARTMENTS_FILE, 'r') as f:
        return set(json.load(f))

def save_seen_apartments(apartments):
    with open(SEEN_APARTMENTS_FILE, 'w') as f:
        json.dump(list(apartments), f)

def get_apartments(page=1):
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    apartments = []
    while True:
        response = requests.get(f"{URL}?page={page}", headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('.fr-card')
        if not cards:
            break

        for card in cards:
            title = card.select_one('.fr-card__title a').get_text(strip=True)
            address = card.select_one('.fr-card__desc').get_text(strip=True)
            details = [detail.get_text(strip=True) for detail in card.select('.fr-card__detail')]
            price = card.select_one('.fr-badge').get_text(strip=True) if card.select_one('.fr-badge') else "Prix non spécifié"
            link = "https://trouverunlogement.lescrous.fr" + card.select_one('.fr-card__title a')['href']
            apartments.append({
                "id": link,  # Utilise le lien comme identifiant unique
                "title": title,
                "address": address,
                "price": price,
                "details": details,
                "link": link
            })

        page += 1
    return apartments

async def start(update, context):
    await update.message.reply_text('Bienvenue ! Je vais vous envoyer la liste des logements CROUS disponibles.')


async def send_new_apartments(context: ContextTypes.DEFAULT_TYPE):
    seen_apartments = load_seen_apartments()
    apartments = get_apartments()
    new_apartments = [apartment for apartment in apartments if apartment['id'] not in seen_apartments]

    if new_apartments:
        print(f"Nouveaux appartements trouvés : {new_apartments}")  # Debug: Log des nouveaux logements trouvés
        message = "🏠 **Nouveaux Logements CROUS Disponibles**\n\n"
        for apartment in new_apartments:
            message += f"**{apartment['title']}**\n"
            message += f"📍 Adresse: {apartment['address']}\n"
            message += f"💰 Prix: {apartment['price']}\n"
            message += f"📜 Détails: {', '.join(apartment['details'])}\n"
            message += f"🔗 [Lien]({apartment['link']})\n\n"

        max_length = 4096
        for i in range(0, len(message), max_length):
            await context.bot.send_message(chat_id=context.job.chat_id, text=message[i:i + max_length], parse_mode='Markdown')

        seen_apartments.update([apartment['id'] for apartment in new_apartments])
        save_seen_apartments(seen_apartments)
        print(f"Logements sauvegardés : {seen_apartments}")  # Debug: Vérifier les logements sauvegardés
    else:
        print("Aucun nouveau logement trouvé.")  # Debug: Indication qu'aucun nouveau logement n'a été trouvé
        await context.bot.send_message(chat_id=context.job.chat_id, text="Aucun nouveau logement trouvé pour le moment.")


async def enable_notifications(update, context):
    chat_id = update.effective_chat.id
    context.job_queue.run_repeating(send_new_apartments, interval=5, first=10, chat_id=chat_id)
    await update.message.reply_text('Vous recevrez les mises à jour pour les nouveaux logements toutes les 5 minutes.')

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("enable", enable_notifications))
    application.run_polling()

if __name__ == '__main__':
    main()
