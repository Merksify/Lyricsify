@echo off
REM Python 3.11 or 3.12 recommended (winsdk has no wheels for newer versions)
py -3.12 -m venv venv || py -3.11 -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt pyinstaller
pyinstaller --noconsole --onefile --name SpotifyLyrics --icon icon.ico --add-data "index.html;." --collect-all winsdk main.py
echo.
echo Done. Your app: dist\SpotifyLyrics.exe
pause