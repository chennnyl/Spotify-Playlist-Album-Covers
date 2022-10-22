# Spotify-Playlist-Album-Covers
Python script to generate an image containing the covers all unique albums in a given playlist

Make sure you run `python3 -m pip install -r requirements.txt` to install all requirements!

To run the script, create an application with the [Spotify Web API](https://developer.spotify.com/dashboard/login) and fill out `.env` with the appropriate values (easiy obtainable from the Dashboard); you can then run it with `python3 from_spotify_playlist.py`. The album covers can be sourced via multithreading or sequentially (the method is selected during code execution); the latter is preferable for particularly large playlists (>2000 songs) so as to avoid the creation of too many threads pinging the Spotify API all at once.

Example output from Spotify's [Queer as Folk playlist](https://open.spotify.com/playlist/37i9dQZF1DX5TMFhaZc9ov) with 64px covers:
![Output of album grid](https://i.imgur.com/tycIsEG.png)
