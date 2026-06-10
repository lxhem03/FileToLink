import re
from os import environ

id_pattern = re.compile(r'^.\d+$')

# Bot information
SESSION = environ.get('SESSION', 'filestreamerobot')
API_ID = int(environ.get('API_ID', '39545686'))
API_HASH = environ.get('API_HASH', '0ed4ebf411d1dc0fc63b821a08ad889b')
BOT_TOKEN = environ.get('BOT_TOKEN', "7512502745:AAGrYncp4MxX94DVelrGYYeWV0_LB7M0aRE")

# Bot settings
PORT = environ.get("PORT", "8080")

# Online Stream and Download
MULTI_CLIENT = True
SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))  # 20 minutes
if 'DYNO' in environ:
    ON_HEROKU = True
else:
    ON_HEROKU = False
URL = environ.get("URL", "")
PERM_URL = environ.get("PERM_URL", "https://improved-casi-tg-guy-7034d8e8.koyeb.app/")
START_IMG = environ.get("START_IMG", "https://files.catbox.moe/lllex3.jpg")

# Admins, Channels & Users
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1002458319512'))
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '1705634892').split()]

# MongoDB information
DATABASE_URI = environ.get('DATABASE_URI', "mongodb+srv://RahulPrince720:Q7qg69E1oH30LT6d@cluster0.fb0ldjk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DATABASE_NAME = environ.get('DATABASE_NAME', "FileXstreamerobot")

# Shortlink Info
SHORTLINK = bool(environ.get('SHORTLINK', False)) # Set True Or False
SHORTLINK_URL = environ.get('SHORTLINK_URL', '')
SHORTLINK_API = environ.get('SHORTLINK_API', '')
