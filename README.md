# Research Brief

Research Brief is a small Windows desktop app for researching a subject of your choice. Enter a topic, let the agent search the web, and read a concise summary with links to its sources.

## Features

- Search for any subject, not only technology.
- Search DuckDuckGo for recent pages and fetch article text when useful.
- Use Groq chat completions to summarize findings in plain language.
- Show the headline, two key points, and sources in a native Tkinter window.
- Click source URLs in the result pane to open them in your browser.
- Save the latest answer to `tech_news_summary.txt` beside the script or executable.
- Package the app as a standalone Windows executable with PyInstaller.

## Requirements

- Windows 10 or later.
- Python 3.9 or later, with Tcl/Tk included (the standard Windows Python installer includes it).
- A Groq API key and internet access.

## Run From Source

Open PowerShell in the project folder and install the Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the desktop app:

```powershell
python tech_news_agent.py
```

If `GROQ_API_KEY` is not set, the app asks for it in a masked dialog. The key is not written to the source file. You may also set `GROQ_API_KEY` in your Windows user environment before starting the app.

Enter a topic in the search field and select **Search** (or press Enter). The search runs in the background while the window remains responsive. Results appear in the briefing pane, and a plain-text copy is saved next to the app.

## Configuration

The default model is `openai/gpt-oss-20b`. To use another model available to your Groq account, set `GROQ_MODEL` before launching the app. For example, in PowerShell for the current session:

```powershell
$env:GROQ_MODEL = "your-available-model-id"
python tech_news_agent.py
```

Model availability and access are controlled by Groq and can change. A `model_not_found` response means the configured model is unavailable to the account or is no longer offered.

## Build A Windows Executable

Install PyInstaller in the same Python environment as the app:

```powershell
python -m pip install pyinstaller
```

Build a single-windowed executable:

```powershell
python -m PyInstaller --noconfirm --windowed --onefile --name ResearchBrief tech_news_agent.py
```

The executable is created at `dist\ResearchBrief.exe`. Copy it to the Desktop or another convenient folder. When the executable runs, the text summary is saved beside it.

## Project Files

- `tech_news_agent.py`: search tools, Groq agent, and Tkinter desktop UI.
- `requirements.txt`: Python runtime dependencies.
- `README.md`: setup, configuration, and packaging instructions.

Generated summaries, local editor settings, build directories, and API-key environment files are excluded from version control.

## Security

- Never commit an API key or paste one into source code, issues, or chat.
- Revoke and replace any key that has been exposed.
- Keep API keys in a protected environment variable or enter them in the app's masked prompt.

## Troubleshooting

- **The key prompt appears each time:** Set `GROQ_API_KEY` in your Windows user environment, then start a new terminal or launch the app again.
- **`model_not_found`:** Set `GROQ_MODEL` to a model currently available to your Groq account.
- **Search results are empty:** Check internet access and try a more specific or broader topic.
- **The app does not start:** Run the source version from PowerShell to see diagnostics, and verify that Python, Tkinter, and the packages in `requirements.txt` are installed in the same environment.