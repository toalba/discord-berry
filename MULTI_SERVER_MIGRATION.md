# Multi-Server Support Migration Guide

## What Changed

This branch (`multi-server-support`) enables the bot to work on multiple Discord servers simultaneously.

### Key Changes

1. **Global Command Sync**
   - Commands are now synced globally instead of to a single guild
   - Commands will appear on ALL servers the bot is invited to
   - ⚠️ **Important**: Global command sync can take up to 1 hour to propagate

2. **Permission System**
   - Removed hardcoded role ID check (`1375423331720757289`)
   - Now uses Discord's built-in permission system
   - Commands require `Manage Server` permission by default
   - Server admins can customize permissions per command in Discord settings

3. **Removed Dependencies**
   - `DC-GUILD` environment variable is no longer needed
   - `MY_GUILD` constant removed from code

## Migration Steps

### 1. Update Environment Variables

Remove or comment out the `DC-GUILD` variable from your `.env` file:
```bash
# DC-GUILD=1234567890  # No longer needed
TOKEN=your_bot_token_here
WEBHOOK=your_webhook_url_here
```

### 2. First Deployment

When you first deploy this version:
- The bot will sync commands globally on startup
- You'll see "Commands synced globally" in the console
- Commands may take up to 1 hour to appear on all servers

### 3. Configure Permissions (Per Server)

Server administrators can configure who can use the bot commands:

1. Go to **Server Settings** → **Integrations**
2. Find your bot in the list
3. Click on it to see all commands
4. Configure permissions per command:
   - By default, only users with "Manage Server" can use `/pick_ban` and `/remove_pb`
   - You can grant access to specific roles or users
   - You can restrict access to specific channels

## Benefits

✅ **Works on unlimited servers** - No configuration needed per server
✅ **Better permission management** - Uses Discord's native system
✅ **More maintainable** - No hardcoded IDs
✅ **Professional** - Follows Discord bot best practices

## Testing

To test the changes:

1. Invite the bot to a test server
2. Wait for commands to sync (up to 1 hour for first time)
3. As a server admin, you should see `/pick_ban` and `/remove_pb`
4. Users without "Manage Server" permission won't see the commands

## Rollback

If you need to revert to single-server mode:
```bash
git checkout main
```

## Notes

- The bot will still work on your original server
- All existing pick&ban sessions will continue to work
- No database changes required
- Backward compatible with existing data
