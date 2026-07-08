"""Run several requisitions to populate the TruLens dashboard for comparison."""
import os, sys, uuid, logging
sys.path.append(os.path.join(os.getcwd(), "src"))
from app.db.session import SessionLocal
from app.ai.graph_executor import execute_graph_with_audit
from app.db.models.models import AuthClient, RequisitionStatusMaster, RequisitionRequest

logging.basicConfig(level=logging.INFO)

JDS = [
    {"title": "Python Developer", "role": "Software Engineer",
     "jd_text": "Looking for a Python Developer with experience in AWS and Generative AI. Must have 3+ years of experience.",
     "mandatory_skills": ["Python"], "preferred_skills": ["AWS", "GenAI"]},
    {"title": "Frontend Developer", "role": "Software Engineer",
     "jd_text": "Looking for a React Frontend Developer with TypeScript and Node.js. Must have 3+ years of experience.",
     "mandatory_skills": ["React"], "preferred_skills": ["TypeScript", "Node.js"]},
    {"title": "DevOps Engineer", "role": "DevOps",
     "jd_text": "Looking for a DevOps Engineer skilled in Kubernetes, AWS and Terraform. Must have 5+ years of experience.",
     "mandatory_skills": ["Kubernetes"], "preferred_skills": ["AWS", "Terraform"]},
    {"title": "Data Scientist", "role": "Data Science",
     "jd_text": "Looking for a Data Scientist with Python, Machine Learning and PyTorch. Must have 4+ years of experience.",
     "mandatory_skills": ["Python"], "preferred_skills": ["Machine Learning", "PyTorch"]},
]

def run():
    db = SessionLocal()
    client = db.query(AuthClient).first()
    if not client:
        client = AuthClient(client_name="Demo Client", client_code="DEMO",
                            client_secret_hash="hash", is_active=True)
        db.add(client); db.flush()
    if not db.query(RequisitionStatusMaster).filter_by(status_id=1).first():
        db.add(RequisitionStatusMaster(status_id=1, status_key="PENDING",
                                       status_message="Pending")); db.flush()
    db.commit()

    for i, jd in enumerate(JDS, 1):
        rid = str(uuid.uuid4()); cid = "cmp-" + rid[:8]
        db.add(RequisitionRequest(request_id=rid, correlation_id=cid,
                                  auth_client_id=client.id, status=1, client_name="InfoBeans"))
        db.commit()
        state = {"requisition_input": {"request_id": rid, "correlation_id": cid,
                 "job_description": {"title": jd["title"], "role": jd["role"],
                    "client_name": "InfoBeans", "location": ["Pune", "Remote"],
                    "work_mode": ["Hybrid"], "jd_text": jd["jd_text"],
                    "mandatory_skills": jd["mandatory_skills"],
                    "preferred_skills": jd["preferred_skills"],
                    "experience": {"min_months": 36}}}}
        print("\n=== [%d/%d] %s (req %s) ===" % (i, len(JDS), jd["title"], rid[:8]), flush=True)
        try:
            fs = execute_graph_with_audit(state, rid, db)
            print("   evaluated=%s qualified=%s" % (fs.get("total_evaluated", 0),
                  fs.get("total_qualified", 0)), flush=True)
        except Exception as e:
            print("   FAILED: %s" % e, flush=True)
    db.close()
    print("\nDone. Refresh the dashboard to see all rows.", flush=True)

if __name__ == "__main__":
    run()
