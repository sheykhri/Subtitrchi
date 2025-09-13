import os
import subprocess
import wave
import json
import srt
from datetime import timedelta
from vosk import Model, KaldiRecognizer
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# === Настройки ===
MODEL_PATH = "vosk-model-small-uz-0.22"  # Папка с моделью
TEMP_AUDIO = "temp.wav"

# === Функции ===
def extract_audio(input_file, output_file=TEMP_AUDIO):
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "-vn",
        output_file
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_file

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

    # Формируем субтитры
    subs = []
    for i, w in enumerate(words, start=1):
        subs.append(srt.Subtitle(
            index=i,
            start=timedelta(seconds=w["start"]),
            end=timedelta(seconds=w["end"]),
            content=w["word"]
        ))
    return srt.compose(subs)

# === Telegram handlers ===
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.audio.get_file() if update.message.audio else await update.message.voice.get_file()
    file_path = "input.ogg"
    await file.download_to_drive(file_path)

    # Конвертируем
    extract_audio(file_path, TEMP_AUDIO)

    # Распознаём
    subtitles = transcribe(TEMP_AUDIO)

    # Сохраняем в файл
    output_file = "subtitles.srt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(subtitles)

    # Отправляем обратно
    await update.message.reply_document(open(output_file, "rb"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! 🎤 Menga ovozli xabar yoki audio fayl yuboring, men esa sizga SRT subtitr beraman.")

# === Main ===
def main():
    token = os.getenv("BOT_TOKEN")  # Railway Config vars
    app = Application.builder().token(token).build()

    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.COMMAND, start))

    app.run_polling()

if __name__ == "__main__":
    main()
