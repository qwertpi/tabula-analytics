from collections import defaultdict
from datetime import date, datetime, timedelta
import json
from math import ceil, sqrt
from typing import Callable, TypeVar

from bottle import default_app, route, redirect # type: ignore
import matplotlib.pyplot as plt # type: ignore
import mpld3 # type: ignore

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

def make_subplots(num, sharex):
    # 1 -> (1, 1), 2 -> (1, 2), 3 -> (2, 2), 4 -> (2, 2), 5 -> (2, 3), ...
    width = ceil(sqrt(num))
    height = ceil(num/width)
    fig, axs = plt.subplots(height, width, sharex=sharex, sharey=True,
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
        for plugin in plugins + [mpld3.plugins.Zoom()]:
            mpld3.plugins.connect(fig, plugin)
        # Padding is required for the bottom to not get cut off
        fig.tight_layout(pad=2)
        return mpld3.fig_to_html(fig)

    return wrapper

T = TypeVar("T")
U = TypeVar("U")
def split_into_years(l: list[T], get_date: Callable[[T], date],
    map: Callable[[T], U]):
    course_start_date = datetime.strptime(
        gen_data['studentCourseDetails'][0]['beginDate'], "%Y-%m-%d").date()
    course_length = int(gen_data['studentCourseDetails'][-1]['courseYearLength'])
    # This is imprecise but it's ok as no marks fall near the boundaries
    breakpoints: list[date] = [course_start_date + timedelta(days=i*365)
        for i in range(0, course_length+1)]

    per_year: list[list[U]] = []
    years: list[str] = []
    for i in range(1, len(breakpoints)):
        in_year: list[U] = []
        for el in l:
            if breakpoints[i-1] < get_date(el) < breakpoints[i]:
                in_year.append(map(el))
        if in_year:
            years.append(f"Y{i}")
            per_year.append(in_year)
    return per_year, years

@mpld3_page
def assignment_marks_scatter():
    data: list[tuple[str, datetime, int]] = []
    for ass in ass_data["historicAssignments"]:
        if "AEP submissions" in ass['name'] or not ass['hasFeedback']:
            continue

        timestamp = datetime.fromisoformat(ass['studentDeadline'])
        mark = int(ass['feedback']['mark'])
        title = f"{ass['module']['code']}: {ass['name']}"
        data.append((title, timestamp, mark))
    marks_per_year, years = split_into_years(data, lambda t: t[1].date(), lambda t: t)

    fig, axs = make_subplots(len(years), False)
    LABEL_STYLE = ".label{background-color: ghostwhite; border-style: groove;}"
    plugins: list[mpld3.plugins.PluginBase] = []
    for ax, marks_in_year in zip(axs, marks_per_year):
        # Sort by timestamp and generate labels
        x: tuple[datetime,]
        y: tuple[int,]
        labels: tuple[str,]
        x, y, labels = zip(*sorted([
            (t[1], t[2], f"<div class='label'>{t[0]}</div>")
            for t in marks_in_year]))
        l = ax.plot(x, y, marker='.', linestyle="None")[0]
        plt.xlabel("Deadline")
        plt.ylabel("Mark")
        plugins.append(mpld3.plugins.PointHTMLTooltip(l, labels, css=LABEL_STYLE))
    return fig, plugins

@mpld3_page
def assignment_marks_delta_scatter():
    data: list[tuple[date, str, datetime, int]] = []
    for ass in ass_data["historicAssignments"]:
        submission_data = ass.get("submission")
        if "AEP submissions" in ass['name'] or not ass['hasFeedback'] or not submission_data:
            continue

        deadline = datetime.fromisoformat(ass['studentDeadline'])
        submission_time = datetime.fromisoformat(
            submission_data['submittedDate'])
        delta = deadline - submission_time
        # matplotlib only handles datetime not timedelta
        base = datetime.today().replace(day=1, month=6, hour=12, minute=0, second=0)
        delta_as_datetime = base - delta
        mark = int(ass['feedback']['mark'])
        title = f"{ass['module']['code']}: {ass['name']}"
        data.append((deadline.date(), title, delta_as_datetime, mark))
    marks_per_year, years = split_into_years(data, lambda t: t[0], lambda t: t[1:])
    min_mark = min([t[2]  for l in marks_per_year for t in l])
    max_mark = max([t[2]  for l in marks_per_year for t in l])

    fig, axs = make_subplots(len(years), True)
    LABEL_STYLE = ".label{background-color: ghostwhite; border-style: groove;}"
    plugins: list[mpld3.plugins.PluginBase] = []
    mark_spread = range(min_mark, max_mark+1)
    for ax, marks_in_year in zip(axs, marks_per_year):
        # Sort by timestamp and generate labels
        x: tuple[timedelta,]
        y: tuple[int,]
        labels: tuple[str,]
        x, y, labels = zip(*sorted([
            (t[1], t[2], f"<div class='label'>{t[0] + "<br>" + t[1].strftime("%X")}</div>")
            for t in marks_in_year]))
        l = ax.plot(x, y, marker='.', linestyle="None")[0]
        ax.plot([base]*len(mark_spread), mark_spread, marker="None", linestyle="-")
        ax.xaxis.set_label("Proximity to deadline "+
            "(depicted as if midday 1st June was the deadline)")
        ax.yaxis.set_label("Mark")
        plugins.append(mpld3.plugins.PointHTMLTooltip(l, labels, css=LABEL_STYLE))
    return fig, plugins

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
    data: list[tuple[int, date]] = []
    for ass in ass_data["historicAssignments"]:
        if "AEP submissions" in ass['name'] or not ass['hasFeedback']:
            continue

        ass_date = datetime.fromisoformat(ass['studentDeadline']).date()
        mark = int(ass['feedback']['mark'])
        data.append((mark, ass_date))
    marks_per_year, years = split_into_years(data, lambda t: t[1], lambda t: t[0])

    min_mark = min([min(l) for l in marks_per_year])
    max_mark = max([max(l) for l in marks_per_year])
    bins = generate_mark_bins(min_mark, max_mark)

    fig, axs = make_subplots(len(marks_per_year), True)
    for ax, marks_in_year in zip(axs, marks_per_year):
        ax.hist(marks_in_year, bins=bins, edgecolor = "black")
    return fig, []

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

    fig, axs = make_subplots(len(years), True)
    for ax, year in zip(axs, years):
        marks_in_year = plot_data[year]
        ax.hist([t[1] for t in marks_in_year], bins=bins, edgecolor = "black")
    return fig, []

PAGES = [assignment_marks_scatter, assignment_marks_delta_scatter,
    assignment_marks_hist, module_marks_hist]
@route('/p<page_number:int>')
def general_page(page_number: int) -> str:
    return PAGES[page_number - 1]() + generate_prev_next_buttons(page_number)

app = default_app()
