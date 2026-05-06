# ✅ Pre-Push Validation Guide

## Before You Push to GitHub

Use this checklist to ensure everything is ready for GitHub Actions validation.

---

## 🔍 Pre-Push Checklist (15 minutes)

### Step 1: Local Environment ✓ (2 min)

```bash
# Make sure you're in the project root
cd /path/to/Projet_2026

# Check Python version
python --version  # Should be 3.9, 3.10, or 3.11

# Verify dependencies installed
pip list | grep -E "pytest|black|mlflow"
```

**Expected Output:**
- Python 3.9+ ✓
- pytest installed ✓
- black installed ✓
- mlflow installed ✓

---

### Step 2: Code Quality Checks ✓ (3 min)

```bash
# Format code
python project.py format

# Check formatting
black --check src tests
```

**Expected Output:**
```
✅ All done! 1 file reformatted in 0.45s
```

---

### Step 3: Linting ✓ (2 min)

```bash
# Run all linting checks
python project.py lint
```

**Expected Output:**
- No flake8 errors
- No pylint errors
- Clean code ✓

**If there are errors:**
```bash
# Read error message
# Fix the issue manually
# Re-run check
python project.py lint
```

---

### Step 4: Unit Tests ✓ (5 min)

```bash
# Run all tests with coverage
python project.py test

# Must see:
# - All tests passing ✓
# - Coverage >= 80% ✓
```

**Expected Output:**
```
===================== test session starts ======================
collected 45 items

tests/test_data.py ........                              [ 17%]
tests/test_features.py ..................                [ 62%]
tests/test_clustering.py ...................             [100%]

------------- coverage report ----------------
Name                  Stmts   Miss  Cover   
──────────────────────────────────────────
src/data/preprocessing.py    100     10    90%
src/features/engineering.py   150     12    92%
src/clustering/models.py     180     18    90%
src/utils/config.py           40      2    95%
──────────────────────────────────────────
TOTAL                        470     42    91%

✓ Coverage is 91% - PASS (>80% required)
```

**If tests fail:**
```bash
# Run verbose mode to see details
pytest tests/ -vv --tb=short

# Find which test failed
# Fix the issue
# Re-run tests
pytest tests/ --cov=src --cov-fail-under=80
```

---

### Step 5: Pre-commit Hooks ✓ (2 min)

```bash
# Run pre-commit on all files
pre-commit run --all-files

# Should see: ✓ PASSED for all hooks
```

**Expected Output:**
```
black....................................................................Passed
isort....................................................................Passed
flake8...................................................................Passed
mypy.....................................................................Passed
bandit...................................................................Passed
```

**If hooks fail:**
```bash
# Auto-fix will be run
# Review changes
git diff

# Stage and commit fixes
git add .
git commit -m "style: auto-format code"
```

---

### Step 6: Final Verification ✓ (1 min)

```bash
# Quick smoke test
python project.py test-local | tail -20

# Should show all passed
# ✅ ALL CHECKS PASSED!
```

---

## 📋 Detailed Checklist

Before committing to Git:

- [ ] **Code Formatting**
  - [ ] Ran `python project.py format`
  - [ ] All .py files formatted with Black
  - [ ] Imports sorted with isort

- [ ] **Code Quality**
  - [ ] No flake8 errors
  - [ ] No pylint warnings
  - [ ] Line length <= 120 chars
  - [ ] Complexity <= 10

- [ ] **Testing**
  - [ ] All unit tests pass
  - [ ] Coverage >= 80%
  - [ ] No test failures
  - [ ] No skipped tests (unless marked)

- [ ] **Type Checking** (optional)
  - [ ] mypy passes (or understand why)

- [ ] **Security**
  - [ ] No bandit warnings
  - [ ] No hardcoded secrets
  - [ ] No SQL injection risks

- [ ] **Documentation**
  - [ ] Code has docstrings
  - [ ] Changes documented
  - [ ] README updated if needed

- [ ] **Git**
  - [ ] No merge conflicts
  - [ ] Commits are atomic
  - [ ] Commit messages are clear

---

## 🚫 Common Pre-Push Issues

### Issue: Black formatting fails

**Error:**
```
3 files would be reformatted
```

**Solution:**
```bash
# Auto-format
python project.py format

# Verify
black --check src tests  # Should be clean now

# Git add and commit
git add src tests
git commit -m "style: auto-format code"
```

---

### Issue: Tests fail with import errors

**Error:**
```
ModuleNotFoundError: No module named 'src'
```

**Solution:**
```bash
# Make sure you're in project root
cd /path/to/Projet_2026

# Reinstall if needed
python -m pip install -r requirements.txt

# Re-run tests
pytest tests/ -v
```

---

### Issue: Coverage below 80%

**Error:**
```
FAILED - Coverage percentage (75%) below threshold (80%)
```

**Solution:**
```bash
# See which lines aren't covered
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Write more tests for uncovered lines
# Then re-run:
pytest tests/ --cov=src --cov-fail-under=80
```

---

### Issue: Pre-commit hooks block commit

**Error:**
```
FAILED - flake8 would fail
```

**Solution:**
```bash
# Let pre-commit auto-fix
pre-commit run --all-files

# Review changes
git diff

# Stage and commit
git add .
git commit -m "style: auto-fix with pre-commit"
```

---

### Issue: Unknown linting error

**Error:**
```
src/features/engineering.py:145:1: E501 line too long (125 > 120 characters)
```

**Solution:**
```bash
# View the problematic line
sed -n '145p' src/features/engineering.py

# Fix: Break line, use shorter names, or use // for continuations
# Then verify
flake8 src tests
```

---

## 🎯 Final Sanity Checks

### Before Running `git push`

```bash
# 1. Ensure you're on correct branch
git branch

# 2. Ensure all changes are committed
git status  # Should be: "nothing to commit"

# 3. Ensure all checks pass one more time
python project.py test-local

# 4. View what you're about to push
git log --oneline origin/main..HEAD  # Shows commits to push

# 5. If everything is green, push!
git push origin main
```

---

## ⏱️ Timing Guide

| Step | Time | Command |
|------|------|---------|
| Format | 30s | `python project.py format` |
| Lint | 1m | `python project.py lint` |
| Test | 3m | `python project.py test` |
| Pre-commit | 1m | `pre-commit run --all-files` |
| Verify | 30s | `python project.py test-local \| tail` |
| **Total** | **6-7 min** | **All checks** |

---

## 📊 Workflow Summary

```
┌─────────────────────────────────────────────┐
│         PRE-PUSH VALIDATION FLOW            │
├─────────────────────────────────────────────┤
│                                              │
│  1. Format Code                              │
│     python project.py format                │
│     ↓                                       │
│  2. Lint & Check Quality                    │
│     python project.py lint                  │
│     ↓                                       │
│  3. Run All Tests                           │
│     python project.py test                  │
│     (Must see: Coverage >= 80%)            │
│     ↓                                       │
│  4. Pre-commit Verification                 │
│     pre-commit run --all-files              │
│     ↓                                       │
│  5. Final Check                             │
│     python project.py test-local            │
│     (Must see: ALL CHECKS PASSED)          │
│     ↓                                       │
│  6. Git Push                                │
│     git push origin main                    │
│     ↓                                       │
│  GitHub Actions Triggered                   │
│  (Runs same checks automatically)           │
│                                              │
└─────────────────────────────────────────────┘
```

---

## 🎯 Success Criteria

Push is ready when you see:

```
✅ Black formatting: PASSED
✅ isort imports: PASSED
✅ flake8 linting: PASSED
✅ Unit tests: PASSED (45/45)
✅ Coverage: 91% (>80% required)
✅ Security: PASSED
✅ Pre-commit hooks: PASSED
✅ Git status: Nothing to commit
```

---

## 🚀 After Push

Once you push to GitHub:

1. Go to GitHub repository
2. Click "Actions" tab
3. Watch workflow run automatically
4. GitHub Actions will repeat all checks
5. You should see ✓ all green checks
6. Your changes are validated! 🎉

---

## 💡 Pro Tips

1. **Run pre-push check regularly**
   - Don't wait until you're about to push
   - Run `python project.py test-local` after every major change

2. **Commit often**
   - Smaller commits are easier to debug
   - Use clear commit messages

3. **Fix issues immediately**
   - Don't accumulate problems
   - Auto-format as you go

4. **Use branches**
   - Develop on feature branches
   - Create PR from feature to main
   - GitHub Actions validates PRs too

5. **Review your changes**
   - `git diff` before committing
   - `git log --oneline -5` to see recent commits
   - Make sure nothing is accidentally included

---

## ❓ FAQ

**Q: Do I need to run all checks every time?**
A: Pre-commit hooks run automatically. But run `test-local` before push to be safe.

**Q: What if I just want to push a small fix?**
A: Still run the checks. Small fixes can break tests too.

**Q: Can I skip the checks?**
A: Yes with `git commit --no-verify`, but GitHub Actions will still block merge if checks fail.

**Q: How long does the full check take?**
A: ~6-7 minutes locally. GitHub Actions takes ~20 minutes (parallelized).

**Q: What if GitHub Actions fails but local checks passed?**
A: Rare but can happen due to environment differences. Check the GitHub Actions logs.

---

## 📞 Need Help?

- **Errors during checks?** → See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Don't understand a tool?** → See [TESTING.md](TESTING.md)
- **Git questions?** → See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#git-workflow)
- **General questions?** → See [README.md](README.md)

---

**Remember:** Pre-push validation prevents problems, saves time, and keeps the project clean! ✨

Good luck with your push! 🚀
