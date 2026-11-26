"""Smoke test every SRMS endpoint against a running server."""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SRMS_BASE", "http://localhost:8740")
passed = failed = 0


def call(method, path, body=None, token=None, expect=200):
    global passed, failed
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as res:
            raw = res.read()
            code = res.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        code = e.code
    payload = json.loads(raw) if raw else None
    ok = code == expect
    if ok:
        passed += 1
    else:
        failed += 1
    label = f"{method} {path}"
    detail = "" if ok else f"  expected {expect} got {code}: {str(payload)[:160]}"
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{detail}")
    return payload


def login(role, ident, pw, expect=200):
    return call("POST", "/api/auth/login",
                {"role": role, "identifier": ident, "password": pw}, expect=expect)


print("== auth ==")
admin = login("admin", "admin", "admin123")["token"]
teacher = login("teacher", "T1", "teach123")["token"]
teacher2 = login("teacher", "t2", "teach123")["token"]
student = login("student", "cs101", "stud123")["token"]
student_f = login("student", "CS104", "stud123")["token"]
login("student", "CS101", "nope", expect=401)
login("ghost", "CS101", "stud123", expect=422)
call("GET", "/api/auth/me", token=admin)
call("GET", "/api/auth/me", expect=401)
call("GET", "/api/auth/me", token="garbage.token.here", expect=401)

print("\n== role isolation ==")
call("GET", "/api/admin/overview", token=teacher, expect=403)
call("GET", "/api/teacher/subjects", token=student, expect=403)
call("GET", "/api/student/result", token=admin, expect=403)
call("GET", "/api/admin/students", expect=401)

print("\n== admin overview ==")
ov = call("GET", "/api/admin/overview", token=admin)
print(f"       students={ov['students']} teachers={ov['teachers']} "
      f"subjects={ov['subjects']} pass_rate={ov['pass_rate']}%")
print(f"       distribution={ov['distribution']}")

print("\n== admin students ==")
studs = call("GET", "/api/admin/students", token=admin)
print(f"       {len(studs)} students, first={studs[0]['roll']} {studs[0]['name']}")
new = call("POST", "/api/admin/students",
           {"name": "Test Kumar", "roll": "cs107", "cls": "BCA-3A", "dob": "2004-02-02"},
           token=admin, expect=201)
call("POST", "/api/admin/students",
     {"name": "Dup", "roll": "CS107", "cls": "BCA-3A", "dob": "2004-02-02"},
     token=admin, expect=409)
call("POST", "/api/admin/students",
     {"name": "", "roll": "CS108", "cls": "BCA-3A", "dob": "2004-02-02"},
     token=admin, expect=422)
card = call("GET", f"/api/admin/students/{new['id']}/card", token=admin)
print(f"       new student card: {card['student']['name']} rows={len(card['result']['rows'])}")
call("DELETE", f"/api/admin/students/{new['id']}", token=admin, expect=204)
call("DELETE", f"/api/admin/students/{new['id']}", token=admin, expect=404)

print("\n== admin subjects ==")
subs = call("GET", "/api/admin/subjects", token=admin)
print(f"       {[s['name'] for s in subs['subjects']]}")
print(f"       teachers={subs['teachers']}")
ns = call("POST", "/api/admin/subjects",
          {"name": "Cloud Computing", "max_marks": 80, "teacher_id": "T1"},
          token=admin, expect=201)
call("PATCH", f"/api/admin/subjects/{ns['id']}/teacher", {"teacher_id": "T9"}, token=admin, expect=404)
call("PATCH", f"/api/admin/subjects/{ns['id']}/teacher", {"teacher_id": "T2"}, token=admin)
call("POST", "/api/admin/subjects", {"name": "Bad", "max_marks": 0}, token=admin, expect=422)

print("\n== admin approvals ==")
appr = call("GET", "/api/admin/approvals", token=admin)
for a in appr:
    print(f"       {a['name']:<24} {a['status']:<10} avg={a['average']}%  {a['teacher']}")
call("POST", "/api/admin/approvals/SUB9/status", {"status": "approved"}, token=admin, expect=404)
# a brand-new subject has no marks at all, so approval must be refused
call("POST", f"/api/admin/approvals/{ns['id']}/status", {"status": "approved"},
     token=admin, expect=409)
call("POST", "/api/admin/approvals/SUB1/status", {"status": "approved"}, token=admin)
call("POST", "/api/admin/approvals/SUB1/status", {"status": "draft"}, token=admin)

print("\n== teacher marks ==")
mine = call("GET", "/api/teacher/subjects", token=teacher)
print(f"       T1 subjects: {[s['name'] + ':' + s['status'] for s in mine]}")
t2subs = call("GET", "/api/teacher/subjects", token=teacher2)
print(f"       T2 subjects: {[s['name'] + ':' + s['status'] for s in t2subs]}")
draft = next(s for s in mine if s["status"] == "draft")["id"]
locked = next(s for s in mine if s["status"] != "draft")["id"]
mk = call("GET", f"/api/teacher/marks?subject_id={draft}", token=teacher)
print(f"       {draft} entries={len(mk['entries'])} locked={mk['locked']}")
mk2 = call("GET", f"/api/teacher/marks?subject_id={locked}", token=teacher)
print(f"       {locked} locked={mk2['locked']}")
call("GET", f"/api/teacher/marks?subject_id={draft}", token=teacher2, expect=404)
call("GET", "/api/teacher/marks?subject_id=SUB2", token=teacher, expect=404)

payload = [{"student_id": e["student_id"], "marks": e["marks"]} for e in mk["entries"]]
payload[0]["marks"] = 91
call("PUT", "/api/teacher/marks", {"subject_id": draft, "action": "draft", "marks": payload}, token=teacher)
after = call("GET", f"/api/teacher/marks?subject_id={draft}", token=teacher)
print(f"       saved marks[0]={after['entries'][0]['marks']} grade={after['entries'][0]['grade']}")
gapped = [dict(e) for e in payload]
gapped[1]["marks"] = None
call("PUT", "/api/teacher/marks", {"subject_id": draft, "action": "submitted", "marks": gapped},
     token=teacher, expect=400)
over = [{"student_id": e["student_id"], "marks": 999} for e in mk["entries"]]
call("PUT", "/api/teacher/marks", {"subject_id": draft, "action": "draft", "marks": over},
     token=teacher, expect=400)
call("PUT", "/api/teacher/marks", {"subject_id": draft, "action": "draft", "marks": payload}, token=teacher)
call("PUT", "/api/teacher/marks", {"subject_id": draft, "action": "submitted", "marks": payload}, token=teacher)
sub = call("GET", f"/api/teacher/marks?subject_id={draft}", token=teacher)
print(f"       after submit: status={sub['status']} locked={sub['locked']}")
call("PUT", "/api/teacher/marks", {"subject_id": draft, "action": "draft", "marks": payload},
     token=teacher, expect=409)
call("POST", f"/api/admin/approvals/{draft}/status", {"status": "approved"}, token=admin)
call("PUT", "/api/teacher/marks", {"subject_id": draft, "action": "draft", "marks": payload},
     token=teacher, expect=409)
call("POST", f"/api/admin/approvals/{draft}/status", {"status": "draft"}, token=admin)
call("PUT", "/api/teacher/marks", {"subject_id": draft, "action": "draft", "marks": payload}, token=teacher)

print("\n== teacher performance ==")
perf = call("GET", "/api/teacher/performance", token=teacher)
for p in perf:
    print(f"       {p['name']:<24} avg={p['average']}% hi={p['highest']}/{p['max']} "
          f"pass={p['pass_rate']}% n={len(p['students'])}")

print("\n== student ==")
res = call("GET", "/api/student/result", token=student)
r = res["result"]
print(f"       {res['student']['name']} {r['percentage']}% CGPA {r['cgpa']} "
      f"total={r['total']}/{r['max']} {'Pass' if r['pass'] else 'Fail'} rows={len(r['rows'])}")
call("GET", "/api/student/card", token=student)
resf = call("GET", "/api/student/result", token=student_f)
rf = resf["result"]
print(f"       {resf['student']['name']} {rf['percentage']}% {'Pass' if rf['pass'] else 'Fail'}")
fails = [x for x in rf["rows"] if x["grade"] == "F"]
print(f"       F rows: {[(x['name'], x['marks']) for x in fails]}")

print("\n== logout-equivalent: deleted student token stops working ==")
tmp = call("POST", "/api/admin/students",
           {"name": "Temp", "roll": "CS999", "cls": "BCA-3A", "dob": "2004-01-01"},
           token=admin, expect=201)
tmp_login = login("student", "CS999", "stud123")["token"]
call("GET", "/api/student/result", token=tmp_login)
call("DELETE", f"/api/admin/students/{tmp['id']}", token=admin, expect=204)
call("GET", "/api/student/result", token=tmp_login, expect=404)

print("\n== a student added later can be graded in the same submit ==")
fresh = call("POST", "/api/admin/students",
             {"name": "Late Joiner", "roll": "CS200", "cls": "BCA-3A", "dob": "2004-06-06"},
             token=admin, expect=201)
late = login("student", "CS200", "stud123")["token"]
d2 = call("GET", "/api/teacher/subjects", token=teacher)
draft2 = next(s for s in d2 if s["status"] == "draft")["id"]
rows2 = call("GET", f"/api/teacher/marks?subject_id={draft2}", token=teacher)
fresh_marks = [{"student_id": e["student_id"], "marks": e["marks"] or 75} for e in rows2["entries"]]
call("PUT", "/api/teacher/marks",
     {"subject_id": draft2, "action": "submitted", "marks": fresh_marks}, token=teacher)
call("POST", f"/api/admin/approvals/{draft2}/status", {"status": "approved"}, token=admin)
after_add = call("GET", "/api/student/result", token=late)
print(f"       {after_add['student']['name']} {after_add['result']['percentage']}% "
      f"CGPA {after_add['result']['cgpa']} over {len(after_add['result']['rows'])} subjects")
call("DELETE", f"/api/admin/students/{fresh['id']}", token=admin, expect=204)
call("GET", "/api/student/result", token=late, expect=404)

print("\n== student self-registration ==")
# A student picks their own roll number and password, and is signed in at once.
reg = call("POST", "/api/auth/register",
           {"roll": "myown01", "name": "My Own", "cls": "BCA-2B",
            "dob": "2005-03-03", "password": "mypass99"}, expect=201)
print(f"       created {reg['user']['id']} as {reg['user']['role']}")
call("POST", "/api/auth/register",
     {"roll": "MYOWN01", "name": "Duplicate", "cls": "BCA-1A",
      "dob": "2005-01-01", "password": "abcdef"}, expect=409)
call("POST", "/api/auth/register",
     {"roll": "ws roll", "name": "Spaces", "cls": "BCA-1A",
      "dob": "2005-01-01", "password": "abcdef"}, expect=201)
call("POST", "/api/auth/register",
     {"roll": "shortpw", "name": "N", "cls": "BCA-1A",
      "dob": "2005-01-01", "password": "12345"}, expect=422)
call("POST", "/api/auth/register",
     {"roll": "blankname", "name": "   ", "cls": "BCA-1A",
      "dob": "2005-01-01", "password": "abcdef"}, expect=422)
call("POST", "/api/auth/register",
     {"roll": "blankcls", "name": "N", "cls": " ",
      "dob": "2005-01-01", "password": "abcdef"}, expect=422)
call("POST", "/api/auth/register",
     {"roll": "x", "name": "N", "cls": "BCA-1A",
      "dob": "2005-01-01", "password": "abcdef"}, expect=422)
call("POST", "/api/auth/register",
     {"roll": "CS1234567890123456789012", "name": "N", "cls": "BCA-1A",
      "dob": "2005-01-01", "password": "abcdef"}, expect=422)
# A role field in the body must not be honoured.
sneaky = call("POST", "/api/auth/register",
              {"roll": "sneaky1", "name": "N", "cls": "BCA-1A", "dob": "2005-01-01",
               "password": "abcdef", "role": "admin"}, expect=201)
assert sneaky["user"]["role"] == "student", sneaky
print("       role:admin in the body was ignored")

own = login("student", "myown01", "mypass99")["token"]
call("GET", "/api/student/result", token=own)
call("GET", "/api/admin/students", token=own, expect=403)
login("student", "myown01", "MYPASS99", expect=401)
login("admin", "myown01", "mypass99", expect=401)

# The new student shows up for staff and can be graded like anyone else.
# A subject of their own, so this block does not depend on a draft being free
# when the late-joiner block above has already approved it.
reg_sub = call("POST", "/api/admin/subjects",
               {"name": "Registration Subject", "max_marks": 100, "teacher_id": "T1"},
               token=admin, expect=201)["id"]
rows3 = call("GET", f"/api/teacher/marks?subject_id={reg_sub}", token=teacher)
mine = next(e for e in rows3["entries"] if e["roll"] == "MYOWN01")
print(f"       self-registered {mine['roll']} found in the marks grid")
graded = [dict(student_id=e["student_id"], marks=(78 if e["roll"] == "MYOWN01" else 80))
          for e in rows3["entries"]]
call("PUT", "/api/teacher/marks",
     {"subject_id": reg_sub, "action": "submitted", "marks": graded}, token=teacher)
call("POST", f"/api/admin/approvals/{reg_sub}/status", {"status": "approved"}, token=admin)
seen = call("GET", "/api/student/result", token=own)
row = next(r for r in seen["result"]["rows"] if r["subject_id"] == reg_sub)
print(f"       {row['name']}: {row['marks']} -> {row['grade']} "
      f"CGPA {seen['result']['cgpa']} pass={seen['result']['pass']}")
assert row["marks"] == 78 and row["grade"] == "B+", row
assert seen["result"]["declared"] is True, seen["result"]
call("GET", "/api/student/card", token=own)

print(f"\n==== {passed} passed, {failed} failed ====")
sys.exit(1 if failed else 0)