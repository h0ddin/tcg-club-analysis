from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class ClubReport:
    club_name: str
    source_path: Path
    copied_filename: str


def load_team_analyzer_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("team_subs_analyzer", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load analyzer module from: {script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Club Analysis Index</title>
  <style>
    :root {{
      --bg: #09111a;
      --panel: rgba(12, 19, 29, 0.92);
      --panel-strong: rgba(16, 27, 39, 0.98);
      --line: rgba(157, 196, 255, 0.18);
      --line-strong: rgba(157, 196, 255, 0.34);
      --text: #edf5ff;
      --muted: #8ea4bd;
      --accent: #8be9fd;
      --accent-2: #ffd580;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
      --radius: 20px;
    }}

    * {{
      box-sizing: border-box;
    }}

    html, body {{
      margin: 0;
      min-height: 100%;
      background:
        radial-gradient(circle at top left, rgba(139, 233, 253, 0.10), transparent 30%),
        radial-gradient(circle at top right, rgba(255, 213, 128, 0.08), transparent 26%),
        linear-gradient(180deg, var(--bg) 0%, #071018 100%);
      color: var(--text);
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    }}

    body {{
      padding: 20px;
    }}

    .app {{
      display: grid;
      gap: 18px;
      min-height: calc(100vh - 40px);
    }}

    .topbar, .viewer-shell {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
    }}

    .topbar {{
      padding: 18px 20px;
      display: grid;
      gap: 12px;
    }}

    h1, h2, p {{
      margin: 0;
    }}

    .search {{
      width: 100%;
      border: 1px solid var(--line-strong);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.04);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
      outline: none;
    }}

    .search:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(139, 233, 253, 0.14);
    }}

    .club-list {{
      display: flex;
      gap: 10px;
      overflow: auto;
      padding-bottom: 4px;
    }}

    .club-button {{
      min-width: 180px;
      text-align: left;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.03);
      color: var(--text);
      padding: 14px;
      cursor: pointer;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }}

    .club-button:hover {{
      transform: translateY(-1px);
      border-color: var(--line-strong);
      background: rgba(255, 255, 255, 0.06);
    }}

    .club-button.active {{
      border-color: var(--accent);
      background: rgba(139, 233, 253, 0.10);
    }}

    .club-button small {{
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .empty {{
      color: var(--muted);
      padding: 16px;
      border: 1px dashed var(--line);
      border-radius: 14px;
    }}

    .viewer-shell {{
      display: grid;
      grid-template-rows: auto 1fr;
      overflow: hidden;
    }}

    .viewer-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 20px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-strong);
    }}

    .viewer-header h2 {{
      font-size: 24px;
      margin-bottom: 4px;
    }}

    .viewer-subtitle {{
      color: var(--muted);
      font-size: 14px;
    }}

    .viewer-actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .viewer-actions a {{
      color: var(--text);
      text-decoration: none;
      border: 1px solid var(--line-strong);
      border-radius: 999px;
      padding: 10px 14px;
      background: rgba(255, 255, 255, 0.04);
    }}

    iframe {{
      width: 100%;
      height: 100%;
      min-height: 78vh;
      border: 0;
      background: #ffffff;
    }}

    @media (max-width: 960px) {{
      body {{
        padding: 12px;
      }}

      .viewer-shell {{
        min-height: 80vh;
      }}

      .viewer-header {{
        flex-direction: column;
        align-items: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <section class="topbar">
      <input id="search" class="search" type="search" placeholder="Filtruj klub..." autocomplete="off">
      <div id="club-list" class="club-list"></div>
    </section>

    <main class="viewer-shell">
      <div class="viewer-header">
        <div>
          <h2 id="viewer-title">Brak raportow</h2>
          <div id="viewer-subtitle" class="viewer-subtitle">Nie znaleziono zadnych plikow analysis-report.html.</div>
        </div>
        <div class="viewer-actions">
          <a id="open-source" href="#" target="_blank" rel="noopener noreferrer">Otworz raport</a>
        </div>
      </div>
      <iframe id="report-frame" title="Club analysis report"></iframe>
    </main>
  </div>

  <script>
    const reports = {reports_json};
    const clubList = document.getElementById("club-list");
    const searchInput = document.getElementById("search");
    const viewerTitle = document.getElementById("viewer-title");
    const viewerSubtitle = document.getElementById("viewer-subtitle");
    const reportFrame = document.getElementById("report-frame");
    const openSource = document.getElementById("open-source");

    let activeIndex = reports.length ? 0 : -1;

    function renderList(filterText = "") {{
      const filter = filterText.trim().toLowerCase();
      clubList.innerHTML = "";

      const visible = reports
        .map((report, index) => ({{ report, index }}))
        .filter((entry) => entry.report.club_name.toLowerCase().includes(filter));

      if (!visible.length) {{
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = reports.length
          ? "Brak klubow pasujacych do filtra."
          : "Brak raportow do wyswietlenia.";
        clubList.appendChild(empty);
        return;
      }}

      for (const entry of visible) {{
        const button = document.createElement("button");
        button.type = "button";
        button.className = "club-button";
        if (entry.index === activeIndex) {{
          button.classList.add("active");
        }}

        button.innerHTML = `<strong>${{entry.report.club_name}}</strong><small>${{entry.report.copied_filename}}</small>`;
        button.addEventListener("click", () => selectReport(entry.index, filterText));
        clubList.appendChild(button);
      }}
    }}

    function selectReport(index, currentFilter = searchInput.value) {{
      activeIndex = index;
      const report = reports[index];

      viewerTitle.textContent = report.club_name;
      viewerSubtitle.textContent = report.source_path;
      reportFrame.src = report.copied_filename;
      openSource.href = report.copied_filename;

      renderList(currentFilter);
    }}

    searchInput.addEventListener("input", (event) => {{
      renderList(event.target.value);
    }});

    if (reports.length) {{
      selectReport(0);
    }} else {{
      openSource.setAttribute("aria-disabled", "true");
      openSource.removeAttribute("href");
      reportFrame.srcdoc = "<!DOCTYPE html><html lang=\\"pl\\"><body style=\\"font-family:Segoe UI,sans-serif;padding:32px;\\"><h1>Brak raportow</h1><p>W katalogu źródłowym nie znaleziono żadnych plików analysis-report.html.</p></body></html>";
      renderList();
    }}
  </script>
</body>
</html>
"""


def discover_reports(clubs_dir: Path) -> list[ClubReport]:
    reports: list[ClubReport] = []
    for report_path in sorted(clubs_dir.glob("*/analysis-report.html")):
        reports.append(
            ClubReport(
                club_name=report_path.parent.name,
                source_path=report_path,
                copied_filename=f"{report_path.parent.name}-analysis-report.html",
            )
        )
    return reports


def club_has_players(club_dir: Path) -> bool:
    players_dir = club_dir / "players"
    if not players_dir.is_dir():
        return False

    return any(
        path.is_file() and not path.name.lower().startswith("analysis-report")
        for path in players_dir.glob("*.txt")
    )


def get_club_directories_with_players(clubs_dir: Path) -> list[Path]:
    return [
        club_dir
        for club_dir in sorted(path for path in clubs_dir.iterdir() if path.is_dir())
        if club_has_players(club_dir)
    ]


def resolve_single_club(clubs_dir: Path, team_name: str) -> Path | None:
    normalized = team_name.strip().lower()
    for club_dir in get_club_directories_with_players(clubs_dir):
        if club_dir.name.lower() == normalized:
            return club_dir
    return None


def prompt_mode() -> str:
    while True:
        selected = input("Tryb generowania [pojedynczo/wszystkie]: ").strip().lower()
        if selected in {"pojedynczo", "p", "single"}:
            return "single"
        if selected in {"wszystkie", "w", "all"}:
            return "all"
        print("Wpisz: pojedynczo albo wszystkie.")


def prompt_single_club(clubs_dir: Path) -> Path | None:
    available_clubs = get_club_directories_with_players(clubs_dir)
    if not available_clubs:
        return None

    print("Dostepne kluby:")
    for index, club_dir in enumerate(available_clubs, start=1):
        print(f"{index}. {club_dir.name}")

    while True:
        selected = input("Wybierz numer albo nazwe klubu: ").strip()
        if selected.isdigit():
            selected_index = int(selected) - 1
            if 0 <= selected_index < len(available_clubs):
                return available_clubs[selected_index]
        else:
            club_dir = resolve_single_club(clubs_dir, selected)
            if club_dir is not None:
                return club_dir
        print("Nieprawidlowy wybor klubu.")


def refresh_all_club_reports(clubs_dir: Path, analyzer_script: Path) -> None:
    analyzer = load_team_analyzer_module(analyzer_script)

    for club_dir in sorted(path for path in clubs_dir.iterdir() if path.is_dir()):
        if not club_has_players(club_dir):
            print(f"Skipping {club_dir.name}: no player files found.")
            continue

        print(f"Generating reports for: {club_dir.name}")
        try:
            analyzer.analyze_team_directory(club_dir.name, club_dir)
        except Exception as error:
            print(f"Skipping {club_dir.name}: analyzer failed with {error}")


def refresh_single_club_report(club_dir: Path, analyzer_script: Path) -> None:
    analyzer = load_team_analyzer_module(analyzer_script)
    if not club_has_players(club_dir):
        print(f"Skipping {club_dir.name}: no player files found.")
        return

    print(f"Generating reports for: {club_dir.name}")
    try:
        analyzer.analyze_team_directory(club_dir.name, club_dir)
    except Exception as error:
        print(f"Skipping {club_dir.name}: analyzer failed with {error}")


def serialize_reports(reports: Iterable[ClubReport], output_dir: Path) -> str:
    payload = []
    for report in reports:
        payload.append(
            {
                "club_name": report.club_name,
                "source_path": str(report.source_path.relative_to(output_dir.parent)),
                "copied_filename": report.copied_filename,
            }
        )
    return json.dumps(payload, ensure_ascii=False)


def build_html(reports: list[ClubReport], clubs_dir: Path, output_dir: Path) -> str:
    return HTML_TEMPLATE.format(
        report_count=len(reports),
        source_dir=clubs_dir.resolve(),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        reports_json=serialize_reports(reports, output_dir),
    )


def copy_reports(reports: Iterable[ClubReport], output_dir: Path) -> None:
    for report in reports:
        shutil.copyfile(report.source_path, output_dir / report.copied_filename)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a single club-analysis/index.html from club analysis-report.html files."
    )
    parser.add_argument(
        "--clubs-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "round15 - advanced team analyzer" / "clubs",
        help="Directory containing club subdirectories with analysis-report.html files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory where index.html should be written.",
    )
    parser.add_argument(
        "--analyzer-script",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "round15 - advanced team analyzer"
        / "team_subs_analyzer.py",
        help="Path to the team_subs_analyzer.py script used to refresh club reports.",
    )
    parser.add_argument(
        "--mode",
        choices=["single", "all"],
        help="Generation mode. If omitted, the script asks interactively.",
    )
    parser.add_argument(
        "--team",
        help="Club name for --mode single.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clubs_dir = args.clubs_dir.resolve()
    output_dir = args.output_dir.resolve()
    analyzer_script = args.analyzer_script.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    mode = args.mode or prompt_mode()
    if mode == "single":
        if args.team:
            selected_club = resolve_single_club(clubs_dir, args.team)
            if selected_club is None:
                raise SystemExit(f"Nie znaleziono klubu z graczami: {args.team}")
        else:
            selected_club = prompt_single_club(clubs_dir)
            if selected_club is None:
                raise SystemExit("Brak klubow z plikami graczy.")
        refresh_single_club_report(selected_club, analyzer_script)
    else:
        refresh_all_club_reports(clubs_dir, analyzer_script)

    reports = discover_reports(clubs_dir)
    copy_reports(reports, output_dir)
    html = build_html(reports, clubs_dir, output_dir)
    output_path = output_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")

    print(f"Saved {len(reports)} reports to: {output_path}")


if __name__ == "__main__":
    main()
