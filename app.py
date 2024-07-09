import json
from datetime import datetime

from bottle import default_app, route, redirect
import matplotlib.pyplot as plt # type: ignore
import mpld3 # type: ignore

@route('/')
def landing():
    with open('data/assignments.json', encoding="utf8") as f:
        global ass_data
        ass_data = json.load(f)
    redirect("/p1", 303)

@route('/p1')
def assignment_marks():
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

app = default_app()
