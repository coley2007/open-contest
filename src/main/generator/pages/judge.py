from code.util import register, auth
from code.util.db import Contest, Problem, Submission, User
from code.generator.lib.htmllib import *
from code.generator.lib.page import *

import os
import logging
from datetime import datetime

class ProblemTab(UIElement):
    def __init__(self, x):
        num, prob = x
        self.html = h.li(
            h.a(prob.title, href=f"#tabs-{num}")
        )

icons = {
    "ok": "check",
    "wrong_answer": "times",
    "tle": "clock",
    "runtime_error": "exclamation-triangle",
    "presentation_error": "times",
    "extra_output": "times",
    "incomplete_output": "times",
    "pending": "sync"
}
verdict_name = {
    "ok": "Accepted",
    "wrong_answer": "Wrong Answer",
    "tle": "Time Limit Exceeded",
    "runtime_error": "Runtime Error",
    "presentation_error": "Presentation Error",
    "extra_output": "Extra Output",
    "incomplete_output": "Incomplete Output",
    "pending": "Pending..."
}

def resultOptions(result):
    ans = []
    for res in verdict_name:
        if result == res:
            ans.append(h.option(verdict_name[res], value=res, selected="selected"))
        else:
            ans.append(h.option(verdict_name[res], value=res))
    return ans

def judgedOptions(jResult):
    ans = []
    if jResult == "Review":
        ans.append(h.option("Review", value="Review", selected="selected"))
        ans.append(h.option("Judged", value="Judged"))
    else:
        ans.append(h.option("Review", value="Review"))
        ans.append(h.option("Judged", value="Judged", selected="selected"))
    return ans

class TestCaseTab(UIElement):
    def __init__(self, x, sub):
        num, result = x
        self.html = h.li(
            h.a(href=f"#tabs-{sub.id}-{num}", contents=[
                h.i(cls=f"fa fa-{icons[result]}", title=f"{verdict_name[result]}"),
                f"Sample #{num}"
            ])
        )

class TestCaseData(UIElement):
    def __init__(self, x, sub):
        num, input, output, error, answer = x
        self.html = div(id=f"tabs-{sub.id}-{num}", contents=[
            div(cls="row", contents=[
                div(cls="col-12", contents=[
                    h.h4("Input"),
                    h.code(input.replace(" ", "&nbsp;").replace("\n", "<br/>"))
                ])
            ]),
            div(cls="row", contents=[
                div(cls="col-6", contents=[
                    h.h4("Output"),
                    h.code(output.replace(" ", "&nbsp;").replace("\n", "<br/>"))
                ]),
                div(cls="col-6", contents=[
                    h.h4("Correct Answer"),
                    h.code(answer.replace(" ", "&nbsp;").replace("\n", "<br/>"))
                ])
            ])
        ])

class SubmissionCard(UIElement):
    def __init__(self, submission: Submission, user: User):
        subTime = submission.timestamp
        subStat = submission.submissionStatus
        probName = submission.problem.title
        submission.checkout = user.id
        submission.version += 1
        submission.save()
        curVer = submission.version
        cls = "red" if submission.result != "ok" else ""
        self.html = div(cls="modal-content", contents=[
            div(cls=f"modal-header {cls}", contents=[
                h.h5(
                    f"Submission to {probName} at ",
                    h.span(subTime, cls="time-format")
                ),
                """
                <button type="button" class="close" data-dismiss="modal" aria-label="Close" onclick="removeCheckout('""" + submission.id + """')">
                    <span aria-hidden="true">&times;</span>
                </button>"""
            ]),
            div(cls="modal-body", contents=[
                h.strong("Language: <span class='language-format'>{}</span>".format(submission.language)),
                h.br(),
                h.strong("Result: ",
                    h.select(cls=f"result-choice {submission.id}", onchange=f"changeSubmissionResult('{submission.id}', '{curVer}')", contents=[
                        *resultOptions(submission.result)
                    ])
                ),
                h.br(),
                h.strong("Judged Status: ",
                    h.select(cls=f"result-choice {submission.id}", name="change-judged-status", id="change-judged-status", onchange=f"changeJudgedStatus('{submission.id}')", contents=[
                        *judgedOptions(submission.submissionStatus)
                    ])
                ),
                h.br(),
                h.button("Rejudge", type="button", onclick=f"rejudge('{submission.id}')", cls="btn btn-primary rejudge"),
                h.span(" "),
                h.button("Download", type="button", onclick=f"download('{submission.id}')", cls="btn btn-primary rejudge"),
                h.br(),
                h.br(),
                h.strong("Code:"),
                h.code(submission.code.replace("\n", "<br/>").replace(" ", "&nbsp;"), cls="code"),
                div(cls="result-tabs", id="result-tabs", contents=[
                    h.ul(*map(lambda x: TestCaseTab(x, submission), enumerate(submission.results))),
                    *map(lambda x: TestCaseData(x, submission), zip(range(submission.problem.tests), submission.inputs, submission.outputs, submission.errors, submission.answers))
                ])
            ])
        ])

class ProblemContent(UIElement):
    def __init__(self, x, cont):
        num, prob = x
        subs = filter(lambda sub: sub.problem == prob and cont.start <= sub.timestamp <= cont.end, Submission.all())
        self.html = div(*map(SubmissionCard, subs), id=f"tabs-{num}")

class SubmissionRow(UIElement):
    def __init__(self, sub):
        self.html = h.tr(
            h.td(sub.user.username),
            h.td(sub.problem.title),
            h.td(cls='time-format', contents=sub.timestamp),
            h.td(sub.language),
            h.td(
                h.i("&nbsp;", cls=f"fa fa-{icons[sub.result]}"),
                h.span(verdict_name[sub.result])
            ),
            h.td(sub.submissionStatus), 
            h.td(sub.checkout),
            onclick=f"submissionPopup('{sub.id}', '{sub.checkout}')"
        )

class SubmissionTable(UIElement):
    def __init__(self, contest):
        subs = filter(lambda sub: sub.user.type != "admin" and contest.start <= sub.timestamp <= contest.end, Submission.all())
        self.html = h.table(
            h.thead(
                h.tr(
                    h.th("Name"),
                    h.th("Problem"),
                    h.th("Time"),
                    h.th("Language"),
                    h.th("Result"),
                    h.th("Submission Status"),
                    h.th("Checkout")
                )
            ),
            h.tbody(
                *map(lambda sub: SubmissionRow(sub), subs)
            ),
            id="submissions"
        )

def judge(params, user):
    cont = Contest.getCurrent()
    if not cont:
        return Page(
            h1("&nbsp;"),
            h1("No Contest Available", cls="center")
        )

    return Page(
        h2("Judge Submissions", cls="page-title"),
        div(id="judge-table", contents=[
            SubmissionTable(cont)
        ]),
        div(cls="modal", tabindex="-1", role="dialog", contents=[
            div(cls="modal-dialog", role="document", contents=[
                div(id="modal-content")
            ])
        ])
    )

def judge_submission(params, user):
    return SubmissionCard(Submission.get(params[0]), user)

register.web("/judgeSubmission/([a-zA-Z0-9-]*)", "admin", judge_submission)
register.web("/judge", "admin", judge)
