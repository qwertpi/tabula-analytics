from collections import defaultdict
from datetime import date, datetime, timedelta
import json
from math import ceil, sqrt
from typing import Callable, Iterable, Optional, TypeVar

from bottle import default_app, route, redirect # type: ignore
import matplotlib.pyplot as plt # type: ignore
import mpld3 # type: ignore
import numpy as np
from scipy.stats import norm, zscore # type: ignore
from sklearn.linear_model import LinearRegression # type: ignore

SCALE = 0.8
FIG_SIZE = (16*SCALE, 9*SCALE)

PURPLE = "#3C1053"
BLUE   = "#00A9CE"
TEAL   = "#6DCDB8"
RED    = "#CB333B"

# {{}} escapes the {}
BUTTON_STYLE = f'''.button {{
    display: inline-block;
    background-color: {PURPLE};
    color: white;
    padding: 8px 16px;
    border-radius: 12px;
    text-decoration: none;
    font-family: sans-serif;
    margin: inherit}}'''

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
        fig.tight_layout()
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
    # Y2K v2
    year_to_str: Callable[[int], str] = lambda y: str(y % 100).zfill(2)
    for i in range(1, len(breakpoints)):
        in_year: list[U] = []
        start_year: Optional[int] = None
        for el in l:
            if breakpoints[i-1] < get_date(el) < breakpoints[i]:
                in_year.append(map(el))
                start_year = get_date(el).year
                end_year = start_year + 1
        if in_year:
            years.append(f"20{year_to_str(start_year)}/{year_to_str(start_year + 1)}")
            per_year.append(in_year)
    return per_year, years

def general_2d_min_max(l: Iterable[Iterable[T]], map: Callable[[T], U]) -> tuple[U, U]:
    relevant = [map(e) for inner_l in l for e in inner_l]
    return min(relevant), max(relevant)

LABEL_STYLE = ".label{background-color: ghostwhite; border-style: groove;}"

def plot_regression_line(xs: Iterable[datetime], ys: Iterable[int], ax):
    reg_x = [x.timestamp() for x in xs]
    reg_model = LinearRegression().fit(np.array(reg_x).reshape(-1, 1), ys)
    ys_reg = reg_model.predict(np.array(reg_x).reshape(-1, 1))
    err_z = zscore(np.array(ys) - ys_reg)
    if any([abs(z) >= 2 for z in err_z]):
        reduced_xs, reduced_ys = zip(*[(x, y) for x, y, z in zip(xs, ys, err_z)
            if abs(z) < 2])
        return plot_regression_line(reduced_xs, reduced_ys, ax)
    ax.plot(xs, ys_reg, '-', color=BLUE)

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
    plugins: list[mpld3.plugins.PluginBase] = []
    for ax, marks_in_year, year in zip(axs, marks_per_year, years):
        # Sort by timestamp and generate labels
        x: tuple[datetime,]
        y: tuple[int,]
        labels: tuple[str,]
        x, y, labels = zip(*sorted([
            (t[1], t[2], f"<div class='label'>{t[0]}</div>")
            for t in marks_in_year]))

        plot_regression_line(x, y, ax)
        l = ax.plot(x, y, marker='o', color=TEAL, linestyle="None")[0]
        ax.set_title(f"Coursework mark vs time of year ({year})")
        ax.set_xlabel("Deadline")
        ax.set_ylabel("Mark")
        plugins.append(mpld3.plugins.PointHTMLTooltip(l, labels, css=LABEL_STYLE))
    return fig, plugins

@mpld3_page
def assignment_marks_delta_scatter():
    data: list[tuple[date, str, datetime, int]] = []
    base = datetime.today().replace(day=1, month=6, hour=12, minute=0, second=0)
    for ass in ass_data["historicAssignments"]:
        submission_data = ass.get("submission")
        if "AEP submissions" in ass['name'] or not ass['hasFeedback'] or not submission_data:
            continue

        deadline = datetime.fromisoformat(ass['studentDeadline'])
        submission_time = datetime.fromisoformat(
            submission_data['submittedDate'])
        delta = deadline - submission_time
        # matplotlib only handles datetime not timedelta
        delta_as_datetime = base - delta
        mark = int(ass['feedback']['mark'])
        title = f"{ass['module']['code']}: {ass['name']}"
        data.append((deadline.date(), title, delta_as_datetime, mark))
    marks_per_year, years = split_into_years(data, lambda t: t[0], lambda t: t[1:])
    min_mark, max_mark = general_2d_min_max(marks_per_year, lambda t: t[2])

    fig, axs = make_subplots(len(years), False)

    plugins: list[mpld3.plugins.PluginBase] = []
    mark_spread = range(min_mark, max_mark+1)
    for ax, marks_in_year, year in zip(axs, marks_per_year, years):
        # Sort by timestamp and generate labels
        x: tuple[datetime,]
        y: tuple[int,]
        labels: tuple[str,]
        x, y, labels = zip(*sorted([
            (t[1], t[2], f"<div class='label'>{t[0] + "<br>" + t[1].strftime("%X")}</div>")
            for t in marks_in_year]))

        # Zero marker
        ax.plot([base]*len(mark_spread), mark_spread, marker="None", linestyle="--", color=RED)

        plot_regression_line(x, y, ax)
        l = ax.plot(x, y, marker='o', color=TEAL, linestyle="None")[0]
        ax.set_title(f"Coursework mark vs difference between submission time and deadline ({year})")
        ax.set_xlabel("Submission time relative to deadline "+
            "(depicted as if midday 1st June was the deadline)")
        ax.set_ylabel("Mark")
        plugins.append(mpld3.plugins.PointHTMLTooltip(l, labels, css=LABEL_STYLE))
    return fig, plugins

def generate_mark_bins(min_mark, max_mark):
    # The 20 point marking scale is a natural choice of bins
    TWENTY_POINTS = [0, 12, 25, 32, 38, 42, 45, 48, 52, 55, 58, 62,
        65, 68, 74, 78, 82, 88, 94, 100]
    bins: list[int] = []
    for i, point in enumerate(TWENTY_POINTS):
        if i != 0 and max_mark <= TWENTY_POINTS[i-1]:
            continue
        if i != len(TWENTY_POINTS) - 1 and min_mark >= TWENTY_POINTS[i+1]:
            continue
        bins.append(point)
    return bins

def generate_bin_labels(data: list[int], data_to_labels: dict[int, list[str]], bins: list[int]):
    bin_labels: list[str] = []
    lower = bins[0]
    upper: Optional[int] = None
    for upper in bins[1:]:
        bin_labels.append("<br>".join(
            [label for point in range(lower, upper)
                for label in data_to_labels[point]]))
        lower = upper
    bin_labels[-1] += "<br>" + "<br>".join([label for label in data_to_labels[lower]])
    return bin_labels

def plot_histogram_with_labels(data: list[int], bins: list[int], bin_labels: list[str], ax):
    plugins = []
    bars = ax.hist(data, bins=bins, color=BLUE, edgecolor = "black")[2]
    for bar, label in zip(bars.get_children(), bin_labels):
        tooltip = mpld3.plugins.LineHTMLTooltip(bar,
            label=f"<div class='label'>{label}</div>", css=LABEL_STYLE)
        plugins.append(tooltip)
    return plugins

def plot_hist_gaus_model(data: list[int], bins: list[int], ax, **kwargs):
    zs = zscore(data)
    if any([abs(z) >= 2 for z in zs]):
        new_data = [d for d, z in zip(data, zs) if abs(z) < 2]
        return plot_hist_gaus_model(new_data, bins, ax, **kwargs)

    mean, std = norm.fit(data)
    x = range(bins[0], bins[-1]+1)
    y = norm.pdf(x, loc=mean, scale=std)
    scale = ax.get_ylim()[1]/y.max()
    ax.plot(x, scale * y, color=RED, **kwargs)

@mpld3_page
def assignment_marks_hist():
    data: list[tuple[int, str, date]] = []

    for ass in ass_data["historicAssignments"]:
        if "AEP submissions" in ass['name'] or not ass['hasFeedback']:
            continue

        ass_date = datetime.fromisoformat(ass['studentDeadline']).date()
        mark = int(ass['feedback']['mark'])
        data.append((mark, f"{ass['module']['code']}: {ass['name']}", ass_date))

    per_year_data, years = split_into_years(data, lambda t: t[2], lambda t: t[0:2])
    mark_to_ass: list[dict[int, list[str]]] = [defaultdict(list) for _ in years]
    for i, year in enumerate(per_year_data):
        for mark, ass_name in year:
            mark_to_ass[i][mark].append(ass_name)
    marks_per_year = [[key for key, l in d.items() for _ in l]
        for d in mark_to_ass]

    min_mark, max_mark = general_2d_min_max(marks_per_year, lambda x: x)
    bins = generate_mark_bins(min_mark, max_mark)
    fig, axs = make_subplots(len(marks_per_year), True)
    plugins = []
    for ax, marks_in_year, mark_to_ass_in_year, year in zip(
        axs, marks_per_year, mark_to_ass, years):
        labels = generate_bin_labels(marks_in_year, mark_to_ass_in_year, bins)
        plugins += plot_histogram_with_labels(marks_in_year, bins, labels, ax)
        ax.set_title(f"Coursework marks ({year})")
        ax.set_xlabel("Mark")
        ax.set_ylabel("Frequency")
        plot_hist_gaus_model(marks_in_year, bins, ax)
    return fig, plugins

@mpld3_page
def module_marks_hist():
    mark_to_module: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    for module in gen_data['studentCourseDetails'][-1]['moduleRegistrations']:
        if not module.get('mark'):
            continue

        module_name = (module['module']['code'].upper() + ": " +
            module['module']['name'])
        mark_to_module[module['academicYear']][module['mark']].append(module_name)

    plot_data: dict[str, list[int]] = {k: [m for m, l in d.items() for _ in l]
        for k, d in mark_to_module.items()}
    years = list(sorted(plot_data.keys(), key=lambda x: int(x.split("/")[0])))
    min_mark, max_mark = general_2d_min_max(plot_data.values(), lambda t: int(t))
    bins = generate_mark_bins(min_mark, max_mark)

    fig, axs = make_subplots(len(years), True)
    plugins = []
    for ax, year in zip(axs, years):
        marks_in_year = plot_data[year]
        mark_to_module_in_year = mark_to_module[year]
        labels = generate_bin_labels(marks_in_year, mark_to_module_in_year, bins)
        plugins += plot_histogram_with_labels(marks_in_year, bins, labels, ax)
        ax.set_title(f"Module marks (20{year})")
        ax.set_xlabel("Mark")
        ax.set_ylabel("Frequency")
        plot_hist_gaus_model(marks_in_year, bins, ax)
    return fig, plugins

PAGES = [assignment_marks_scatter, assignment_marks_delta_scatter,
    assignment_marks_hist, module_marks_hist]
@route('/p<page_number:int>')
def general_page(page_number: int) -> str:
    if 1 <= page_number <= len(PAGES):
        return PAGES[page_number - 1]() + generate_prev_next_buttons(page_number)
    return "Nice try"

app = default_app()
