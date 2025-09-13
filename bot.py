import os
import subprocess
import wave
import json
import srt
import urllib.request
import zipfile
from datetime import timedelta
from vosk import Model, KaldiRecognizer
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

MODEL_PATH = "vosk-model-small-uz-0.22"
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-uz-0.22.zip"


# === Загрузка модели если нет ===
def ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("⚡ Скачиваю модель VOSK...")
        zip_path = "model.zip"
        urllib.request.urlretrieve(MODEL_URL, zip_path)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(".")
        os.remove(zip_path)
        print("✅ Модель готова.")


# === Конвертация аудио ===
def extract_audio(input_file, output_file):
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "-vn",
        output_file
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_file


# === Распознавание ===
def transcribe(audio_path):
    wf = wave.open(audio_path, "rb")
    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    words = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            if "result" in res:
                words.extend(res["result"])

    final_res = json.loads(rec.FinalResult())
    if "result" in final_res:
        words.extend(final_res["result"])

    subs = []
    for i, w in enumerate(words, start=1):
        subs.append(srt.Subtitle(
            index=i,
            start=timedelta(seconds=w["start"]),
            end=timedelta(seconds=w["end"]),
            content=w["word"]
        ))
    return srt.compose(subs)


# === Обработчики ===
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    input_file = f"{user_id}_input.ogg"
    temp_audio = f"{user_id}_temp.wav"
    output_file = f"{user_id}_subtitles.srt"

    try:
        file = await update.message.audio.get_file() if update.message.audio else await update.message.voice.get_file()
        await file.download_to_drive(input_file)

        extract_audio(input_file, temp_audio)
        subtitles = transcribe(temp_audio)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(subtitles)

        await update.message.reply_document(open(output_file, "rb"))

    finally:
        # чистим файлы
        for f in [input_file, temp_audio, output_file]:
            if os.path.exists(f):
                os.remove(f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 🎤 Menga ovozli xabar yoki audio fayl yuboring, men esa sizga SRT subtitr beraman."
    )


# === Main ===
def main():
    ensure_model()

    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))

    app.run_polling()


if __name__ == "__main__":
    main()
