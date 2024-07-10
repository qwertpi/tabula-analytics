from collections import Counter
from datetime import date, datetime, timedelta
import json

from bottle import default_app, route, redirect # type: ignore
import matplotlib.pyplot as plt # type: ignore
import mpld3 # type: ignore
import numpy as np
import pandas as pd

SCALE = 0.8
FIG_SIZE = (16*SCALE, 9*SCALE)

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

data_loaded = False

def load_data():
    with open('data/assignments.json', encoding="utf8") as f:
        global ass_data
        ass_data = json.load(f)

    with open('data/me.json', encoding="utf8") as f:
        global gen_data
        gen_data = json.load(f)['member']

    global data_loaded
    data_loaded = True

@route('/')
def landing():
    load_data()
    redirect("/p1", 303)

def mpld3_page(func):
    def wrapper(*args, **kwargs) -> str:
        if not data_loaded:
            load_data()

        fig, plugins = func(*args, **kwargs)
        for plugin in plugins:
            mpld3.plugins.connect(fig, plugin)
        return mpld3.fig_to_html(fig)

    return wrapper

@mpld3_page
def assignment_marks_scatter():
    plot_data: list[tuple[str, str, datetime, int]] = []
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

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    l1 = ax.plot(x, y, marker='.', linestyle="None")[0]
    plt.xlabel("Deadline")
    plt.ylabel("Mark")
    LABEL_STYLE = ".label{background-color: ghostwhite; border-style: groove;}"
    return fig, [
        mpld3.plugins.PointHTMLTooltip(l1, labels, css=LABEL_STYLE),
        mpld3.plugins.Zoom(button=True, enabled=True)]

@mpld3_page
def assignment_marks_bar():
    course_start_date = datetime.strptime(
        gen_data['studentCourseDetails'][0]['beginDate'], "%Y-%m-%d").date()
    course_length = gen_data['studentCourseDetails'][-1]['courseYearLength']

    # This is imprecise but it's ok as no marks fall near the boundaries
    breakpoints = [course_start_date + timedelta(days=i*365)
        for i in range(0, course_length+1)]
    counts: list[Counter[str]] = []
    for i in range(1, len(breakpoints)):
        in_year_marks = []
        for ass in ass_data["historicAssignments"]:
            if "AEP submissions" in ass['name'] or not ass['hasFeedback']:
                continue

            ass_date = datetime.fromisoformat(ass['studentDeadline']).date()
            if breakpoints[i-1] < ass_date < breakpoints[i]:
                in_year_marks.append(ass['feedback']['mark'])
        if in_year_marks:
            counts.append(Counter(in_year_marks))

    marks = range(0, 101)
    df = pd.DataFrame(data=None, columns=[f"Y{i}" for i in range(1, len(counts)+1)], index=marks, dtype=np.int8)
    for year_sub_1, counter in enumerate(counts):
        df[f"Y{year_sub_1 + 1}"] = pd.Series(counter)
    colapsed = df.dropna(how="all")
    min_mark = colapsed.index.min()
    max_mark = colapsed.index.max()
    df = df.fillna(0)

    # Go horizontal then vertical
    # Only tested for up to 4 years
    layout = (max(1, len(counts)//2), min(2, len(counts)))
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    subs = df.plot.bar(ax=ax, xlabel="Mark", ylabel="Frequency",
        subplots=True, sharey=True, layout=layout)
    for sub in subs:
        for sub_ax in sub:
            sub_ax.set_xbound(min_mark-1, max_mark+1)
    # Padding is required for the bottom to not get cut off
    fig.tight_layout(pad=2)
    return fig, [mpld3.plugins.Zoom(button=True, enabled=True)]

PAGES = [assignment_marks_scatter, assignment_marks_bar]
@route('/p<page_number:int>')
def general_page(page_number: int) -> str:
    return PAGES[page_number - 1]() + generate_prev_next_buttons(page_number)

app = default_app()
