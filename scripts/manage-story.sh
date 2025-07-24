#!/bin/bash

# Story Management Script for fapilog project
# Usage: ./scripts/manage-story.sh [command] [story-number]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if gh CLI is installed
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed. Please install it first."
        echo "Install from: https://cli.github.com/"
        exit 1
    fi
    
    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI is not authenticated. Run 'gh auth login' first."
        exit 1
    fi
}

# Validate story number format
validate_story_number() {
    local story_num="$1"
    if [[ ! "$story_num" =~ ^[0-9]+$ ]]; then
        log_error "Invalid story number format. Expected format: X (e.g., 47, 100)"
        exit 1
    fi
}

# Check if story file exists
check_story_file() {
    local story_num="$1"
    local story_file="$PROJECT_ROOT/docs/stories/story-${story_num}.md"
    
    if [[ ! -f "$story_file" ]]; then
        log_error "Story file does not exist: $story_file"
        exit 1
    fi
    
    echo "$story_file"
}

# Extract story information from story file
extract_story_info() {
    local story_file="$1"
    local story_title epic_num story_points user_story
    
    story_title=$(grep "^# Story" "$story_file" | head -1 | sed 's/^# //')
    epic_num=$(grep "^\*\*Epic:\*\*" "$story_file" | head -1 | grep -o '[0-9]\+' | head -1 || echo "")
    story_points=$(grep "Story Points:" "$story_file" | head -1 | grep -o '[0-9]\+' || echo "")
    
    echo "$story_title|$epic_num|$story_points"
}

# Create story template content
create_story_template() {
    local issue_number="$1"
    local title="$2"
    local epic="$3"
    local points="$4"
    local user_story="$5"
    
    cat > "$PROJECT_ROOT/docs/stories/story-${issue_number}.md" << EOF
# Story ${issue_number} – ${title}

**Epic:** ${epic}  
Sprint Target: Sprint #⟪next⟫  
Story Points: ${points}

**As a [role]**  
I want ${user_story}  
So that [benefit].

───────────────────────────────────  
Acceptance Criteria

- [ ] [Acceptance criteria 1]
- [ ] [Acceptance criteria 2]  
- [ ] [Acceptance criteria 3]

───────────────────────────────────  
Tasks / Technical Checklist

1. **[Task 1]**:

   - [Subtask 1.1]
   - [Subtask 1.2]

2. **[Task 2]**:

   - [Subtask 2.1]
   - [Subtask 2.2]

───────────────────────────────────  
Dev Notes

**Implementation Notes:**
- [Technical context]
- [Dependencies]
- [Architecture decisions]

**Performance Impact:**
- [Expected improvements]
- [Metrics to track]

───────────────────────────────────  
Testing

**Unit Tests:**
- [Test scenarios]

**Integration Tests:**
- [End-to-end scenarios]

**Performance Tests:**
- [Benchmarks and metrics]

───────────────────────────────────  
Status: **Not Started**

**Dev Agent Record**

- **Agent Model Used:** N/A
- **GitHub Issue:** #${issue_number}
- **Debug Log References:** N/A  
- **Completion Notes:** N/A
- **File List:** N/A
- **Change Log:** N/A
EOF
}

# Create new story with auto-numbering
create_story() {
    local title="$1"
    local epic="$2"
    local points="$3"
    local user_story="$4"
    
    log_info "Creating new auto-numbered story: $title"
    
    # Create GitHub issue first to get auto-assigned number
    local issue_url
    issue_url=$(gh issue create \
        --title "Story: $title" \
        --body "**Epic:** $epic  
**Story Points:** $points  
**User Story:** $user_story  

This story was auto-created and will be detailed in the story file." \
        --label "story,enhancement,architectural-improvements" \
        --assignee "@me")
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to create GitHub issue"
        return 1
    fi
    
    # Extract issue number from URL
    local issue_number
    issue_number=$(echo "$issue_url" | grep -o '[0-9]\+$')
    
    log_success "Created GitHub issue #${issue_number}: $issue_url"
    
    # Create story file with the issue number
    create_story_template "$issue_number" "$title" "$epic" "$points" "$user_story"
    
    log_success "Created story file: docs/stories/story-${issue_number}.md"
    log_info "Story ${issue_number} is ready for detailed planning and implementation"
    
    # Show next steps
    echo ""
    log_info "Next steps:"
    echo "  1. Edit story file to add acceptance criteria and tasks"
    echo "  2. Start development: ./scripts/manage-story.sh start ${issue_number}"
    echo "  3. Create PR: ./scripts/manage-story.sh create-pr ${issue_number}"
    echo ""
    
    return 0
}

# Create GitHub issue for existing story
create_issue() {
    local story_num="$1"
    local story_file
    story_file=$(check_story_file "$story_num")
    
    log_info "Creating GitHub issue for story-${story_num}..."
    
    local story_info
    story_info=$(extract_story_info "$story_file")
    IFS='|' read -r story_title epic_num story_points <<< "$story_info"
    
    # Create issue with story file content as body
    local issue_url
    issue_url=$(gh issue create \
        --title "$story_title" \
        --body-file "$story_file" \
        --label "story,enhancement,architectural-improvements" \
        --assignee "@me")
    
    if [[ $? -eq 0 ]]; then
        local issue_number
        issue_number=$(echo "$issue_url" | grep -o '[0-9]\+$')
        log_success "Created issue #${issue_number}: $issue_url"
        
        # Update story file with GitHub issue link
        echo "" >> "$story_file"
        echo "**GitHub Issue:** #${issue_number}" >> "$story_file"
        
        log_info "Updated story file with issue link"
        return 0
    else
        log_error "Failed to create GitHub issue"
        return 1
    fi
}

# Start development (create branch)
start_development() {
    local story_num="$1"
    local story_file
    story_file=$(check_story_file "$story_num")
    
    local branch_name="story-${story_num}/implementation"
    
    log_info "Starting development for story-${story_num}..."
    
    # Check if branch already exists
    if git rev-parse --verify "$branch_name" &> /dev/null; then
        log_warning "Branch '$branch_name' already exists"
        log_info "Switching to existing branch..."
        git checkout "$branch_name"
    else
        log_info "Creating new branch: $branch_name"
        git checkout -b "$branch_name"
        git push -u origin "$branch_name"
    fi
    
    log_success "Ready to start development on branch: $branch_name"
    log_info "GitHub Actions will automatically move the story to 'In Progress'"
}

# Create pull request
create_pr() {
    local story_num="$1"
    local story_file
    story_file=$(check_story_file "$story_num")
    
    local current_branch
    current_branch=$(git branch --show-current)
    
    if [[ ! "$current_branch" =~ story-${story_num} ]]; then
        log_error "Current branch ($current_branch) doesn't match story-${story_num}"
        exit 1
    fi
    
    log_info "Creating pull request for story-${story_num}..."
    
    local story_info
    story_info=$(extract_story_info "$story_file")
    IFS='|' read -r story_title epic_num story_points <<< "$story_info"
    
    # Get issue number from story file or from story number (for auto-numbered stories)
    local issue_number
    issue_number=$(grep "^\*\*GitHub Issue:\*\*" "$story_file" | grep -o '#[0-9]\+' | tr -d '#' || echo "$story_num")
    
    local pr_title="$story_title"
    local pr_body="## Story Implementation

**Story:** story-${story_num}  
**Epic:** ${epic_num:-architectural-improvements} – Processing Performance Optimization  
**Issue:** Closes #${issue_number}

### Implementation Summary
Implementation of story-${story_num} as defined in docs/stories/story-${story_num}.md

Please refer to the story file for detailed acceptance criteria and task list.

### Story File
\`docs/stories/story-${story_num}.md\`

### Review Notes
- [ ] All story acceptance criteria have been met
- [ ] All technical tasks have been completed
- [ ] Tests have been written and are passing
- [ ] Performance improvements have been validated

Closes #${issue_number}"
    
    local pr_url
    pr_url=$(gh pr create \
        --title "$pr_title" \
        --body "$pr_body" \
        --head "$current_branch" \
        --base "main")
    
    if [[ $? -eq 0 ]]; then
        log_success "Created pull request: $pr_url"
        log_info "GitHub Actions will automatically move the story to 'Review'"
    else
        log_error "Failed to create pull request"
        return 1
    fi
}

# Show story status
show_status() {
    local story_num="$1"
    local story_file
    story_file=$(check_story_file "$story_num")
    
    log_info "Story status for story-${story_num}:"
    echo ""
    
    # Get story title
    local story_title
    story_title=$(grep "^# Story" "$story_file" | head -1 | sed 's/^# //')
    echo "📖 $story_title"
    echo ""
    
    # Check for GitHub issue
    local issue_number
    issue_number=$(grep "^\*\*GitHub Issue:\*\*" "$story_file" | grep -o '#[0-9]\+' | tr -d '#' || echo "$story_num")
    
    if [[ -n "$issue_number" ]]; then
        echo "🔗 GitHub Issue: #${issue_number}"
        gh issue view "$issue_number" --json state,labels,assignees,url | \
            jq -r '"   State: " + .state + "\n   Labels: " + (.labels | map(.name) | join(", ")) + "\n   URL: " + .url'
        echo ""
    else
        echo "❌ No GitHub issue found"
        echo ""
    fi
    
    # Check for branch
    local branch_name="story-${story_num}/implementation"
    if git rev-parse --verify "$branch_name" &> /dev/null; then
        echo "🌿 Development branch: $branch_name"
        
        # Check for PR
        local pr_number
        pr_number=$(gh pr list --head "$branch_name" --json number --jq '.[0].number' 2>/dev/null || echo "")
        
        if [[ -n "$pr_number" ]]; then
            echo "📝 Pull Request: #${pr_number}"
            gh pr view "$pr_number" --json state,url | \
                jq -r '"   State: " + .state + "\n   URL: " + .url'
        else
            echo "📝 No pull request created yet"
        fi
    else
        echo "❌ No development branch created yet"
    fi
    
    echo ""
}

# Show help
show_help() {
    cat << EOF
Story Management Script for fapilog

Usage: $0 [command] [arguments...]

Commands:
  create-story TITLE EPIC POINTS USER_STORY    Create new auto-numbered story
  create-issue STORY_NUM                        Create GitHub issue for existing story
  start        STORY_NUM                        Start development (create branch)
  create-pr    STORY_NUM                        Create pull request for story
  status       STORY_NUM                        Show current status of story
  help                                          Show this help message

Examples:
  # Create new auto-numbered story
  $0 create-story "Parallel Enricher Processing" "architectural-improvements" 8 "enrichers to execute in parallel"
  
  # Work with existing stories
  $0 create-issue 47                   # Create issue for story-47.md (if it exists)
  $0 start 47                          # Start development on story-47
  $0 create-pr 47                      # Create PR for story-47
  $0 status 47                         # Show status of story-47

Auto-numbering:
  - New stories use GitHub issue numbers (story-47.md, story-48.md, etc.)
  - No manual numbering needed - GitHub handles uniqueness
  - Perfect for multiple developers - no race conditions

Requirements:
  - GitHub CLI (gh) must be installed and authenticated
  - Git repository must be properly configured

EOF
}

# Main script logic
main() {
    local command="$1"
    
    case "$command" in
        "create-story")
            local title="$2"
            local epic="$3"
            local points="$4"
            local user_story="$5"
            
            if [[ -z "$title" || -z "$epic" || -z "$points" || -z "$user_story" ]]; then
                log_error "Missing required arguments for create-story"
                echo "Usage: $0 create-story TITLE EPIC POINTS USER_STORY"
                echo "Example: $0 create-story \"Parallel Enricher Processing\" \"architectural-improvements\" 8 \"enrichers to execute in parallel\""
                exit 1
            fi
            check_gh_cli
            create_story "$title" "$epic" "$points" "$user_story"
            ;;
        "create-issue")
            local story_num="$2"
            if [[ -z "$story_num" ]]; then
                log_error "Story number is required"
                show_help
                exit 1
            fi
            check_gh_cli
            validate_story_number "$story_num"
            create_issue "$story_num"
            ;;
        "start")
            local story_num="$2"
            if [[ -z "$story_num" ]]; then
                log_error "Story number is required"
                show_help
                exit 1
            fi
            validate_story_number "$story_num"
            start_development "$story_num"
            ;;
        "create-pr")
            local story_num="$2"
            if [[ -z "$story_num" ]]; then
                log_error "Story number is required"
                show_help
                exit 1
            fi
            check_gh_cli
            validate_story_number "$story_num"
            create_pr "$story_num"
            ;;
        "status")
            local story_num="$2"
            if [[ -z "$story_num" ]]; then
                log_error "Story number is required"
                show_help
                exit 1
            fi
            check_gh_cli
            validate_story_number "$story_num"
            show_status "$story_num"
            ;;
        "help"|"--help"|"-h"|"")
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 