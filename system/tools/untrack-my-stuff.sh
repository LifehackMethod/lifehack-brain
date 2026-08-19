#!/bin/sh
# untrack-my-stuff.sh — take YOUR OWN material back out of version control.
#
# WHAT THIS IS FOR. If an export (or your notes) ever got unzipped or copied INSIDE your brain folder,
# git started tracking it. That is not dangerous on its own — you cannot upload anything to a repository
# you do not own — but your private history should not be sitting in a folder that is pointed at a public
# one, and it clutters everything you do afterwards.
#
# ⭐ IT DOES NOT DELETE YOUR FILES. `git rm --cached` removes a file from git's INDEX and leaves it exactly
# where it is on disk. Nothing you wrote is touched. This is the whole reason it uses that command and not
# anything else.
#
# WHY THIS IS A SCRIPT AND NOT A COMMAND TO PASTE: a multi-line block pasted into a terminal gets
# mangled — backticks command-substitute, the shell hangs on a continuation prompt, and you cannot tell a
# broken paste from a real failure. One line that runs a file in the repo cannot fail that way.
#
# RUN IT FROM YOUR BRAIN FOLDER:
#     sh system/tools/untrack-my-stuff.sh

set -u

if [ ! -d .git ]; then
	echo ""
	echo "  This needs to run from the top of your brain folder (the one with system/ in it)."
	echo "  Try:  cd ~/Lifehack\\ Brain  — then run it again."
	echo ""
	exit 1
fi

# ⭐ THIS PATTERN MUST COVER EVERYTHING system/githooks/pre-commit REFUSES. That hook is the guard;
# this script is the stated recovery from it, so a folder the guard blocks but this misses is a folder
# a student is told to clean up and cannot. It was exactly that for a while: the hook's own header
# records that .gitignore gained data/ on 2026-08-12 and the guard did not, so "the two halves of one
# change disagreed for a day." The guard was fixed; this, its sibling, was not -- with two personal
# files tracked under data/ it printed "You're good" and exited 0. Measured and fixed 2026-08-18.
#
# data/ is where the person's writing actually lives since the 2026-08-12 layout change; memory/ is the
# pre-2026-08-12 name for the same thing, kept so an older install is still covered. state/ is the
# ingest's working notes ABOUT their material -- half-sorted piles, extracted conclusions, a map of
# what is in their export -- which is just as personal as the material. .brain-root is the per-install
# pointer to their notes folder, a personal path. The rest are raw-corpus fingerprints from an export
# unpacked into the repo by hand (measured 2026-08-09: 6,228 files staged, including a users.json
# holding an email address and a phone number).
#
# The last four alternatives -- design_chats/, projects/<hex>.json, memories.json, login_history.json --
# are additional export fingerprints this script has always carried and the hook does not. Keeping them
# is deliberate: this side may clean up MORE than the hook refuses, never less.
PATTERN='^data/|^memory/|(^|/)state/|(^|/)_unpacked/|\.zip$|(^|/)conversations\.json$|(^|/)users\.json$|(^|/)\.brain-root$|(^|/)design_chats/|(^|/)projects/[0-9a-f-]{8,}\.json$|(^|/)memories\.json$|(^|/)login_history\.json$'

tracked=$(git ls-files | grep -E "$PATTERN" | grep -v -x 'memory/README.md')

if [ -z "$tracked" ]; then
	echo ""
	echo "  Nothing to clean up — none of your own material is being tracked. You're good."
	echo ""
	exit 0
fi

count=$(printf '%s\n' "$tracked" | wc -l | tr -d ' ')

echo ""
echo "  Found $count file(s) of your own material being tracked by git."
echo "  I'm going to stop tracking them. THE FILES STAY ON YOUR DISK — nothing is deleted."
echo ""
printf '%s\n' "$tracked" | head -15 | sed 's/^/      /'
[ "$count" -gt 15 ] && echo "      ... and $((count - 15)) more"
echo ""

# -r for directories, --cached so the working file is never removed, -q because 6,000 lines helps nobody.
printf '%s\n' "$tracked" | tr '\n' '\0' | xargs -0 git rm -r -q --cached -- 2>/dev/null

still=$(git ls-files | grep -E "$PATTERN" | grep -v -x 'memory/README.md' | wc -l | tr -d ' ')

echo "  ------------------------------------------------------------"
if [ "$still" -eq 0 ]; then
	echo "  DONE. $count file(s) are no longer tracked, and all of them are still on your disk."
	echo ""
	echo "  One last step — save the cleanup:"
	echo "      git commit -m \"Stop tracking my own material\""
	echo ""
	echo "  (If that commit is refused, read what it says: something of yours is still staged.)"
else
	echo "  PARTIAL: $still file(s) are still tracked. Send this output to whoever gave you this folder;"
	echo "  do not commit until it reads DONE."
	exit 1
fi
echo ""
