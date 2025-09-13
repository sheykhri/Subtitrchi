import requests
import zipfile
import io
import os

# URL модели
url = "https://alphacephei.com/vosk/models/vosk-model-small-uz-0.22.zip"

# Имя папки после распаковки
extract_dir = "vosk-model-small-uz-0.22"

# Скачиваем архив
print("📥 Скачивание модели...")
response = requests.get(url, stream=True)
response.raise_for_status()

# Распаковываем из памяти
with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
    print("📂 Распаковка модели...")
    zip_ref.extractall(".")

# Проверяем результат
if os.path.exists(extract_dir):
    print(f"✅ Модель успешно скачана и распакована в: {extract_dir}")
else:
    print("⚠ Ошибка: папка модели не найдена!")
