#!/bin/bash

# Get all branches (local and remote)
git branch -a --format='%(refname:short)|%(upstream:short)|%(upstream:track)|%(committerdate:iso8601)|%(authorname)|%(subject)' | while IFS='|' read branch upstream track date author subject; do
  
  # Skip HEAD pointer
  if [[ "$branch" == *"HEAD"* ]]; then
    continue
  fi
  
  # Clean branch name
  clean_branch="${branch#remotes/origin/}"
  
  # Get ahead/behind vs origin/main
  if git rev-parse --verify "$branch" &>/dev/null; then
    ahead_behind=$(git rev-list --left-right --count origin/main...$branch 2>/dev/null || echo "0	0")
    ahead=$(echo "$ahead_behind" | awk '{print $1}')
    behind=$(echo "$ahead_behind" | awk '{print $2}')
    
    # Get last commit hash
    last_commit=$(git rev-parse --short "$branch" 2>/dev/null || echo "unknown")
    
    # Determine work stream
    work_stream="other"
    if [[ "$clean_branch" == claude/* ]]; then
      work_stream="claude"
    elif [[ "$clean_branch" == feature/* ]]; then
      work_stream="feature"
    elif [[ "$clean_branch" == hotfix/* ]]; then
      work_stream="hotfix"
    elif [[ "$clean_branch" == main ]]; then
      work_stream="main"
    fi
    
    # Output JSON-like line
    echo "{\"branch\":\"$clean_branch\",\"ahead\":$ahead,\"behind\":$behind,\"last_commit\":\"$last_commit\",\"date\":\"$date\",\"author\":\"$author\",\"subject\":\"$subject\",\"work_stream\":\"$work_stream\"}"
  fi
done | jq -s '.' > audit_artifacts/$(cat /tmp/audit_ts.txt)/branches.json

# Also create a readable summary
echo "Branch Map Summary" > audit_artifacts/$(cat /tmp/audit_ts.txt)/branches.txt
echo "==================" >> audit_artifacts/$(cat /tmp/audit_ts.txt)/branches.txt
echo "" >> audit_artifacts/$(cat /tmp/audit_ts.txt)/branches.txt

cat audit_artifacts/$(cat /tmp/audit_ts.txt)/branches.json | jq -r '.[] | "\(.work_stream) | \(.branch) | ahead: \(.ahead), behind: \(.behind) | \(.last_commit) | \(.date) | \(.author)"' >> audit_artifacts/$(cat /tmp/audit_ts.txt)/branches.txt
