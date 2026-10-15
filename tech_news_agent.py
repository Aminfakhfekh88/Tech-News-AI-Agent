import os
import json
import re
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from html import escape
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from groq import Groq

# Utilisation d'un modèle actif valide sur Groq
MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
APP_DIRECTORY = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
OUTPUT_FILE = APP_DIRECTORY / "tech_news_summary.txt"
OUTPUT_HTML = APP_DIRECTORY / "tech_news_dashboard.html"


# Implémentation des outils
def web_search(query: str) -> str:
    """Searches DuckDuckGo and returns top 3 result snippets."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region='wt-wt', max_results=3))
            if not results:
                return "No search results found."
            return json.dumps(results, indent=2)
    except Exception as e:
        return f"Search error: {e}"


def fetch_webpage(url: str) -> str:
    """Fetches text content from a URL and extracts clean paragraphs."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()

        paragraphs = [p.get_text() for p in soup.find_all('p')]
        text = "\n".join(paragraphs)[:2000]
        return text if text else "Could not extract main text."
    except Exception as e:
        return f"Failed to fetch webpage: {e}"


TOOLS = {
    "web_search": web_search,
    "fetch_webpage": fetch_webpage
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search DuckDuckGo for recent technology news.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": "Fetch a webpage and extract its main paragraph text.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"]
            }
        }
    }
]

SYSTEM_PROMPT = """
You are a research summarizer. Search for current, reliable information about the exact subject the user provides.
The user may ask about any subject, not only technology. Do not replace or narrow their subject without a reason.

Use the available tools when you need current news or article details. After gathering enough information, respond directly.

Search Rules:
1. Base each `web_search` query on the user's subject; keep it short and simple (2 to 5 plain keywords).
2. DO NOT use quotes, special operators (OR, AND, site:), or long sentences in web_search.
3. If search results are irrelevant, noisy, or empty, refine your query using broader or alternative keywords.
4. Once you have sufficient news details, provide your Final Answer immediately without running more searches.

Final Answer Format:
Return only this clean plain-text structure, with no thought process or tool traces:

HEADLINE
<short, specific topic title>

SUMMARY
- <first key point>
- <second key point>

SOURCES
- <article title> - <full URL>

Write for a general reader. Use exactly two short points, explain technical terms simply, and say why each item matters. Include source URLs when available; never invent sources.
"""


def build_dashboard(summary: str) -> str:
        sections = {"HEADLINE": [], "SUMMARY": [], "SOURCES": []}
        current_section = None

        for line in summary.splitlines():
                heading = line.strip().strip("#*: ").upper()
                if heading in sections:
                        current_section = heading
                elif current_section and line.strip():
                        sections[current_section].append(line.strip())

        headline = " ".join(sections["HEADLINE"]) or "Technology news brief"
        points = [line.removeprefix("-").strip() for line in sections["SUMMARY"]]
        sources = [line.removeprefix("-").strip() for line in sections["SOURCES"]]

        point_items = "".join(f"<li>{escape(point)}</li>" for point in points)
        if not point_items:
                point_items = "<li>The agent did not return summary points. See the text file for its response.</li>"

        source_items = []
        for source in sources:
                match = re.search(r"https?://[^\s<>]+", source)
                if match:
                        url = match.group(0).rstrip(".,;)")
                        title = source[:match.start()].strip(" -:\t") or url
                        source_items.append(
                                f'<li><span>{escape(title)}</span>'
                                f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">Open source</a></li>'
                        )
                else:
                        source_items.append(f"<li>{escape(source)}</li>")

        if not source_items:
                source_items.append("<li>No source links were returned.</li>")

        return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(headline)} | Tech Brief</title>
    <style>
        :root {{ color-scheme: light; --paper: #f2f4ef; --ink: #172d2b; --muted: #546765; --line: #cbd5cf; --accent: #087c70; --signal: #c8563d; }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: var(--paper); color: var(--ink); font-family: "Segoe UI", sans-serif; }}
        header {{ background: var(--ink); color: #f8faf6; padding: 34px max(24px, calc((100% - 860px) / 2)); border-bottom: 5px solid var(--signal); }}
        .eyebrow {{ margin: 0 0 14px; color: #9dd5c8; font-size: 13px; font-weight: 700; }}
        h1 {{ max-width: 760px; margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: 36px; line-height: 1.15; font-weight: 500; }}
        .updated {{ margin: 16px 0 0; color: #c3d0cb; font-size: 13px; }}
        main {{ max-width: 860px; margin: 0 auto; padding: 34px 24px 56px; }}
        section {{ padding: 0 0 30px; }}
        section + section {{ padding-top: 25px; border-top: 1px solid var(--line); }}
        h2 {{ margin: 0 0 18px; color: var(--accent); font-size: 14px; font-weight: 750; }}
        .points {{ display: grid; gap: 17px; margin: 0; padding: 0; list-style: none; counter-reset: item; }}
        .points li {{ display: grid; grid-template-columns: 34px 1fr; gap: 12px; align-items: start; font-family: Georgia, "Times New Roman", serif; font-size: 21px; line-height: 1.45; }}
        .points li::before {{ counter-increment: item; content: "0" counter(item); padding-top: 4px; color: var(--signal); font-family: "Segoe UI", sans-serif; font-size: 13px; font-weight: 700; }}
        .sources {{ display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; }}
        .sources li {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px 20px; color: var(--muted); font-size: 14px; }}
        a {{ color: var(--accent); font-weight: 700; text-decoration-thickness: 1px; text-underline-offset: 3px; }}
        footer {{ max-width: 860px; margin: 0 auto; padding: 0 24px 28px; color: var(--muted); font-size: 12px; }}
        @media (max-width: 560px) {{ header {{ padding-top: 26px; padding-bottom: 26px; }} h1 {{ font-size: 30px; }} main {{ padding-top: 26px; }} .points li {{ font-size: 18px; }} }}
    </style>
</head>
<body>
    <header>
        <p class="eyebrow">TECH NEWS / QUICK BRIEF</p>
        <h1>{escape(headline)}</h1>
        <p class="updated">Updated {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
    </header>
    <main>
        <section aria-labelledby="summary-heading">
            <h2 id="summary-heading">What matters</h2>
            <ol class="points">{point_items}</ol>
        </section>
        <section aria-labelledby="sources-heading">
            <h2 id="sources-heading">Sources</h2>
            <ul class="sources">{"".join(source_items)}</ul>
        </section>
    </main>
    <footer>Generated by Tech News Agent</footer>
</body>
</html>
"""


def save_and_open_dashboard(final_answer: str) -> None:
    if not final_answer:
        raise RuntimeError("The model returned an empty final summary.")

    OUTPUT_FILE.write_text(final_answer + "\n", encoding="utf-8")
    OUTPUT_HTML.write_text(build_dashboard(final_answer), encoding="utf-8")
    print(final_answer)
    print(f"\nSummary saved to: {OUTPUT_FILE}")
    print(f"Dashboard saved to: {OUTPUT_HTML}")

    dashboard_url = OUTPUT_HTML.resolve().as_uri()
    if not webbrowser.open(dashboard_url) and os.name == "nt":
        os.startfile(OUTPUT_HTML.resolve())


def run_agent(user_query: str, api_client: Groq, max_turns: int = 5) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]

    print(f"\n🤖 Running Agent on Groq Model: '{MODEL_NAME}'\n" + "="*50)

    for _ in range(max_turns):
        response = api_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump(exclude_none=True))
        tool_calls = assistant_message.tool_calls or []

        if not tool_calls:
            final_answer = (assistant_message.content or "").strip()
            return final_answer

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            if tool_name in TOOLS:
                observation = TOOLS[tool_name](**tool_args)
            else:
                observation = f"Error: Tool '{tool_name}' not found."

            print(f"Observation ({tool_name}): {observation}\n" + "-" * 50)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": observation
            })

        time.sleep(1)
    else:
        messages.append({
            "role": "user",
            "content": "Use the information gathered so far to write the final summary now. Do not call any tools."
        })
        response = api_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
            tools=TOOL_DEFINITIONS,
            tool_choice="none"
        )
        final_answer = (response.choices[0].message.content or "").strip()
        return final_answer


class TechNewsDesktopApp:
    def __init__(self, root: tk.Tk, api_client: Groq):
        self.root = root
        self.api_client = api_client
        self.root.title("Research Brief")
        self.root.geometry("900x740")
        self.root.minsize(680, 560)
        self.root.configure(bg="#edf2ef")

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#edf2ef")
        style.configure("Title.TLabel", background="#edf2ef", foreground="#183532", font=("Segoe UI", 23, "bold"))
        style.configure("Hint.TLabel", background="#edf2ef", foreground="#526662", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background="#edf2ef", foreground="#183532", font=("Segoe UI", 11, "bold"))
        style.configure("Accent.TButton", background="#087c70", foreground="white", font=("Segoe UI", 10, "bold"), padding=(18, 9))
        style.map("Accent.TButton", background=[("disabled", "#8ba7a0"), ("active", "#06665c")])

        container = ttk.Frame(root, style="App.TFrame", padding=(30, 26))
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="RESEARCH DESK", style="Hint.TLabel").pack(anchor="w")
        ttk.Label(container, text="What should I look into?", style="Title.TLabel").pack(anchor="w", pady=(5, 8))
        ttk.Label(
            container,
            text="Enter any topic. The agent will search current sources and explain the key points simply.",
            style="Hint.TLabel",
            wraplength=780
        ).pack(anchor="w", pady=(0, 20))

        search_row = ttk.Frame(container, style="App.TFrame")
        search_row.pack(fill="x", pady=(0, 18))
        self.topic_entry = tk.Entry(
            search_row,
            font=("Segoe UI", 12),
            bg="white",
            fg="#183532",
            insertbackground="#087c70",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#cbd5cf",
            highlightcolor="#087c70"
        )
        self.topic_entry.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 12))
        self.topic_entry.bind("<Return>", self.start_search)
        self.search_button = ttk.Button(search_row, text="Search", style="Accent.TButton", command=self.start_search)
        self.search_button.pack(side="right")

        ttk.Label(container, text="BRIEFING", style="Section.TLabel").pack(anchor="w", pady=(0, 9))
        result_frame = ttk.Frame(container, style="App.TFrame")
        result_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(result_frame)
        scrollbar.pack(side="right", fill="y")
        self.result_box = tk.Text(
            result_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 11),
            bg="white",
            fg="#263d39",
            relief="flat",
            padx=20,
            pady=18,
            spacing1=3,
            spacing3=5,
            cursor="arrow"
        )
        self.result_box.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.result_box.yview)
        self.result_box.tag_configure("heading", foreground="#087c70", font=("Segoe UI", 10, "bold"), spacing1=10)
        self.result_box.tag_configure("bullet", lmargin1=12, lmargin2=30, spacing1=4, spacing3=8)
        self.result_box.tag_configure("link", foreground="#087c70", underline=True)
        self.result_box.insert("1.0", "Your research brief will appear here.")
        self.result_box.configure(state="disabled")

        self.status = tk.StringVar(value="Ready")
        ttk.Label(container, textvariable=self.status, style="Hint.TLabel").pack(anchor="w", pady=(12, 0))
        self.topic_entry.focus_set()

    def start_search(self, _event=None):
        topic = self.topic_entry.get().strip()
        if not topic:
            self.status.set("Enter a topic to search.")
            self.topic_entry.focus_set()
            return

        self.search_button.configure(state="disabled")
        self.status.set(f"Searching for: {topic}")
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", "Searching sources and preparing your brief...")
        self.result_box.configure(state="disabled")
        threading.Thread(target=self.search_topic, args=(topic,), daemon=True).start()

    def search_topic(self, topic: str):
        try:
            summary = run_agent(topic, self.api_client)
            if not summary:
                raise RuntimeError("The agent returned an empty summary.")
            OUTPUT_FILE.write_text(summary + "\n", encoding="utf-8")
        except Exception as error:
            self.root.after(0, self.show_error, str(error))
            return

        self.root.after(0, self.show_summary, summary)

    def show_summary(self, summary: str):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        for line in summary.splitlines():
            cleaned = line.strip()
            if cleaned.upper().strip("#*: ") in {"HEADLINE", "SUMMARY", "SOURCES"}:
                self.result_box.insert("end", cleaned.strip("#*: ") + "\n", "heading")
            elif cleaned.startswith(("- ", "* ")):
                self.result_box.insert("end", "  • " + cleaned[2:] + "\n", "bullet")
            elif cleaned:
                self.result_box.insert("end", cleaned + "\n")
            else:
                self.result_box.insert("end", "\n")

        rendered = self.result_box.get("1.0", "end-1c")
        for index, match in enumerate(re.finditer(r"https?://[^\s<>]+", rendered)):
            url = match.group(0).rstrip(".,;)")
            if not url:
                continue
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.start() + len(url)}c"
            tag = f"source-{index}"
            self.result_box.tag_add(tag, start, end)
            self.result_box.tag_configure(tag, foreground="#087c70", underline=True)
            self.result_box.tag_bind(tag, "<Button-1>", lambda _event, link=url: webbrowser.open(link))
            self.result_box.tag_bind(tag, "<Enter>", lambda _event: self.result_box.configure(cursor="hand2"))
            self.result_box.tag_bind(tag, "<Leave>", lambda _event: self.result_box.configure(cursor="arrow"))

        self.result_box.configure(state="disabled")
        self.search_button.configure(state="normal")
        self.status.set(f"Done. Saved a copy to {OUTPUT_FILE.name}")

    def show_error(self, error: str):
        self.search_button.configure(state="normal")
        self.status.set(f"Search failed: {error}")


def main():
    root = tk.Tk()
    root.withdraw()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        api_key = simpledialog.askstring(
            "Groq API key",
            "Enter your Groq API key. It will not be saved in this script.",
            show="*",
            parent=root
        )
    if not api_key:
        root.destroy()
        return

    try:
        api_client = Groq(api_key=api_key)
    except Exception as error:
        messagebox.showerror("Could not start", str(error), parent=root)
        root.destroy()
        return

    root.deiconify()
    TechNewsDesktopApp(root, api_client)
    root.mainloop()


if __name__ == "__main__":
    main()