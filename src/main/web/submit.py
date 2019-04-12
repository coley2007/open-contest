import os
import logging
from code.util import register
from code.util.db import Submission, Problem, User
import time
import shutil
import re
from uuid import uuid4

MAX_OUTPUT_LENGTH = 1000000
MAX_OUTPUT_DISPLAY_LENGTH = 10000

def addSubmission(probId, lang, code, user, type):
    sub = Submission()
    sub.problem = Problem.get(probId)
    sub.language = lang
    sub.code = code
    sub.result = "pending"
    sub.user = user
    sub.timestamp = time.time() * 1000
    sub.type = type
    sub.submissionStatus = "Review"
    sub.checkout = ""
    if type == "submit":
        sub.save()
    else:
        sub.id = str(uuid4())
    return sub

exts = {
    "c": "c",
    "cpp": "cpp",
    "cs": "cs",
    "java": "java",
    "python2": "py",
    "python3": "py",
    "ruby": "rb",
    "vb": "vb"
}

def readFile(path):
    try:
        with open(path, "rb") as f:
            return f.read(MAX_OUTPUT_LENGTH).decode("utf-8")
    except:
        return None

def strip(text):
    return re.sub("[ \t\r]*\n", "\n", text)

def runCode(sub):
    # Copy the code over to the runner /tmp folder
    extension = exts[sub.language]
    os.mkdir(f"/tmp/{sub.id}")
    with open(f"/tmp/{sub.id}/code.{extension}", "wb") as f:
        f.write(sub.code.encode("utf-8"))
    
    prob = sub.problem
    tests = prob.samples if sub.type == "test" else prob.tests
    
    # Copy the input over to the tmp folder for the runner
    for i in range(tests):
        shutil.copyfile(f"/db/problems/{prob.id}/input/in{i}.txt", f"/tmp/{sub.id}/in{i}.txt")

    # Output files will go here
    os.mkdir(f"/tmp/{sub.id}/out")

    # Run the runner
    if os.system(f"docker run --rm --network=none -m 256MB -v /tmp/{sub.id}/:/source nathantheinventor/open-contest-dev-{sub.language}-runner {tests} {sub.problem.timeLimit} > /tmp/{sub.id}/result.txt") != 0:
        raise Exception("Something went wrong")

    inputs = []
    outputs = []
    answers = []
    errors = []
    results = []
    result = "ok"

    for i in range(tests):
        inputs.append(sub.problem.testData[i].input)
        errors.append(readFile(f"/tmp/{sub.id}/out/err{i}.txt"))
        outputs.append(readFile(f"/tmp/{sub.id}/out/out{i}.txt"))
        answers.append(sub.problem.testData[i].output)
        
        res = readFile(f"/tmp/{sub.id}/out/result{i}.txt")
        if res == "ok" and strip((answers[-1] or "").rstrip()) != strip((outputs[-1] or "").rstrip()):
            res = "wrong_answer"
        if res == None:
            res = "tle"
        if res == "ok" or res == "tle" or res == "runtime_error":
            sub.submissionStatus = "Judged"
        results.append(res)

        # Make result the first incorrect result
        if res != "ok" and result == "ok":
            result = res

    sub.result = result
    if readFile(f"/tmp/{sub.id}/result.txt") == "compile_error\n":
        sub.results = "compile_error"
        sub.delete()
        sub.compile = readFile(f"/tmp/{sub.id}/out/compile_error.txt")
        shutil.rmtree(f"/tmp/{sub.id}", ignore_errors=True)
        return

    sub.results = results
    sub.inputs = inputs
    for index, output in enumerate(outputs):
        outputs[index] = (output[:MAX_OUTPUT_DISPLAY_LENGTH] + '... additional data not displayed ...') if len(output) > MAX_OUTPUT_DISPLAY_LENGTH else output
    sub.outputs = outputs
    sub.answers = answers
    sub.errors = errors

    if sub.type == "submit":
        sub.save()

    shutil.rmtree(f"/tmp/{sub.id}", ignore_errors=True)

def submit(params, setHeader, user):
    probId = params["problem"]
    lang   = params["language"]
    code   = params["code"]
    type   = params["type"]
    submission = addSubmission(probId, lang, code, user, type)
    runCode(submission)
    return submission.toJSON()

def changeResult(params, setHeader, user):
    id = params["id"]
    sub = Submission.get(id)
    if not sub:
        return "Error: incorrect id"
    sub.result = params["result"]
    sub.save()
    return "ok"

def rejudge(params, setHeader, user):
    id = params["id"]
    submission = Submission.get(id)
    if os.path.exists(f"/tmp/{id}"):
        shutil.rmtree(f"/tmp/{id}")
    runCode(submission)
    return submission.result

def changeJudgedStatus(params, setHeader, user):
    id = params["id"]
    submission = Submission.get(id)
    submission.submissionStatus = params["chosenStatus"]
    submission.save()

def removeCheckout(params, setHeader, user):
    id = params["id"]
    submission = Submission.get(id)
    submission.checkout = ""
    submission.save()

def checkCheckout(params, setHeader, user):
    id = params["id"]
    checkout = params["checkout"]
    submission = Submission.get(id)
    checkoutUser = User.get(checkout)
    if checkoutUser.id != user.id:
        return checkoutUser.username
    else:
        return "ok"

def checkSubVersion(params, setHeader, user):
    id = params["id"]
    curVer = int(params["curVer"])
    submission = Submission.get(id)
    if curVer == submission.version:
        return "ok"
    else:
        return "different"

register.post("/checkSubVersion", "admin", checkSubVersion)
register.post("/checkCheckout", "admin", checkCheckout)
register.post("/removeCheckout", "admin", removeCheckout)
register.post("/changeJudgedStatus", "admin", changeJudgedStatus)
register.post("/submit", "loggedin", submit)
register.post("/changeResult", "admin", changeResult)
register.post("/rejudge", "admin", rejudge)
