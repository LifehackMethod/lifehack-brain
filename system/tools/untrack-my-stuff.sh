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

PATTERN='^memory/|(^|/)_unpacked/|\.zip$|(^|/)conversations\.json$|(^|/)users\.json$|(^|/)design_chats/|(^|/)projects/[0-9a-f-]{8,}\.json$|(^|/)memories\.json$|(^|/)login_history\.json$'

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
