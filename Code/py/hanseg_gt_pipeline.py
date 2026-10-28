"""Run the full ground-truth pipeline for one case; never raises. usage: hanseg_gt_pipeline.py case_XX"""
import subprocess, sys, os, time, json
case = sys.argv[1]
ROOT = r"D:/2d_3d_regis dataset/New_version"; PY = sys.executable
CODE = f"{ROOT}/Code/py"; W = f"{ROOT}/outputs/hanseg_{case}"; GT = f"{ROOT}/Data/HaN-Seg/GT"
os.makedirs(f"{GT}/_logs", exist_ok=True); os.makedirs(W, exist_ok=True)
log = open(f"{GT}/_logs/{case}.log", "w", encoding="utf-8")
stages = [("register", [f"{CODE}/hanseg_register.py", case, W]), ("segment", [f"{CODE}/hanseg_segment.py", case]),
          ("facial", [f"{CODE}/hanseg_facial.py", case]), ("stage2", [f"{CODE}/hanseg_stage2.py", case]), ("stage3", [f"{CODE}/hanseg_stage3.py", case])]
errors = {}
for name, cmd in stages:
    t = time.time(); log.write(f"\n===== {name} =====\n"); log.flush()
    r = subprocess.run([PY] + cmd, stdout=log, stderr=subprocess.STDOUT)
    log.write(f"[{name}] exit={r.returncode} {time.time()-t:.0f}s\n"); log.flush()
    if r.returncode != 0:
        errors[name] = f"{name} crashed (exit {r.returncode}); see _logs/{case}.log"
        if name in ("register", "segment"): break   # later stages cannot run
r = subprocess.run([PY, f"{CODE}/hanseg_gt_qa_export.py", case], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
log.write("\n===== qa_export =====\n" + r.stdout); log.close()
line = [l for l in r.stdout.splitlines() if l.startswith("STATUS")]
if r.returncode != 0 or not line:
    # QA itself failed: make sure the case still lands in not_usable with the reason
    os.makedirs(f"{GT}/not_usable/{case}", exist_ok=True)
    json.dump({"case": case, "status": "not_usable", "fail_reasons": list(errors.values()) + ["QA/export crashed: " + r.stdout[-400:]]}, open(f"{GT}/not_usable/{case}/report.json", "w"), indent=1)
    print(f"STATUS {case} not_usable | QA crash", flush=True)
else:
    if errors:   # a stage crashed but QA ran: record it in the report and enforce not_usable
        for st in ("usable", "not_usable"):
            p = f"{GT}/{st}/{case}/report.json"
            if os.path.exists(p):
                rep = json.load(open(p)); rep["fail_reasons"] += list(errors.values()); rep["status"] = "not_usable"; json.dump(rep, open(p, "w"), indent=1)
                if st == "usable":
                    import shutil; os.makedirs(f"{GT}/not_usable", exist_ok=True); shutil.rmtree(f"{GT}/not_usable/{case}", ignore_errors=True); shutil.move(f"{GT}/usable/{case}", f"{GT}/not_usable/{case}")
    print(line[0] + (" | stage errors: " + str(list(errors)) if errors else ""), flush=True)
