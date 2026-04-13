#!/usr/bin/env python3
"""
Telegram Member Adder - Deployable on Render
This script runs continuously and adds members from a JSON file.
"""

import asyncio
import json
import sys
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, PeerFloodError, UserPrivacyRestrictedError,
    UserNotMutualContactError, UserChannelsTooMuchError, ChatAdminRequiredError,
    SessionPasswordNeededError
)
from telethon.tl.types import InputPeerUser

from config import (
    API_ID, API_HASH, PHONE_NUMBER, SESSION_PATH, MEMBERS_JSON,
    MIN_DELAY, MAX_DELAY, MAX_PER_SESSION, MAX_CONSECUTIVE_FAILURES,
    LOG_FILE, validate_config
)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TelegramMemberAdder:
    def __init__(self):
        validate_config()
        self.client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)
        self.stats = {
            'added': 0,
            'skipped': 0,
            'failed': 0,
            'start_time': datetime.now()
        }
        
    async def start_client(self):
        """Start and authenticate the client"""
        logger.info("Starting Telegram client...")
        await self.client.start(phone=PHONE_NUMBER)
        
        if not await self.client.is_user_authorized():
            logger.error("Authentication failed!")
            sys.exit(1)
            
        me = await self.client.get_me()
        logger.info(f"✅ Logged in as: {me.first_name} (@{me.username})")
        return True
    
    async def select_destination_group(self):
        """Select the group where members will be added"""
        dialogs = await self.client.get_dialogs()
        
        groups = []
        logger.info("\n📋 Available groups and channels:")
        
        for i, dialog in enumerate(dialogs):
            if dialog.is_group or dialog.is_channel:
                groups.append(dialog)
                entity_type = "Channel" if dialog.is_channel else "Group"
                logger.info(f"[{len(groups)-1:3d}] {entity_type:8s} | {dialog.name}")
        
        if not groups:
            logger.error("No groups or channels found!")
            sys.exit(1)
        
        # For Render deployment, you can set the destination group ID in environment
        # or manually select it first time and save to a file
        dest_group_file = Path("destination_group.json")
        
        if dest_group_file.exists():
            with open(dest_group_file, 'r') as f:
                data = json.load(f)
                group_id = data['group_id']
                for g in groups:
                    if g.id == group_id:
                        logger.info(f"✅ Using saved destination: {g.name}")
                        return g
        
        # If no saved group, select manually (for first run)
        while True:
            try:
                choice = int(input("\n🎯 Enter the number of the DESTINATION group: "))
                if 0 <= choice < len(groups):
                    selected = groups[choice]
                    # Save for future runs
                    with open(dest_group_file, 'w') as f:
                        json.dump({'group_id': selected.id, 'name': selected.name}, f)
                    return selected
                else:
                    logger.error(f"Please enter a number between 0 and {len(groups)-1}")
            except ValueError:
                logger.error("Please enter a valid number")
    
    def load_members(self):
        """Load member list from JSON file"""
        json_path = Path(MEMBERS_JSON)
        
        if not json_path.exists():
            logger.error(f"❌ Members file not found: {MEMBERS_JSON}")
            logger.info("Please run scrape_members.py locally first and upload members.json")
            sys.exit(1)
            
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        members = data.get('members', [])
        logger.info(f"📊 Loaded {len(members)} members from {MEMBERS_JSON}")
        return members
    
    def load_progress(self):
        """Load progress from previous runs"""
        progress_file = Path("progress.json")
        if progress_file.exists():
            with open(progress_file, 'r') as f:
                return json.load(f)
        return {'processed_ids': [], 'last_index': 0}
    
    def save_progress(self, progress):
        """Save progress after each successful addition"""
        with open("progress.json", 'w') as f:
            json.dump(progress, f)
    
    async def add_members(self, members, dest_group):
        """Main method to add members with error handling and delays"""
        progress = self.load_progress()
        start_index = progress['last_index']
        processed_ids = set(progress['processed_ids'])
        
        logger.info(f"\n🚀 Starting from index {start_index}")
        logger.info(f"📌 Already processed: {len(processed_ids)} members")
        logger.info(f"🎯 Destination: {dest_group.name}")
        logger.info(f"⏱️  Delay between adds: {MIN_DELAY}-{MAX_DELAY} seconds")
        logger.info("="*60)
        
        consecutive_failures = 0
        
        for i in range(start_index, len(members)):
            member = members[i]
            
            # Skip already processed members
            if member['id'] in processed_ids:
                continue
                
            # Check daily limit
            if MAX_PER_SESSION > 0 and self.stats['added'] >= MAX_PER_SESSION:
                logger.info(f"✅ Reached daily limit of {MAX_PER_SESSION}. Stopping.")
                break
                
            # Check consecutive failures
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.warning(f"⚠️ Too many consecutive failures ({MAX_CONSECUTIVE_FAILURES}). Stopping.")
                break
            
            try:
                # Create user peer
                user_to_add = InputPeerUser(
                    user_id=member['id'],
                    access_hash=member['access_hash']
                )
                
                # Attempt to add
                await self.client.add_chat_members(dest_group.id, [user_to_add])
                
                # Success
                self.stats['added'] += 1
                processed_ids.add(member['id'])
                consecutive_failures = 0
                
                display_name = member.get('first_name', 'Unknown')
                username = member.get('username', 'N/A')
                logger.info(f"✅ [{i+1}/{len(members)}] Added: {display_name} (@{username})")
                logger.info(f"   Progress: {self.stats['added']} added, {self.stats['skipped']} skipped")
                
                # Save progress
                progress['last_index'] = i + 1
                progress['processed_ids'] = list(processed_ids)
                self.save_progress(progress)
                
                # Random delay
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                next_add_time = datetime.now() + timedelta(seconds=delay)
                logger.info(f"   ⏱️  Next add at: {next_add_time.strftime('%H:%M:%S')}")
                await asyncio.sleep(delay)
                
            except FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(f"⏰ Flood wait! Telegram requires {wait_time} seconds delay.")
                
                if wait_time > 3600:  # More than 1 hour
                    logger.error(f"❌ Wait time too long ({wait_time}s). Stopping for today.")
                    break
                    
                logger.info(f"   Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                
                # Retry after flood wait
                try:
                    await self.client.add_chat_members(dest_group.id, [user_to_add])
                    self.stats['added'] += 1
                    processed_ids.add(member['id'])
                    consecutive_failures = 0
                    logger.info(f"✅ Retry successful!")
                except Exception as e2:
                    self.stats['failed'] += 1
                    consecutive_failures += 1
                    logger.error(f"❌ Retry failed: {type(e2).__name__}")
                    
            except PeerFloodError:
                self.stats['failed'] += 1
                logger.error("❌ PeerFloodError: Account is temporarily limited.")
                logger.error("   Stop the script and try again in 24 hours.")
                break
                
            except UserPrivacyRestrictedError:
                self.stats['skipped'] += 1
                processed_ids.add(member['id'])
                logger.info(f"⏭️  Skipped: User has privacy restrictions")
                
            except UserNotMutualContactError:
                self.stats['skipped'] += 1
                processed_ids.add(member['id'])
                logger.info(f"⏭️  Skipped: User only allows contacts to add them")
                
            except UserChannelsTooMuchError:
                self.stats['skipped'] += 1
                processed_ids.add(member['id'])
                logger.info(f"⏭️  Skipped: User is in too many groups")
                
            except ChatAdminRequiredError:
                logger.error("❌ You are not an admin in the destination group!")
                break
                
            except Exception as e:
                self.stats['failed'] += 1
                consecutive_failures += 1
                logger.error(f"❌ Unexpected error: {type(e).__name__}: {e}")
                
            # Save progress even on skip/failure
            progress['last_index'] = i + 1
            progress['processed_ids'] = list(processed_ids)
            self.save_progress(progress)
        
        # Final summary
        await self.print_summary()
    
    async def print_summary(self):
        """Print final statistics"""
        runtime = datetime.now() - self.stats['start_time']
        
        logger.info("\n" + "="*60)
        logger.info("📊 FINAL SUMMARY")
        logger.info("="*60)
        logger.info(f"✅ Successfully added: {self.stats['added']}")
        logger.info(f"⏭️  Skipped:            {self.stats['skipped']}")
        logger.info(f"❌ Failed:             {self.stats['failed']}")
        logger.info(f"⏱️  Total runtime:      {runtime}")
        logger.info("="*60)
    
    async def run(self):
        """Main execution flow"""
        try:
            await self.start_client()
            
            # For Render, members.json should be in the repository
            members = self.load_members()
            
            if not members:
                logger.error("No members to add!")
                return
                
            dest_group = await self.select_destination_group()
            
            # Ask for confirmation (skip in automated environment)
            if sys.stdin.isatty():
                confirm = input(f"\n⚠️  Add {len(members)} members to '{dest_group.name}'? (yes/no): ")
                if confirm.lower() != 'yes':
                    logger.info("Cancelled.")
                    return
            
            await self.add_members(members, dest_group)
            
        except SessionPasswordNeededError:
            logger.error("❌ Two-factor authentication is not supported on Render.")
            logger.error("   Please disable 2FA or use a different account.")
            
        except Exception as e:
            logger.error(f"❌ Fatal error: {type(e).__name__}: {e}")
            
        finally:
            await self.client.disconnect()
            logger.info("👋 Disconnected.")


async def main():
    adder = TelegramMemberAdder()
    await adder.run()


if __name__ == "__main__":
    asyncio.run(main())
