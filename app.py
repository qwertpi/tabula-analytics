from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
import json
from math import ceil, sqrt

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

def make_subplots(num):
    # 1 -> (1, 1), 2 -> (1, 2), 3 -> (2, 2), 4 -> (2, 2), 5 -> (2, 3), ...
    width = ceil(sqrt(num))
    height = ceil(num/width)
    fig, axs = plt.subplots(height, width, sharex=True, sharey=True,
        squeeze=False, figsize=FIG_SIZE)
    return fig, axs.flatten()

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

    fig, axs = make_subplots(1)
    l1 = axs[0].plot(x, y, marker='.', linestyle="None")[0]
    plt.xlabel("Deadline")
    plt.ylabel("Mark")
    LABEL_STYLE = ".label{background-color: ghostwhite; border-style: groove;}"
    return fig, [
        mpld3.plugins.PointHTMLTooltip(l1, labels, css=LABEL_STYLE),
        mpld3.plugins.Zoom(button=True, enabled=True)]

def get_marks_per_year():
    course_start_date = datetime.strptime(
        gen_data['studentCourseDetails'][0]['beginDate'], "%Y-%m-%d").date()
    course_length = gen_data['studentCourseDetails'][-1]['courseYearLength']
    # This is imprecise but it's ok as no marks fall near the boundaries
    breakpoints = [course_start_date + timedelta(days=i*365)
        for i in range(0, course_length+1)]

    marks_per_year: list[list[int]] = []
    for i in range(1, len(breakpoints)):
        in_year_marks: list[int] = []
        for ass in ass_data["historicAssignments"]:
            if "AEP submissions" in ass['name'] or not ass['hasFeedback']:
                continue

            ass_date = datetime.fromisoformat(ass['studentDeadline']).date()
            if breakpoints[i-1] < ass_date < breakpoints[i]:
                in_year_marks.append(int(ass['feedback']['mark']))
        if in_year_marks:
            marks_per_year.append(in_year_marks)
    return marks_per_year

def generate_mark_bins(min_mark, max_mark):
    # The 20 point marking scale is a natural choice of bins
    TWENTY_POINTS = [0, 12, 25, 32, 38, 42, 45, 48, 52, 55, 58, 62,
        65, 68, 74, 78, 82, 88, 94, 100]
    bins = []
    for i, point in enumerate(TWENTY_POINTS):
        if i != 0 and max_mark <= TWENTY_POINTS[i-1]:
            continue
        if i != len(TWENTY_POINTS) - 1 and min_mark >= TWENTY_POINTS[i+1]:
            continue
        bins.append(point)
    return bins

@mpld3_page
def assignment_marks_hist():
    marks_per_year = get_marks_per_year()

    years = [f"Y{i}" for i in range(1, len(marks_per_year)+1)]
    min_mark = min([min(l) for l in marks_per_year])
    max_mark = max([max(l) for l in marks_per_year])
    bins = generate_mark_bins(min_mark, max_mark)

    fig, axs = make_subplots(len(marks_per_year))
    for ax, marks_in_year in zip(axs, marks_per_year):
        ax.hist(marks_in_year, bins=bins, edgecolor = "black")
    # Padding is required for the bottom to not get cut off
    fig.tight_layout(pad=2)
    return fig, [mpld3.plugins.Zoom(button=True, enabled=True)]

@mpld3_page
def module_marks_hist():
    plot_data: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for module in gen_data['studentCourseDetails'][-1]['moduleRegistrations']:
        if not module.get('mark'):
            continue

        module_meta = module['module']
        plot_data[module['academicYear']].append(
            (module_meta['code'] + ": " + module_meta['name'], module['mark']))

    years = list(sorted(plot_data.keys(), key=lambda x: int(x.split("/")[0])))
    min_mark = min(t[1] for l in plot_data.values() for t in l)
    max_mark = max(t[1] for l in plot_data.values() for t in l)
    bins = generate_mark_bins(min_mark, max_mark)

    fig, axs = make_subplots(len(years))
    for ax, year in zip(axs, years):
        marks_in_year = plot_data[year]
        ax.hist([t[1] for t in marks_in_year], bins=bins, edgecolor = "black")
    # Padding is required for the bottom to not get cut off
    fig.tight_layout(pad=2)
    return fig, [mpld3.plugins.Zoom(button=True, enabled=True)]

PAGES = [assignment_marks_scatter, assignment_marks_hist, module_marks_hist]
@route('/p<page_number:int>')
def general_page(page_number: int) -> str:
    return PAGES[page_number - 1]() + generate_prev_next_buttons(page_number)

app = default_app()
