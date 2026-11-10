"""Creates a small demo Git repo (./demo_repo) with commits in the last 6 days.
Cross-platform Python replacement for make_demo_repo.sh.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


def run():
    target = Path("demo_repo")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()

    now = datetime.now(timezone.utc)

    def git(*args: str, when: datetime | None = None):
        env = os.environ.copy()
        if when:
            stamp = when.isoformat()
            env["GIT_AUTHOR_DATE"] = stamp
            env["GIT_COMMITTER_DATE"] = stamp
        subprocess.run(["git", *args], cwd=target, check=True, capture_output=True, env=env)

    git("init", "-q", "-b", "main")
    git("config", "user.name", "Demo Dev")
    git("config", "user.email", "demo@example.com")

    for d in ["routes", "controllers", "models", "components", "tests"]:
        (target / d).mkdir(parents=True, exist_ok=True)

    def commit(days_ago: float, msg: str):
        git("add", "-A")
        when = now - timedelta(days=days_ago)
        git("commit", "-q", "-m", msg, when=when)

    # 0) initial setup
    (target / "README.md").write_text("# DevHire - student job portal\n", encoding="utf-8")
    (target / "package.json").write_text('{\n  "name": "devhire"\n}\n', encoding="utf-8")
    commit(20, "chore: initial project setup")

    # 1) feat(auth)
    (target / "routes" / "auth.js").write_text("""const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const router = express.Router();

router.post('/register', async (req, res) => {
  const hash = await bcrypt.hash(req.body.password, 10);
  const user = await User.create({ email: req.body.email, password: hash });
  res.status(201).json({ id: user._id });
});

router.post('/login', async (req, res) => {
  const user = await User.findOne({ email: req.body.email });
  const ok = user.password === req.body.password;
  if (!ok) return res.status(401).send('Invalid');
  const token = jwt.sign({ id: user._id }, process.env.SECRET, { expiresIn: '1d' });
  res.json({ token });
});

module.exports = router;
""", encoding="utf-8")

    (target / "tests" / "auth.test.js").write_text("""test('register creates user', async () => { /* ... */ });
test('login returns token', async () => { /* ... */ });
test('login rejects wrong password', async () => { /* ... */ });
""", encoding="utf-8")

    (target / "package-lock.json").write_text("\n".join(f'"pkg-{i}": "1.0.0",' for i in range(1, 401)) + "\n", encoding="utf-8")
    commit(6, "feat(auth): add JWT login with bcrypt")

    # 2) fix(auth)
    (target / "controllers" / "authController.js").write_text("""exports.login = async (req, res) => {
  const user = await User.findOne({ email: req.body.email });
  if (!user) return res.status(401).send('Invalid');
  const ok = await bcrypt.compare(req.body.password, user.password);
  if (!ok) return res.status(401).send('Invalid');
  res.json({ token: sign(user) });
};
""", encoding="utf-8")

    auth_js = (target / "routes" / "auth.js").read_text(encoding="utf-8")
    auth_js = auth_js.replace("const ok = user.password === req.body.password;", "const ok = await bcrypt.compare(req.body.password, user.password);")
    (target / "routes" / "auth.js").write_text(auth_js, encoding="utf-8")
    commit(5, "fix(auth): handle null user in login")

    # 3) perf(db)
    (target / "models" / "Application.js").write_text("""const schema = new Schema({ userId: ObjectId, jobId: ObjectId, status: String });
schema.index({ userId: 1 });
module.exports = model('Application', schema);
""", encoding="utf-8")
    commit(4, "perf(db): add index on user_id")

    # 4) feat(jobs)
    (target / "routes" / "jobs.js").write_text("""router.get('/jobs', async (req, res) => {
  const { q, location, type } = req.query;
  const filter = {};
  if (q) filter.title = new RegExp(q, 'i');
  if (location) filter.location = location;
  if (type) filter.type = type;
  const jobs = await Job.find(filter).limit(50);
  res.json(jobs);
});
""", encoding="utf-8")

    (target / "components" / "JobList.jsx").write_text("""export default function JobList({ jobs, filters, onFilter }) {
  return (
    <div>
      <FilterBar value={filters} onChange={onFilter} />
      {jobs.map(j => <JobCard key={j._id} job={j} />)}
    </div>
  );
}
""", encoding="utf-8")
    commit(3, "feat(jobs): add job search with filters")

    # 5) style(ui)
    (target / "components" / "Navbar.css").write_text(".navbar { background: #1f3a5f; }\n.navbar a { color: #fff; }\n", encoding="utf-8")
    commit(2, "style(ui): update navbar colors")

    # 6) typo
    (target / "README.md").write_text("# DevHire - student job portal.\n", encoding="utf-8")
    commit(2, "fix typo")

    # 7) wip
    (target / "controllers" / "jobsController.js").write_text("// TODO saved jobs\n", encoding="utf-8")
    commit(1, "wip")

    # 8) real merge commit
    git("checkout", "-q", "-b", "dev")
    (target / "docs.md").write_text("// docs\n", encoding="utf-8")
    commit(1, "docs: add notes")
    git("checkout", "-q", "main")
    merge_when = now - timedelta(days=1)
    env = os.environ.copy()
    stamp = merge_when.isoformat()
    env["GIT_AUTHOR_DATE"] = stamp
    env["GIT_COMMITTER_DATE"] = stamp
    subprocess.run(["git", "merge", "-q", "--no-ff", "dev", "-m", "Merge branch 'dev'"], cwd=target, check=True, env=env)

    # 9) unmerged feature branch for work in progress
    git("checkout", "-q", "-b", "feature/job-alerts")
    (target / "routes" / "alerts.js").write_text("// job alerts\n", encoding="utf-8")
    commit(0.5, "feat(alerts): add email alerts for new matching jobs")
    git("checkout", "-q", "main")

    res = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=target, check=True, capture_output=True, text=True)
    print(f"demo_repo created successfully with {res.stdout.strip()} commits.")


if __name__ == "__main__":
    run()
