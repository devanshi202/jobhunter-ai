#!/bin/bash
# ==============================================================================
# JobHunter AI — Daily Manual Pipeline Runner
#
# Usage:
#   ./run_pipeline.sh              (runs full pipeline: scrape -> match -> apply -> contacts -> outreach)
#   ./run_pipeline.sh --skip-scrape (skips scraping, re-runs matching & outreach on existing data)
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PYTHON_VENV="$DIR/../venv/bin/python"

if [ ! -f "$PYTHON_VENV" ]; then
    echo "❌ Virtualenv not found at $PYTHON_VENV. Please run from ai-service environment."
    exit 1
fi

echo "======================================================================"
echo "🎯 JobHunter AI — Manual Pipeline Execution"
echo "======================================================================"
START_TIME=$(date +%s)

# STEP 1: SCRAPING
# if [ "$1" == "--skip-scrape" ]; then
#     echo "⏩ Skipping scraping (--skip-scrape flag passed). Using existing data."
# else
#     echo ""
#     "$PYTHON_VENV" "$DIR/01_scrape_jobs.py"
# fi

echo ""
"$PYTHON_VENV" "$DIR/01_scrape_jobs.py"

# STEP 2: JOB MATCHING
echo ""
"$PYTHON_VENV" "$DIR/02_match_jobs.py"

# STEP 3: RESOLVE DIRECT APPLY LINKS
echo ""
"$PYTHON_VENV" "$DIR/03_resolve_apply.py"

# STEP 4: FIND CONTACTS & MX VERIFICATION
echo ""
"$PYTHON_VENV" "$DIR/04_find_contacts.py"

# STEP 5: GENERATE OUTREACH (EMAILS + LINKEDIN NOTES)
echo ""
"$PYTHON_VENV" "$DIR/05_generate_outreach.py"

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "======================================================================"
echo "🎉 PIPELINE COMPLETE IN ${ELAPSED}s!"
echo "======================================================================"
echo "📁 All results saved to: $DIR/output/"
echo "   • Ranked Jobs CSV   : output/matched_jobs_ranked.csv"
echo "   • Clean Apply Links : output/resolved_apply_links.csv"
echo "   • Recruiter Contacts: output/contacts_summary.csv"
echo "   • Email Drafts View : output/email_drafts_preview.md"
echo "   • LinkedIn Notes    : output/connection_notes_preview.md"
echo "======================================================================"
