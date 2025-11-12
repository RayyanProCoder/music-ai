import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import io
from PIL import Image
import yt_dlp
from googleapiclient.discovery import build
load_dotenv()

try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except TypeError:
    st.error("Gemini API key not found. Please make sure you have a .env file with GOOGLE_API_KEY set.")
    st.stop()


def get_gemini_response(image_data, prompt):
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    try:
        response = model.generate_content([prompt, image_data])
        return response.text
    except Exception as e:
        st.error(f"An error occurred while calling the Gemini API: {e}")
        return None

def find_and_play_song():
    name = st.session_state.get('identified_name')
    entity_type = st.session_state.get('identified_type')

    if not name:
        st.error("Identified name not found in session state.")
        return

    if entity_type == 'Artist':
        search_query = f"{name} official audio"
    elif entity_type == 'Figure':
        search_query = f"{name} devotional music"
    else: 
        search_query = f"{name} music"

    try:
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        if not youtube_api_key:
            st.error("YouTube API key not found. Please add YOUTUBE_API_KEY to your .env file.")
            return

        with st.spinner(f"Searching for music related to {name}..."):
            youtube = build('youtube', 'v3', developerKey=youtube_api_key)
            search_response = youtube.search().list(
                q=search_query,
                part='snippet',
                maxResults=10,
                type='video'
            ).execute()

            all_videos = search_response.get('items', [])
            if not all_videos:
                st.warning(f"Sorry, I couldn't find any music related to {name} on YouTube.")
                return

            # Filter out already played videos
            videos_to_try = [v for v in all_videos if v['id']['videoId'] not in st.session_state.played_video_ids]

            if not videos_to_try:
                st.info(f"Looks like you've heard all the top results I could find for {name}!")
                return

            song_downloaded = False
            for video in videos_to_try:
                video_id = video['id']['videoId']
                video_title = video['snippet']['title']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                thumbnail_url = video['snippet']['thumbnails']['high']['url']

                # Add to played list immediately to avoid retrying it
                st.session_state.played_video_ids.append(video_id)

                cache_dir = "audio_cache"
                os.makedirs(cache_dir, exist_ok=True)
                cached_song_path = os.path.join(cache_dir, f"{video_id}.mp3")

                if os.path.exists(cached_song_path):
                    st.session_state.current_song_file = cached_song_path
                    song_downloaded = True
                else:
                    try:
                        progress_bar = st.progress(0, text=f"Trying: {video_title[:30]}...")

                        def progress_hook(d):
                            if d['status'] == 'downloading':
                                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                                if total_bytes:
                                    progress = d['downloaded_bytes'] / total_bytes
                                    progress_bar.progress(progress, text=f"Downloading... {int(progress * 100)}%")
                            elif d['status'] == 'finished':
                                progress_bar.progress(1.0, text="Download complete, preparing audio...")

                        ydl_opts = {
                            'format': 'bestaudio/best',
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '192',
                            }],
                            'outtmpl': cached_song_path.replace('.mp3', '.%(ext)s'),
                            'quiet': True,
                            'progress_hooks': [progress_hook]
                        }

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([video_url])

                        st.session_state.current_song_file = cached_song_path
                        song_downloaded = True
                        progress_bar.empty()
                    except yt_dlp.utils.DownloadError as e:
                        st.write(f"Skipping unavailable video: *{video_title}*")
                        if 'progress_bar' in locals():
                            progress_bar.empty()
                        continue # Try the next video

                if song_downloaded:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(thumbnail_url, use_container_width=True)
                    with col2:
                        st.write(f"**🎵 Now Playing:**")
                        st.write(f"*{video_title}*")
                    break # Exit the loop on success

            if not song_downloaded:
                st.warning(f"Sorry, I tried several top results for {name} but couldn't find a playable video.")

    except Exception as e:
        st.error(f"An error occurred while trying to play the song: {e}")
        st.info("If this keeps happening, click below to open the song directly on YouTube:")
        st.markdown(f"[Open on YouTube](https://www.youtube.com/results?search_query={name.replace(' ', '+')})")

st.set_page_config(page_title="Music AI", page_icon="🎤", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Poppins', sans-serif;
    }

    .stApp {
        background-color: #121212;
        color: #ffffff;
    }

    .main-card {
        background: #1e1e1e;
        padding: 0.1rem 0.1rem;
        border-radius: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        border: 1px solid rgba(255, 255, 255, 0.18);
        animation: fadeInUp 0.8s ease-out forwards;
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    h1 {
        font-weight: 700;
        text-align: center;
        color: #ffffff;
        margin-bottom: 1rem;
    }

    .st-emotion-cache-1kyxreq {
        border-color: rgba(255, 255, 255, 0.3);
        border-radius: 10px;
    }

    .stImage img {
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }

    div.stButton > button:first-child {
        background-color: #1DB954;
        color: white;
        border-radius: 50px;
        border: none;
        padding: 14px 30px;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease-in-out;
        box-shadow: 0 4px 10px rgba(29, 185, 84, 0.3);
    }

    div.stButton > button:first-child:hover {
        background-color: #1ED760;
        transform: scale(1.05);
        box-shadow: 0 6px 15px rgba(29, 185, 84, 0.4);
    }

    div.stButton > button[kind="secondary"] {
        background-color: rgba(255, 255, 255, 0.1);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 50px;
        padding: 12px 28px;
        font-weight: 600;
        font-size: 16px;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.3);
    }

    .stAudio {
        width: 100%;
    }
    .stAudio > audio {
        width: 100%;
        border-radius: 50px;
        background: #282828;
    }

    .artist-identified {
        background-color: rgba(29, 185, 84, 0.1);
        color: #1DB954;
        padding: 0.75rem 1.25rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 600;
        border: 1px solid rgba(29, 185, 84, 0.2);
    }
</style>
""", unsafe_allow_html=True)

if 'identified_name' not in st.session_state:
    st.session_state.identified_name = None
if 'identified_type' not in st.session_state:
    st.session_state.identified_type = None
if 'played_video_ids' not in st.session_state:
    st.session_state.played_video_ids = []
if 'current_song_file' not in st.session_state:
    st.session_state.current_song_file = None
if 'run_find_song' not in st.session_state:
    st.session_state.run_find_song = False


def reset_search():
    st.session_state.identified_name = None
    st.session_state.identified_type = None
    st.session_state.played_video_ids = []
    st.session_state.current_song_file = None
    st.session_state.run_find_song = False

with st.container():
    st.markdown('<div class="main-card"><h1>🎤 Music AI</h1>', unsafe_allow_html=True)

    if 'identified_name' in st.session_state and st.session_state.identified_name:
        st.markdown(f'<p class="artist-identified">Identified: {st.session_state.identified_name}</p>', unsafe_allow_html=True)
        st.write("")

        if st.session_state.run_find_song:
            find_and_play_song()
            st.session_state.run_find_song = False

        if st.session_state.current_song_file:
            st.audio(st.session_state.current_song_file, format='audio/mp3', autoplay=True)

        st.divider()
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button(f"Play Another Song", use_container_width=True):
                st.session_state.run_find_song = True
                st.session_state.current_song_file = None
                st.rerun()
        with btn_col2:
            if st.button("New Search", on_click=reset_search, use_container_width=True, type="secondary"):
                st.rerun()

    else:
        st.markdown("<p style='text-align: center; color: #b3b3b3;'>Upload an image of a music artist, and I'll find their music.</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
            st.write("")

            if st.button("Identify Artist", use_container_width=True):
                with st.spinner("Identifying..."):
                    prompt = """
                    Analyze the image and identify the primary subject.
                    - If it is a music artist, respond with: Artist: [Name]
                    - If it is a religious figure (like a god, prophet, or spiritual leader), respond with: Figure: [Name]
                    - If it is neither, respond with the exact phrase: 'No match'.
                    Respond with only one of these formats.
                    """
                    response_text = get_gemini_response(image, prompt)

                    if response_text:
                        if response_text.startswith("Artist:"):
                            st.session_state.identified_name = response_text.replace("Artist:", "").strip()
                            st.session_state.identified_type = "Artist"
                            st.session_state.run_find_song = True
                            st.rerun()
                        elif response_text.startswith("Figure:"):
                            st.session_state.identified_name = response_text.replace("Figure:", "").strip()
                            st.session_state.identified_type = "Figure"
                            st.session_state.run_find_song = True
                            st.rerun()
                        else:
                            st.warning("I couldn't identify a music artist or religious figure in this image. Please try another one.")
                    else:
                        st.error("Could not get a response from the model.")

    st.markdown('</div>', unsafe_allow_html=True)
