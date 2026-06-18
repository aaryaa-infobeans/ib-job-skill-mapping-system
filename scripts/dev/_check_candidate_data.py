import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

rows = db.execute(text('''
    SELECT allocation_percentage, start_date, end_date, project_id, is_deleted
    FROM team_member_allocation
    WHERE team_member_id = :mid
    ORDER BY start_date DESC
'''), {'mid': '1793'}).fetchall()

print(f'Allocations for 1793 ({len(rows)} records):')
for r in rows:
    print(f'  project_id={r[3]:<15} alloc={r[0]}%  {r[1]} to {r[2]}  deleted={r[4]}')

db.close()
