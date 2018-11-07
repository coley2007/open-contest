from code.util import register
from code.util.db import Contest
import json

def getContests(params, setHeader, user):
    return Contest.allJSON()

def getContest(params, setHeader, user):
    id = params["id"]
    return Contest.get(id).toJSON()

def deleteContest(params, setHeader, user):
    id = params["id"]
    Contest.get(id).delete()
    return "ok"

def editContest(params, setHeader, user):
    id = params.get("id")
    contest = Contest.get(id) or Contest()

    contest.name     = params["name"]
    contest.start    = params["start"]
    contest.end      = params["end"]
    contest.problems = [Problem.get(id) for id in json.loads(params["problems"])]

    contest.save()

    return contest.id

register.post("/getContests", "loggedin", getContests)
register.post("/getContest", "loggedin", getContest)
register.post("/deleteContest", "loggedin", deleteContest)
register.post("/editContest", "loggedin", editContest)


# register.post("/editContest", "admin", async (params) => {
#     const id = params.id;
#     let contest = id ? await Contest.construct(id): new Contest();
    
#     contest.name     = params.name;
#     contest.start    = params.start;
#     contest.end      = params.end;
#     contest.problems = JSON.parse(params.problems);
    
#     await contest.save();

#     return contest.id;
# });