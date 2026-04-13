#!/usr/bin/env python3
"""
Telegram Group Member Scraper
Run this LOCALLY on your computer first to extract members.
DO NOT run this on Render - it's for local use only.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import ChannelParticipantsSearch
import pandas as pd

from config import API_ID, API_HASH, PHONE_NUMBER, SESSION_PATH, MEMBERS_JSON, MEMBERS_CSV, validate_config


class TelegramMemberScraper:
    def __init__(self):
        validate_config()
        self.client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)
        
    async def start_client(self):
        """Start and authenticate the client"""
        await self.client.start(phone=PHONE_NUMBER)
        
        if not await self.client.is_user_authorized():
            print("❌ Authentication failed. Please check your credentials.")
            sys.exit(1)
            
        me = await self.client.get_me()
        print(f"✅ Logged in as: {me.first_name} (@{me.username})")
        return True
    
    async def select_group(self):
        """Display all groups and let user choose one"""
        dialogs = await self.client.get_dialogs()
        
        groups = []
        print("\n" + "="*60)
        print("📋 YOUR GROUPS AND CHANNELS")
        print("="*60)
        
        for i, dialog in enumerate(dialogs):
            if dialog.is_group or dialog.is_channel:
                groups.append(dialog)
                entity_type = "Channel" if dialog.is_channel else "Group"
                member_count = getattr(dialog.entity, 'participants_count', 'Unknown')
                print(f"[{len(groups)-1:3d}] {entity_type:8s} | {dialog.name[:40]:40s} | Members: {member_count}")
        
        if not groups:
            print("❌ No groups or channels found!")
            sys.exit(1)
            
        print("="*60)
        
        while True:
            try:
                choice = int(input("\n🔍 Enter the number of the SOURCE group to scrape: "))
                if 0 <= choice < len(groups):
                    return groups[choice]
                else:
                    print(f"❌ Please enter a number between 0 and {len(groups)-1}")
            except ValueError:
                print("❌ Please enter a valid number")
    
    async def scrape_members(self, source_group):
        """Extract all members from the selected group"""
        print(f"\n⏳ Scraping members from '{source_group.name}'...")
        print("⏱️  This may take several minutes for large groups.\n")
        
        members = []
        batch_size = 100
        offset = 0
        
        while True:
            participants = await self.client.get_participants(
                source_group,
                limit=batch_size,
                offset=offset,
                aggressive=True  # Try to get all members even with restrictions
            )
            
            if not participants:
                break
                
            for user in participants:
                member_info = {
                    'id': user.id,
                    'access_hash': user.access_hash,
                    'username': user.username,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'phone': user.phone,
                    'is_bot': user.bot,
                    'scraped_at': datetime.now().isoformat()
                }
                members.append(member_info)
            
            offset += len(participants)
            print(f"  📊 Scraped {len(members)} members so far...")
            
            if len(participants) < batch_size:
                break
                
            await asyncio.sleep(2)  # Small delay to avoid rate limits
        
        print(f"\n✅ Successfully scraped {len(members)} members total!")
        return members
    
    def save_members(self, members, group_name):
        """Save members to JSON and CSV files"""
        # Save to JSON
        with open(MEMBERS_JSON, 'w', encoding='utf-8') as f:
            json.dump({
                'source_group': group_name,
                'scraped_count': len(members),
                'scraped_at': datetime.now().isoformat(),
                'members': members
            }, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved to: {MEMBERS_JSON}")
        
        # Save to CSV
        df = pd.DataFrame(members)
        df.to_csv(MEMBERS_CSV, index=False, encoding='utf-8')
        print(f"💾 Saved to: {MEMBERS_CSV}")
        
        # Display statistics
        print("\n" + "="*60)
        print("📊 SCRAPING STATISTICS")
        print("="*60)
        print(f"Total members scraped: {len(members)}")
        print(f"Members with username: {sum(1 for m in members if m['username'])}")
        print(f"Bots: {sum(1 for m in members if m['is_bot'])}")
        print(f"With phone numbers: {sum(1 for m in members if m['phone'])}")
        print("="*60)
    
    async def run(self):
        """Main execution flow"""
        try:
            await self.start_client()
            source_group = await self.select_group()
            members = await self.scrape_members(source_group)
            self.save_members(members, source_group.name)
            
        except SessionPasswordNeededError:
            print("\n❌ Two-factor authentication is enabled.")
            password = input("Enter your 2FA password: ")
            await self.client.sign_in(password=password)
            await self.run()  # Retry
            
        except Exception as e:
            print(f"\n❌ Error: {type(e).__name__}: {e}")
            
        finally:
            await self.client.disconnect()
            print("\n👋 Disconnected. Goodbye!")


async def main():
    scraper = TelegramMemberScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
