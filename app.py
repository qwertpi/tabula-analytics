from datetime import datetime
import json

from bottle import default_app, route, redirect # type: ignore
import matplotlib.pyplot as plt # type: ignore
import mpld3 # type: ignore

BUTTON_STYLE = '''.button {
    display: inline-block;
    background-color: #3C1053;
    color: white;
    padding: 8px 16px;
    border-radius: 12px;
    text-decoration: none;
    font-family: sans-serif;
    margin: inherit}'''

def generate_button(links_to: str, message:str, position: str):
    return (f"<a href='{links_to}' class='button' style='float: {position};'>"+
        f"{message}</a><style>{BUTTON_STYLE}</style>")

def generate_prev_next_buttons(i: int):
    def generate_prev_button(i: int):
        if i == 1:
            return ""
        return generate_button(f"p{i-1}", "‹ Back", "left")

    def generate_next_button(i: int):
        if i == len(PAGES):
            return ""
        return generate_button(f"p{i+1}", "Next ›", "right")

    return generate_prev_button(i) + generate_next_button(i)

ass_data = {}
@route('/')
def landing():
    with open('data/assignments.json', encoding="utf8") as f:
        global ass_data
        ass_data = json.load(f)
    redirect("/p1", 303)

def assignment_marks() -> str:
    plot_data: list[tuple[str, str, datetime, int]] = []
    if not ass_data:
        redirect("/", 303)
    for ass in ass_data["historicAssignments"]:
        if "AEP submissions" in ass['name'] or not ass['hasFeedback']:
            continue

        timestamp = datetime.fromisoformat(ass['studentDeadline'])
        plot_data.append((ass['module']['code'], ass['name'], timestamp,
            ass['feedback']['mark']))

    # Sort by timestamp and generate labels
    x: tuple[datetime,]
    y: tuple[int,]
    labels: tuple[str,]
    x, y, labels = zip(*sorted([
        (t[2], t[3], f"<div class='label'>{t[0]}: {t[1]}</div>")
        for t in plot_data]))

    fig, ax = plt.subplots()
    l1 = ax.plot(x, y, marker='.', linestyle="None")[0]
    plt.xlabel("Deadline")
    plt.ylabel("Mark")
    LABEL_STYLE = ".label{background-color: ghostwhite; border-style: groove;}"
    plugins = [
        mpld3.plugins.PointHTMLTooltip(l1, labels, css=LABEL_STYLE),
        mpld3.plugins.Zoom(button=True, enabled=True)]
    for plugin in plugins:
        mpld3.plugins.connect(fig, plugin)
    return mpld3.fig_to_html(fig)

def empty_test_page():
    return "TO DO"

PAGES = [assignment_marks, empty_test_page, empty_test_page, empty_test_page]
@route('/p<page_number:int>')
def general_page(page_number: int) -> str:
    return PAGES[page_number - 1]() + generate_prev_next_buttons(page_number)
app = default_app()
