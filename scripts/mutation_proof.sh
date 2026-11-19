#!/usr/bin/env bash
# Mutation proof: in a throwaway worktree at HEAD, reverse-apply the src/
# changes of FIX_COMMIT and run the named test modules. Pass = tests FAIL
# with the fix reverted. Usage: scripts/mutation_proof.sh <fix-commit> <test.module>...
set -u
fix="$1"; shift
repo="$(git rev-parse --show-toplevel)"
wt="$(mktemp -d "${TMPDIR:-/tmp}/mutproof-XXXXXX")"
git -C "$repo" worktree add -q --detach "$wt" HEAD
if ! git -C "$repo" diff "$fix^" "$fix" -- src/ | git -C "$wt" apply -R; then
  # E4: a failed reverse patch used to fall through and report the tests
  # of UNREVERTED code. Stop instead; re-run at the fix commit (see
  # docs/mutation_proofs.md, method "at the fix commit").
  echo "== PROOF INVALID: reverse patch of $fix does not apply at HEAD"
  git -C "$repo" worktree remove --force "$wt"
  exit 2
fi
echo "== reverted src/ hunks of $fix in $wt"
git -C "$wt" diff --stat
( cd "$wt" && "$repo/.venv/bin/python" -m unittest "$@" 2>&1 | grep -E "^(Ran|OK|FAILED|FAIL:|ERROR:)" )
rc=${PIPESTATUS[0]}
git -C "$repo" worktree remove --force "$wt"
