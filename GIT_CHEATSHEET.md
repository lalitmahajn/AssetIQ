# 🛠️ Git & GitHub Cheatsheet

A comprehensive reference for common Git commands used in professional development workflows.

---

## 🏁 Getting Started
| Action | Command | Description |
| :--- | :--- | :--- |
| **Initialize** | `git init` | Create a new local repository. |
| **Clone** | `git clone <url>` | Download an existing repository from GitHub. |
| **Status** | `git status` | Show changed files and staged changes. |
| **Config** | `git config --global user.name "Your Name"` | Set your global username. |

---

## 📝 Basic Workflow (Add, Commit, Push)
| Action | Command | Description |
| :--- | :--- | :--- |
| **Add** | `git add <file>` | Stage a specific file for the next commit. |
| **Add All** | `git add .` | Stage **all** changes in the current directory. |
| **Commit** | `git commit -m "message"` | Commit staged changes with a descriptive message. |
| **Push** | `git push` | Upload local commits to the remote repository. |
| **Pull** | `git pull` | Download changes from remote and merge them. |
| **Fetch** | `git fetch` | Download changes from remote **without** merging. |

---

## 🌿 Branching & Merging
| Action | Command | Description |
| :--- | :--- | :--- |
| **List Branches** | `git branch` | List all local branches. |
| **Create Branch** | `git checkout -b <name>` | Create a new branch and switch to it. |
| **Switch Branch** | `git checkout <name>` | Switch to an existing branch. |
| **Merge** | `git merge <name>` | Merge a specific branch into your current branch. |
| **Delete Local** | `git branch -d <name>` | Delete a local branch (must be merged). |
| **Delete Remote**| `git push origin --delete <name>` | Delete a branch from GitHub. |

---

## 🔍 Inspection & History
| Action | Command | Description |
| :--- | :--- | :--- |
| **Log** | `git log --oneline` | Show commit history in a single line per commit. |
| **Graph** | `git log --graph --all` | Visual representation of branch history. |
| **Diff** | `git diff` | Show unstaged changes compared to the last commit. |
| **Diff Staged** | `git diff --staged` | Show changes that are staged for commit. |
| **Show Commit** | `git show <commit_id>` | Show details of a specific commit. |

---

## ⏪ Undoing Changes
| Action | Command | Description |
| :--- | :--- | :--- |
| **Discard Local** | `git checkout -- <file>` | Revert a file to the last committed state. |
| **Unstage File** | `git reset HEAD <file>` | Remove a file from the staging area. |
| **Amend Commit** | `git commit --amend` | Update the last commit with current changes. |
| **Reset Soft** | `git reset --soft HEAD~1` | Undo last commit but keep changes staged. |
| **Reset Hard** | `git reset --hard HEAD~1` | **Danger:** Undo last commit and delete all changes. |
| **Revert** | `git revert <commit_id>` | Create a new commit that undoes a previous one. |

---

## 💾 Stashing (Temporary Storage)
Used when you need to switch branches but aren't ready to commit current work.
| Action | Command | Description |
| :--- | :--- | :--- |
| **Stash** | `git stash` | Store all current changes in a temporary stack. |
| **Pop** | `git stash pop` | Apply stashed changes and remove them from stack. |
| **List** | `git stash list` | Show all stashed entries. |
| **Drop** | `git stash drop` | Remove the most recent stash without applying. |

---

## � Remote Repositories
Manage the connection between your local repository and the remote server (e.g., GitHub).

| Action | Command | Description |
| :--- | :--- | :--- |
| **List Remotes** | `git remote -v` | Show URLs of remote repositories. |
| **Add Remote** | `git remote add origin <url>` | Connect local repo to a new remote URL. |
| **Set URL** | `git remote set-url origin <url>` | Change the URL of an existing remote. |
| **Rename Remote** | `git remote rename <old> <new>` | Rename a remote (e.g., from `origin` to `upstream`). |
| **Remove Remote** | `git remote remove <name>` | Disconnect from a remote repository. |

---

## �🚀 Advanced / Pro Tips
- **Shortcuts**: Use `git commit -am "message"` to add and commit all modified files in one step (only works for tracked files).
- **Ignoring Files**: Create a `.gitignore` file to tell Git which files/folders (like `node_modules` or `.env`) should never be tracked.
- **Remote Info**: `git remote -v` shows the URLs for the remote repositories.

---

## 💡 Practical Examples for AssetIQ
**Pushing a specific fix:**
```powershell
git add apps/backend/logic.py
git commit -m "Fix calculation error in plant logic"
git push
```

**Syncing with the latest team changes:**
```powershell
git fetch origin
git merge origin/main
```
