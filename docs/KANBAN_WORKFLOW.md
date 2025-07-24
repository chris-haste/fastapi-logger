# GitHub Kanban Board Workflow

This document explains how to use the automated GitHub Kanban board workflow for managing story implementation in the fapilog project.

## Overview

The workflow automatically manages story lifecycle through GitHub Issues, Pull Requests, and branch management, providing full traceability from story conception to completion.

## Setup Requirements

### 1. GitHub CLI Installation
```bash
# Install GitHub CLI
brew install gh  # macOS
# or
sudo apt install gh  # Ubuntu
# or download from https://cli.github.com/

# Authenticate
gh auth login
```

### 2. GitHub Project Board
1. Create a new GitHub Project (Projects V2) in your repository
2. Add columns: **Backlog**, **In Progress**, **Review**, **Done**
3. Note your project URL (needed for automation)

### 3. Repository Setup
Ensure the following files are in your repository:
- `.github/workflows/project-automation.yml` - GitHub Actions workflow
- `.github/ISSUE_TEMPLATE/story.yml` - Story issue template
- `.github/pull_request_template.md` - PR template
- `scripts/manage-story.sh` - Story management script

## Story Lifecycle Workflow

### Phase 1: Story Planning
```bash
# 1. Create story file (manual)
vim docs/stories/story-100.1.md

# 2. Create GitHub issue from story
./scripts/manage-story.sh create-issue 100.1
```

**Result:** 
- Issue created with story content
- Automatically added to "Backlog" column
- Story file updated with issue link

### Phase 2: Development Start
```bash
# Start development (creates branch)
./scripts/manage-story.sh start 100.1
```

**Result:**
- Branch `story-100.1/implementation` created
- Automatically moved to "In Progress" column
- GitHub Actions adds comment and label to issue

### Phase 3: Development Work
```bash
# Make commits referencing the issue
git commit -m "feat(story-100.1): implement parallel enricher groups

- Extended resolve_dependencies() to return parallel groups
- Added dependency level grouping

Ref #47"  # Reference the issue number

# Update story progress
git commit -m "docs(story-100.1): mark task 1 complete

✅ Enhanced dependency resolution completed

Ref #47"
```

### Phase 4: Review Process
```bash
# Create pull request
./scripts/manage-story.sh create-pr 100.1
```

**Result:**
- Pull request created with story template
- Automatically moved to "Review" column
- GitHub Actions updates issue status

### Phase 5: Completion
```bash
# When PR is approved and merged
gh pr merge --squash --delete-branch
```

**Result:**
- Issue automatically closed (via "Closes #47" in PR)
- Moved to "Done" column
- Completion comment added

## Command Reference

### Story Management Script

```bash
# Create GitHub issue for a story
./scripts/manage-story.sh create-issue STORY_NUM

# Start development (create branch)
./scripts/manage-story.sh start STORY_NUM

# Create pull request
./scripts/manage-story.sh create-pr STORY_NUM

# Check story status
./scripts/manage-story.sh status STORY_NUM

# Show help
./scripts/manage-story.sh help
```

### GitHub CLI Commands

```bash
# List open issues
gh issue list --label story

# View specific issue
gh issue view ISSUE_NUMBER

# List pull requests
gh pr list

# View PR status
gh pr view PR_NUMBER

# Merge PR
gh pr merge PR_NUMBER --squash --delete-branch
```

### Git Branch Management

```bash
# List story branches
git branch -a | grep story-

# Switch to story branch
git checkout story-100.1/implementation

# Delete completed story branch
git branch -d story-100.1/implementation
git push origin --delete story-100.1/implementation
```

## Automation Features

### GitHub Actions Triggers

| Event | Action | Board Update |
|-------|--------|--------------|
| Issue created | Auto-add to project | → Backlog |
| Branch `story-X.X/*` pushed | Add in-progress label | → In Progress |
| PR opened | Add review label | → Review |
| PR merged | Close issue, add completed label | → Done |
| PR closed (not merged) | Return to in-progress | → In Progress |

### Automatic Comments

The system adds contextual comments to issues:
- 🚀 **Development Started** when branch is created
- 📖 **Ready for Review** when PR is opened
- ✅ **Story Completed** when PR is merged
- 🔄 **Back to Development** when PR is closed without merging

### Label Management

Automatic labels are applied:
- `story` - All story-related issues
- `enhancement` - Feature additions
- `epic-X` - Epic grouping (e.g., `epic-100`)
- `in-progress` - Active development
- `review` - Under review
- `completed` - Finished stories

## Example Workflow Walkthrough

Let's implement story-100.1 (Parallel Enricher Processing):

### 1. Create Issue
```bash
./scripts/manage-story.sh create-issue 100.1
```
```
[INFO] Creating GitHub issue for story-100.1...
[SUCCESS] Created issue #47: https://github.com/user/fapilog/issues/47
[INFO] Updated story file with issue link
```

### 2. Start Development
```bash
./scripts/manage-story.sh start 100.1
```
```
[INFO] Starting development for story-100.1...
[INFO] Creating new branch: story-100.1/implementation
[SUCCESS] Ready to start development on branch: story-100.1/implementation
[INFO] GitHub Actions will automatically move the story to 'In Progress'
```

### 3. Check Status
```bash
./scripts/manage-story.sh status 100.1
```
```
[INFO] Story status for story-100.1:

📖 Story 100.1 – Parallel Enricher Processing Pipeline

🔗 GitHub Issue: #47
   State: open
   Labels: story, enhancement, in-progress, epic-100
   URL: https://github.com/user/fapilog/issues/47

🌿 Development branch: story-100.1/implementation
📝 No pull request created yet
```

### 4. Implement & Commit
```bash
# Work on implementation
git add src/fapilog/_internal/enricher_registry.py
git commit -m "feat(enricher-registry): implement parallel execution groups

- Extended resolve_dependencies() to return parallel groups
- Group enrichers by dependency levels (level 0, 1, 2...)
- Maintain topological ordering within each level

✅ Completed story-100.1 task 1
Ref #47"
```

### 5. Create Pull Request
```bash
./scripts/manage-story.sh create-pr 100.1
```
```
[INFO] Creating pull request for story-100.1...
[SUCCESS] Created pull request: https://github.com/user/fapilog/pull/52
[INFO] GitHub Actions will automatically move the story to 'Review'
```

### 6. Complete Story
```bash
# After review and approval
gh pr merge 52 --squash --delete-branch
```

The issue is automatically closed and moved to "Done" column.

## Best Practices

### Commit Messages
Use conventional commit format with story references:
```bash
git commit -m "feat(story-100.1): implement parallel enricher processing

- Added asyncio.gather() for parallel execution
- Implemented error isolation between enrichers
- Added performance metrics for parallel vs sequential

✅ Completed story-100.1 tasks 2-3
Closes #47"
```

### Branch Naming
Use consistent branch naming:
- `story-X.Y/feature-name` (preferred)
- `story-X.Y/implementation` (generic)
- `feat/story-X.Y-description` (alternative)

### Issue References
Always reference issues in commits:
- `Ref #47` - Reference without closing
- `Closes #47` - Reference and close on merge
- `Fixes #47` - Reference and close on merge

### Story File Updates
Keep story files updated during development:
- Mark tasks as complete with ✅
- Update Dev Agent Record section
- Document decisions and changes

## Troubleshooting

### Common Issues

**GitHub Actions not triggering:**
- Check workflow file syntax
- Ensure repository has Actions enabled
- Verify branch naming matches patterns

**Issue not found by automation:**
- Ensure issue title contains "Story X.Y"
- Check story number format (X.Y)
- Verify issue is open

**Script permissions:**
```bash
chmod +x scripts/manage-story.sh
```

**GitHub CLI authentication:**
```bash
gh auth status
gh auth login
```

### Manual Recovery

If automation fails, manually update:
```bash
# Move issue between columns (if using Projects V2)
gh issue edit ISSUE_NUMBER --add-label "in-progress"
gh issue edit ISSUE_NUMBER --remove-label "backlog"

# Add manual comments
gh issue comment ISSUE_NUMBER --body "Manual status update: moved to in-progress"
```

## Configuration

### Project URL Update
Update `.github/workflows/project-automation.yml`:
```yaml
project-url: https://github.com/users/YOUR_USERNAME/projects/PROJECT_NUMBER
```

### Custom Labels
Add custom labels in the workflow file:
```yaml
labels: ['story', 'enhancement', 'epic-100', 'priority-high']
```

### Notification Settings
Configure GitHub notifications for:
- Issue assignments
- PR reviews
- Workflow failures

This workflow provides complete automation for story management while maintaining flexibility for manual intervention when needed. 