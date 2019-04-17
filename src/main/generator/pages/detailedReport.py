from code.util.db import Submission, User, Contest, Problem
from code.generator.lib.htmllib import *
from code.generator.lib.page import *
import logging
from code.util import register
import time
from datetime import datetime, timezone

def detailedReport(params, user):
    contest = Contest.getCurrent() or Contest.getPast()
    if not contest:
        return Page(
            h1("&nbsp;"),
            h1("No Contest Available", cls="center")
        )
    elif contest.scoreboardOff <= time.time() * 1000 and not user.isAdmin():
        return Page(
            h1("&nbsp;"),
            h1("Scoreboard is off.", cls="center")
        )

    start = contest.start
    end = contest.end
    
    subs = {}
    for sub in Submission.all():
        if start <= sub.timestamp <= end and not sub.user.isAdmin():
            subs[sub.user.id] = subs.get(sub.user.id) or []
            subs[sub.user.id].append(sub)            
    
    problemSummary = {}
    for prob in contest.problems:
        problemSummary[prob.id] = [0, 0]

    scores = []
    for user in subs:
        usersubs = subs[user]
        scor = score(usersubs, start, problemSummary)
        scores.append((
            User.get(user).username,
            scor[0],
            scor[1],
            scor[2],
            len(usersubs)
        ))
    scores = sorted(scores, key=lambda score: score[1] * 1000000000 + score[2] * 10000000 - score[3], reverse=True)
    
    ranks = [i + 1 for i in range(len(scores))]
    for i in range(1, len(scores)):
        u1 = scores[i]
        u2 = scores[i - 1]
        if (u1[1], u1[2], u1[3]) == (u2[1], u2[2], u2[3]):
            ranks[i] = ranks[i - 1]
    
    subs = {}
    for sub in Submission.all():
        if start <= sub.timestamp <= end and not sub.user.isAdmin():
            subs[sub.user.id] = subs.get(sub.user.id) or []
            subs[sub.user.id].append(sub)

    pn = 0
    probCount = []
    for i in range(len(contest.problems)):
        pn += 1
        probCount.append(h.th(str(pn)))

    allContestProblems = []
    i = 0
    for prob in contest.problems:
        i += 1
        allContestProblems.append([i, Problem.get(prob.id), 0, 0])

    # Final Summary Display Construction
    finalStandingDisplay = []

    for (name, solved, samples, points, attempts), rank in zip(scores, ranks):
        # iterate over each sub by the person
        curContestantInfo = []
        i = 0
        isOld = False
        for problem in allContestProblems:
            for sub in subs[User.getByName(name).id]:
                if sub.problem.id == problem[1].id:
                    if curContestantInfo != []:
                        for infoBlock in curContestantInfo:
                            if sub.problem.id == infoBlock[0]:
                                isOld = True
                        if isOld:
                            isOld = False
                            for infoBlock in curContestantInfo:
                                if sub.problem.id == infoBlock[0]:
                                    infoBlock[2] = infoBlock[2] + 1
                                    if infoBlock[1] != "--" and sub.result == "ok":
                                        if int(sub.timestamp) > int(infoBlock[1]):
                                            infoBlock[1] = str(sub.timestamp)
                                    elif sub.result == "ok":
                                        infoBlock[1] = str(sub.timestamp)
                        else:
                            if sub.result == "ok":
                                curContestantInfo.append([sub.problem.id, sub.timestamp, 1])
                            else:
                                curContestantInfo.append([sub.problem.id, "--", 1])
                    else:
                        if sub.result == "ok":
                            curContestantInfo.append([sub.problem.id, sub.timestamp, 1])
                        else:
                            curContestantInfo.append([sub.problem.id, "--", 1])

        cciDisplay = []
        noEntries = True
        for problem in allContestProblems:
            for info in curContestantInfo:
                if problem[1].id == info[0]:
                    noEntries = False
                    if info[1] == "--":
                        cciDisplay.append(
                        h.td(f"({str(info[2])}) --", cls="center")
                        )
                    else:
                        cciDisplay.append(
                        # Times are currently set to Eastern with daylight saving (UTC minus four hours).
                        # Remove the "- 14400" in the following lines to change the time back to UTC.
                        h.td(f"({str(info[2])}) {datetime.fromtimestamp((int(info[1])/1000) - 14400).strftime('%H:%M')}", cls="center")
                        )
            if noEntries:
                cciDisplay.append(
                    h.td("  ")
                    )
            noEntries = True
            DispName = name
        if contest.end >= time.time() * 1000:
            DispName = ""
        finalStandingDisplay.append(h.tr(
            h.td(rank, cls="center"),
            h.td(DispName, cls="center"),
            h.td(User.getByName(name).id, cls="center"),
            h.td(solved, cls="center"),
            h.td(points, cls="center"),
            h.td(attempts, cls="center"),
            *cciDisplay
        ))

    # Problem Summary Display Construction
    probSummaryDisplay = []

    allGoodSubs = []
    for sub in Submission.all():
        if start <= sub.timestamp <= end and not sub.user.isAdmin():
            allGoodSubs.append(sub)

    for prob in allContestProblems:
        for sub in allGoodSubs:
            curSub = sub
            if prob[1].id == curSub.problem.id:
                if curSub.result == "ok":
                    prob[2] += 1
                    prob[3] += 1
                else:
                    prob[2] += 1
    
    i = 0
    for x in range(len(allContestProblems)):
        curProb = allContestProblems[i]
        i += 1
        probSummaryDisplay.append(h.tr(
            h.td(curProb[0]),
            h.td(curProb[1].title),
            h.td(curProb[2], cls="center"),
            h.td(curProb[3], cls="center"),
        ))
    # Language Summary Display Construction
    langBreakdownDisplay = []

    allContProbsWithLangNums = []
    i = 0
    for prob in contest.problems:
        i += 1
        allContProbsWithLangNums.append([i, Problem.get(prob.id), 0, 0, 0, 0, 0, 0, 0, 0, 0])

    langIndexForLangDisplay = {'c': 2, 'cpp': 3, 'cs': 4, 'java': 5, 'python2': 6, 'python3': 7, 'ruby': 8, 'vb': 9}

    for prob in allContProbsWithLangNums:
        for sub in allGoodSubs:
            curSub = sub
            if prob[1].id == curSub.problem.id:
                prob[langIndexForLangDisplay[sub.language]] += 1
                prob[10] += 1

    i = 0
    for x in range(len(allContProbsWithLangNums)):
        curProb = allContProbsWithLangNums[i]
        i += 1
        langBreakdownDisplay.append(h.tr(
            h.td(curProb[0]),
            h.td(curProb[1].title),
            h.td(curProb[2], cls="center"),
            h.td(curProb[3], cls="center"),
            h.td(curProb[4], cls="center"),
            h.td(curProb[5], cls="center"),
            h.td(curProb[6], cls="center"),
            h.td(curProb[7], cls="center"),
            h.td(curProb[8], cls="center"),
            h.td(curProb[9], cls="center"),
            h.td(curProb[10], cls="center")
        ))

    return Page(
        h2("Final Standings", cls="page-title"),
        h.table(cls="fs", contents=[
            h.thead(
                h.tr(
                    h.th("Rank"),
                    h.th("Username"),
                    h.th("ID"),
                    h.th("Correct"),
                    h.th("Penalty"),
                    h.th("Attempts"),
                    *probCount
                )
            ),
            h.tbody(
                *finalStandingDisplay
            )
        ]),
        h.p(cls="detRepp", contents=["Each value in parenthesis represents the number of attempts of the given problem for the contestant.", h.br(), "Each time represents the time of the correct submission in Eastern Standard Time.", h.br(), "Username is not shown during the contest."]),
        h2("Problem Summary", cls="page-title"),
        h.table(cls="fs", id="probSummary", contents=[
            h.thead(
                h.tr(
                    h.th("#"),
                    h.th("Title"),
                    h.th("Attempts"),
                    h.th("Correct")
                )
            ),
            h.tbody(
                *probSummaryDisplay
            )
        ]),
        h2("Language Breakdown", cls="page-title"),
        h.p("Correct Submissions by Language"),
        h.table(cls="fs", id="langBreakdown", contents=[
            h.thead(
                h.tr(
                    h.th("#"),
                    h.th("Title"),
                    h.th("C"),
                    h.th("C++"),
                    h.th("C#"),
                    h.th("Java"),
                    h.th("Python 2"),
                    h.th("Python 3"),
                    h.th("Ruby"),
                    h.th("Visual Basic"),
                    h.th("Total")
                )
            ),
            h.tbody(
                *langBreakdownDisplay
            )
        ])
    )
 
def score(submissions: list, contestStart, problemSummary) -> tuple:
    """ Given a list of submissions by a particular user, calculate that user's score.
        Calculates score in ACM format. """
    
    solvedProbs = 0
    sampleProbs = 0
    penPoints = 0

    # map from problems to list of submissions
    probs = {}

    # Put the submissions into the probs list
    for sub in submissions:
        probId = sub.problem.id
        if probId not in probs:
            probs[probId] = []
        probs[probId].append(sub)
    
    # For each problem, calculate how much it adds to the score
    for prob in probs:
        # Sort the submissions by time
        subs = sorted(probs[prob], key=lambda sub: sub.timestamp)
        # Penalty points for this problem
        points = 0
        solved = False
        sampleSolved = False
        
        for sub in subs:
            for res in sub.results[:sub.problem.samples]:
                if res != "ok":
                    break
            else:
                sampleSolved = True
            if sub.result != "ok":
                # Unsuccessful submissions count for 20 penalty points
                # But only if the problem is eventually solved
                points += 20
            else:
                # The first successful submission adds a penalty point for each
                #     minute since the beginning of the contest
                # The timestamp is in millis
                points += (sub.timestamp - contestStart) // 60000
                solved = True
                break
        
        # Increment attempts
        problemSummary[sub.problem.id][0] += 1

        # A problem affects the score only if it was successfully solved
        if solved:
            solvedProbs += 1
            penPoints += points
            problemSummary[sub.problem.id][1] += 1
        elif sampleSolved:
            sampleProbs += 1
    
    # The user's score is dependent on the number of solved problems and the number of penalty points
    return solvedProbs, sampleProbs, int(penPoints)

register.web("/detailedReport", "loggedin", detailedReport)