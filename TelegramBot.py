import requests

TOKEN = '7555446767:AAGJlcrccqzgvcRnlsThfLjP0C0vr83OmK0'
CHAT_ID = '1552822688'

def enviar_msg(msg):
    msg = msg
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}'
    r = requests.get(url)
    return r