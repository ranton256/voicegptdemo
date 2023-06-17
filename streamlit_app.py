import streamlit as st
from bokeh.models.widgets import Button
from bokeh.models import CustomJS

from streamlit_bokeh_events import streamlit_bokeh_events

from gtts import gTTS
from io import BytesIO
import base64

import openai

openai.api_key = st.secrets["openai_api_key"]

# This app is from https://levelup.gitconnected.com/i-created-a-voice-chatbot-powered-by-chatgpt-api-here-is-how-6302d555b949
# with some minor changes by me.
# to get bokeh stream events and bokeh to both be happy at once, I had to downgroade bokeh Python package.
# pip install bokeh==2.4
# I also tried manual NPM insteall of BokehJS, which I don't think made a difference.
# % node --version
# v20.0.0
# npm install @bokeh/bokehjs


if 'prompts' not in st.session_state:
    st.session_state['prompts'] = [
        {"role": "system",
         "content": "You are a helpful assistant. Answer as concisely as possible with a little humor expression."}
    ]


def generate_response(prompt):
    st.session_state['prompts'].append({"role": "user", "content": prompt})
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=st.session_state['prompts']
    )

    message = completion.choices[0].message.content
    return message


sound = BytesIO()

st.markdown(
    "This app is based on code by [Yeyu Huang](https://medium.com/@wenbohuang0307) published in an "
    "[article in Level Up Coding](https://levelup.gitconnected.com/i-created-a-voice-chatbot-powered-by-chatgpt-api-here-is-how-6302d555b949)"
    " with some changes to fix dependency issues, use secrets.toml, and autoplay audio response."
)

placeholder = st.container()

placeholder.title("Voice ChatBot Example")

stt_button = Button(label='Speak', button_type='success', margin=(5, 5, 5, 5), width=200)

stt_button.js_on_event("button_click", CustomJS(code="""
    var value = "";
    var rand = 0;
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en';

    document.dispatchEvent(new CustomEvent("GET_ONREC", {detail: 'start'}));

    recognition.onspeechstart = function () {
        document.dispatchEvent(new CustomEvent("GET_ONREC", {detail: 'running'}));
    }
    recognition.onsoundend = function () {
        document.dispatchEvent(new CustomEvent("GET_ONREC", {detail: 'stop'}));
    }
    recognition.onresult = function (e) {
        var value2 = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                value += e.results[i][0].transcript;
                rand = Math.random();

            } else {
                value2 += e.results[i][0].transcript;
            }
        }
        document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: {t:value, s:rand}}));
        document.dispatchEvent(new CustomEvent("GET_INTRM", {detail: value2}));

    }
    recognition.onerror = function(e) {
        document.dispatchEvent(new CustomEvent("GET_ONREC", {detail: 'stop'}));
    }
    recognition.start();
    """))

result = streamlit_bokeh_events(
    bokeh_plot=stt_button,
    events="GET_TEXT,GET_ONREC,GET_INTRM",
    key="listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0)

tr = st.empty()

if 'input' not in st.session_state:
    st.session_state['input'] = dict(text='', session=0)

tr.text_area("**Your input**", value=st.session_state['input']['text'])

# The icon this is using is from https://commons.wikimedia.org/wiki/File:Mic-Animation.gif
# Moughamir, CC BY-SA 4.0 <https://creativecommons.org/licenses/by-sa/4.0>, via Wikimedia Commons

if result:
    if "GET_TEXT" in result:
        if result.get("GET_TEXT")["t"] != '' and result.get("GET_TEXT")["s"] != st.session_state['input']['session']:
            st.session_state['input']['text'] = result.get("GET_TEXT")["t"]
            tr.text_area("**Your input**", value=st.session_state['input']['text'])
            st.session_state['input']['session'] = result.get("GET_TEXT")["s"]

    if "GET_INTRM" in result:
        if result.get("GET_INTRM") != '':
            tr.text_area("**Your input**", value=st.session_state['input']['text'] + ' ' + result.get("GET_INTRM"))

    if "GET_ONREC" in result:
        if result.get("GET_ONREC") == 'start':
            placeholder.image("Mic-Animation.gif")
            st.session_state['input']['text'] = ''
        elif result.get("GET_ONREC") == 'running':
            placeholder.image("Mic-Animation.gif")
        elif result.get("GET_ONREC") == 'stop':
            placeholder.image("Mic-Animation.jpg")
            if st.session_state['input']['text'] != '':
                input = st.session_state['input']['text']
                output = generate_response(input)
                st.write("**ChatBot:**")
                st.write(output)
                st.session_state['input']['text'] = ''

                tts = gTTS(output, lang='en', tld='com')
                tts.write_to_fp(sound)

                # st.audio will not autoplay, so do it by hand.
                #st.audio(sound)

                sound.seek(0)
                sound_bytes = sound.getvalue()

                # st.write(f"len of sound_bytes is {len(sound_bytes)}")
                audio_base64 = base64.b64encode(sound_bytes).decode('utf-8')
                audio_tag = f'<audio style="width: 704px" class="stAudio" controls="true" autoplay="true" src="data:audio/wav;base64,{audio_base64}">'

                st.markdown(audio_tag, unsafe_allow_html=True)

                st.session_state['prompts'].append({"role": "user", "content": input})
                st.session_state['prompts'].append({"role": "assistant", "content": output})
