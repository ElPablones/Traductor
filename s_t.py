import os
import time
import glob
import streamlit as st
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from PIL import Image
from gtts import gTTS
from googletrans import Translator

# --- CONFIGURACIÓN DE IDIOMAS Y ACENTOS ---
LANG_MAP = {
    "Inglés": "en",
    "Español": "es",
    "Francés": "fr",
    "Portugués": "pt",
    "Alemán": "de",
    "Italiano": "it",
    "Bengali": "bn",
    "Coreano": "ko",
    "Mandarín": "zh-cn",
    "Japonés": "ja"
}

MIC_LANG_MAP = {
    "en": "en-US", "es": "es-ES", "fr": "fr-FR", "pt": "pt-BR",
    "de": "de-DE", "it": "it-IT", "bn": "bn-IN", "ko": "ko-KR",
    "zh-cn": "zh-CN", "ja": "ja-JP"
}

ACCENT_MAP = {
    "en": {"Estados Unidos": "com", "Reino Unido": "co.uk", "Australia": "com.au", "Canadá": "ca", "India": "co.in", "Irlanda": "ie", "Sudáfrica": "co.za"},
    "es": {"España": "es", "México": "com.mx", "Estados Unidos": "us"},
    "fr": {"Francia": "fr", "Canadá": "ca"},
    "pt": {"Brasil": "com.br", "Portugal": "pt"}
}

# --- INICIALIZACIÓN DEL ESTADO ---
if "spoken_text" not in st.session_state:
    st.session_state.spoken_text = ""

os.makedirs("temp", exist_ok=True)

# --- INTERFAZ DE USUARIO ---
st.title("🎙️ Traductor Inteligente")
st.subheader("Escucho, traduzco y hablo.")

try:
    image = Image.open('OIG7.jpg')
    st.image(image, width=300)
except FileNotFoundError:
    pass

with st.sidebar:
    st.header("Configuración")
    st.write("1. Selecciona los idiomas.\n2. Presiona 'Escuchar' y habla.\n3. Presiona 'Convertir' para traducir y generar el audio.")
    
    in_lang_name = st.selectbox("🗣️ Lenguaje de Entrada", list(LANG_MAP.keys()), index=1)
    out_lang_name = st.selectbox("🌍 Lenguaje de Salida", list(LANG_MAP.keys()), index=0)
    
    input_language = LANG_MAP[in_lang_name]
    output_language = LANG_MAP[out_lang_name]
    
    tld = "com"
    if output_language in ACCENT_MAP:
        accent_name = st.selectbox("📍 Selecciona el acento", list(ACCENT_MAP[output_language].keys()))
        tld = ACCENT_MAP[output_language][accent_name]
    else:
        st.info("Acentos regionales no disponibles para este idioma. Se usará el estándar.")

    display_output_text = st.checkbox("Mostrar texto traducido", value=True)

# --- RECONOCIMIENTO DE VOZ ---
st.write(f"**Instrucciones:** Toca el botón y habla en **{in_lang_name}**.")

mic_lang_code = MIC_LANG_MAP.get(input_language, "es-ES")

stt_button = Button(label="Escuchar  🎤", width=300, height=50)
stt_button.js_on_event("button_click", CustomJS(code=f"""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = '{mic_lang_code}'; 
 
    recognition.onresult = function (e) {{
        var value = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {{
            if (e.results[i].isFinal) {{
                value += e.results[i][0].transcript;
            }}
        }}
        if (value != "") {{
            document.dispatchEvent(new CustomEvent("GET_TEXT", {{detail: value}}));
        }}
    }}
    
    recognition.onend = function() {{
        console.log("Reconocimiento detenido");
    }}
    
    recognition.start();
"""))

result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT",
    key="listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0
)

if result and "GET_TEXT" in result:
    st.session_state.spoken_text = result.get("GET_TEXT")

if st.session_state.spoken_text:
    st.info(f"**Escuchado:** {st.session_state.spoken_text}")

# --- TRADUCCIÓN Y SÍNTESIS DE VOZ ---
def text_to_speech(in_lang, out_lang, text, tld_code):
    translator = Translator()
    translation = translator.translate(text, src=in_lang, dest=out_lang)
    trans_text = translation.text
    
    tts = gTTS(trans_text, lang=out_lang, tld=tld_code, slow=False)
    file_name = f"audio_{int(time.time())}"
    file_path = f"temp/{file_name}.mp3"
    tts.save(file_path)
    
    return file_path, trans_text

if st.button("🔄 Convertir y Traducir"):
    if st.session_state.spoken_text == "":
        st.warning("Primero debes grabar un mensaje de voz.")
    else:
        with st.spinner('Traduciendo y generando audio...'):
            try:
                audio_path, output_text = text_to_speech(
                    input_language, 
                    output_language, 
                    st.session_state.spoken_text, 
                    tld
                )
                
                st.success("¡Traducción completada!")
                
                if display_output_text:
                    st.markdown(f"### Texto en {out_lang_name}:")
                    st.write(f"> {output_text}")
                
                st.markdown("### Tu audio:")
                with open(audio_path, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format="audio/mp3", start_time=0)
                    
            except Exception as e:
                st.error(f"Hubo un error en la traducción: {e}")

# --- LIMPIEZA DE ARCHIVOS TEMPORALES ---
def remove_old_files(days=1):
    mp3_files = glob.glob("temp/*.mp3")
    now = time.time()
    n_seconds = days * 86400
    for f in mp3_files:
        if os.stat(f).st_mtime < now - n_seconds:
            try:
                os.remove(f)
            except Exception:
                pass

remove_old_files(1)
