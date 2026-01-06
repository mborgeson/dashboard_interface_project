# Walkthrough - Antigravity Backup Workflow

I have set up a workflow to backup **filtered** Antigravity conversations and artifacts to your project directory.

## What has been done
1.  Created a configuration file: `.agent/backup_list.txt`.
2.  Updated the workflow `.agent/workflows/backup-chats.md` to read from this list.
3.  Verified the backup process: Only the Conversation IDs listed in `backup_list.txt` are copied.

## How to use
1.  **Add Conversations:** Open `.agent/backup_list.txt` and add the IDs of the conversations you want to backup (one per line).
2.  **Run Backup:** Run the `/backup-chats` workflow (or the commands within it).

## Verification Results
-   I ran the backup with only the current conversation ID (`7fe5bf73-e82c-44e6-abd8-68d84d6e7c70`) in the list.
-   Result: Only `7fe5bf73-e82c-44e6-abd8-68d84d6e7c70.pb` and its corresponding brain folder were copied to `antigravity/` in your project.
