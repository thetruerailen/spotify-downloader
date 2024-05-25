import os
import socket
import threading
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from pytube import YouTube
from youtube_search import YoutubeSearch
from pydub import AudioSegment
import curses
import pyfiglet

# Replace with your Spotify API credentials
SPOTIFY_CLIENT_ID = 'SPOTIFY_CLIENT_ID'
SPOTIFY_CLIENT_SECRET = 'SPOTIFY_CLIENT_SECRET'

VERSION = "v1.0.0"

try:
    spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID, 
        client_secret=SPOTIFY_CLIENT_SECRET
    ))
except Exception as e:
    print(f"Error initializing Spotify client: {e}")
    spotify = None

# Chat server configuration
CHAT_SERVER_IP = '37.114.53.29'
CHAT_SERVER_PORT = 5000

def search_youtube(query):
    """Search YouTube and return the first result."""
    results = YoutubeSearch(query, max_results=1).to_dict()
    if not results:
        return None
    return f"https://www.youtube.com{results[0]['url_suffix']}"

def download_video(url, path=""):
    """Download a video from YouTube."""
    yt = YouTube(url)
    video_stream = yt.streams.filter(only_audio=True).first()
    video_stream.download(output_path=path)
    return video_stream.default_filename

def convert_to_mp3(filename, path="./"):
    """Convert the downloaded video to MP3."""
    video_path = os.path.join(path, filename)
    video = AudioSegment.from_file(video_path)

    # Ensure the output path exists
    output_path = os.path.join(path)
    os.makedirs(output_path, exist_ok=True)

    audio_filename = os.path.splitext(filename)[0] + ".mp3"
    audio_path = os.path.join(output_path, audio_filename)

    video.export(audio_path, format="mp3")
    os.remove(video_path)  # Remove the original video file

    return audio_filename

def download_song_by_search(song_name, path=""):
    """Download a song by searching its name on YouTube."""
    video_url = search_youtube(song_name + " song audio")
    if video_url:
        video_filename = download_video(video_url, path)
        return convert_to_mp3(video_filename, path)
    else:
        return None

def download_playlist_songs(playlist_url, path=""):
    """Download all songs from a Spotify playlist."""
    results = spotify.playlist_items(playlist_url, additional_types=('track',))
    for item in results['items']:
        track = item['track']
        song_name = track['name']
        artist_name = track['artists'][0]['name']
        download_song_by_search(f"{song_name} {artist_name}", path)

def chat_client_interface(stdscr, nickname):
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    stdscr.clear()
    stdscr.refresh()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((CHAT_SERVER_IP, CHAT_SERVER_PORT))
    client.send(nickname.encode('utf-8'))

    messages = []

    def receive_messages():
        """Receive messages from the server."""
        while True:
            try:
                message = client.recv(1024).decode('utf-8')
                messages.append(message)
                if len(messages) > curses.LINES - 2:
                    messages.pop(0)
                stdscr.clear()
                for idx, msg in enumerate(messages):
                    stdscr.addstr(idx, 0, msg, curses.color_pair(2))
                stdscr.refresh()
            except:
                stdscr.addstr(len(messages), 0, "An error occurred!", curses.color_pair(3))
                stdscr.refresh()
                client.close()
                break

    def send_message(stdscr):
        """Send messages to the server."""
        curses.echo()
        stdscr.addstr(curses.LINES - 1, 0, "You: ")
        message = stdscr.getstr(curses.LINES - 1, 5, 50).decode('utf-8')
        client.send(f'{nickname}: {message}'.encode('utf-8'))
        curses.noecho()
        stdscr.addstr(curses.LINES - 1, 0, " " * (5 + len(message)))
        stdscr.refresh()

    threading.Thread(target=receive_messages).start()

    while True:
        send_message(stdscr)

def main_menu(stdscr):
    """Display the main menu using curses."""
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    stdscr.clear()
    stdscr.refresh()

    # Generate ASCII logo
    ascii_logo = pyfiglet.figlet_format("Spotify Downloader")
    logo_lines = ascii_logo.split('\n')
    logo_height = len(logo_lines)

    menu = ['Download Spotify Playlist', 'Download Song by Search', 'Chat', 'Credits', 'Version: ' + VERSION, 'Exit']
    current_row = 0

    while True:
        stdscr.clear()
        for idx, line in enumerate(logo_lines):
            stdscr.addstr(idx, 0, line, curses.color_pair(2))

        for idx, row in enumerate(menu):
            x = 0
            y = idx + logo_height + 2  # Adjust y to account for logo height and add space
            if idx == current_row:
                stdscr.addstr(y, x, row, curses.color_pair(1))
            else:
                stdscr.addstr(y, x, row)

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == 0:
                playlist_id = curses_ask_input(stdscr, "Enter the Spotify Playlist URL or ID: ")
                download_path = curses_ask_input(stdscr, "Enter the download path (leave blank for current directory): ")
                download_playlist_songs(playlist_id, download_path)
                stdscr.addstr(len(menu) + logo_height + 3, 0, "Download complete. Press any key to continue.", curses.color_pair(2))
                stdscr.getch()
            elif current_row == 1:
                song_name = curses_ask_input(stdscr, "Enter the name of the song you want to download: ")
                download_path = curses_ask_input(stdscr, "Enter the download path (leave blank for current directory): ")
                download_song_by_search(song_name, download_path)
                stdscr.addstr(len(menu) + logo_height + 3, 0, "Download complete. Press any key to continue.", curses.color_pair(2))
                stdscr.getch()
            elif current_row == 2:
                nickname = curses_ask_input(stdscr, "Enter your nickname: ")
                curses.wrapper(chat_client_interface, nickname)
            elif current_row == 3:
                show_credits(stdscr)
            elif current_row == 4:
                break

def show_credits(stdscr):
    stdscr.clear()
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_WHITE)

    credits = ["Credits", "Author: rae", "Github: https://github.com/thetruerailen/spotify-downloader"]
    height, width = stdscr.getmaxyx()

    for idx, line in enumerate(credits):
        if idx >= height:
            break  # Prevent writing outside the screen
        if len(line) > width:
            line = line[:width]  # Trim the line if it's too long
        try:
            stdscr.addstr(idx, 0, line, curses.color_pair(3) if idx == 0 else curses.A_NORMAL)
        except curses.error:
            print(f"Error writing to screen at line {idx}: {line}")

    stdscr.refresh()
    stdscr.getch()

def curses_ask_input(stdscr, prompt):
    """Prompt the user for input in the curses interface."""
    stdscr.clear()
    stdscr.addstr(0, 0, prompt)
    stdscr.refresh()
    curses.echo()
    input_value = stdscr.getstr(1, 0, 50).decode('utf-8')
    curses.noecho()
    stdscr.clear()
    stdscr.refresh()
    return input_value

def main():
    """Main function to start the curses application."""
    curses.wrapper(main_menu)

if __name__ == "__main__":
    main()
