#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️ Admin Setup & Management Panel
پنل مدیریت و راه‌اندازی سیستم - فاز ۱
"""

import os
import sys
import json
import shutil
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

# وارد کردن سیستم‌های اصلی
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from game_core import DatabaseManager, GameLogic, CardManager, Card, CardRarity, Player

# ==================== SETUP CLASS ====================

class GameSetupManager:
    def __init__(self):
        self.config_path = "game_config.json"
        self.images_path = "card_images"
        self.backups_path = "backups"
        
        # ایجاد پوشه‌ها
        os.makedirs(self.images_path, exist_ok=True)
        os.makedirs(self.backups_path, exist_ok=True)
    
    def create_config_file(self) -> Dict:
        """ایجاد یا بارگیری فایل تنظیمات"""
        default_config = {
            "bot_settings": {
                "token": os.getenv("BOT_TOKEN", ""),
                "admin_user_ids": [855597318],
                "webhook_url": None,
                "webhook_port": 8443
            },
            "game_settings": {                "daily_hearts": 10,
                "heart_reset_hours": 24,
                "claim_cooldown_hours": 24,
                "ability_cooldown_hours": 24,
                "max_cards_per_page": 8,
                "card_drop_rates": {
                    "normal": 65,
                    "epic": 25,
                    "legend": 10
                }
            },
            "database": {
                "path": "game_bot.db",
                "backup_interval_hours": 24,
                "auto_backup": True
            },
            "images": {
                "path": self.images_path,
                "max_size_mb": 5,
                "allowed_formats": ["png", "jpg", "jpeg", "gif"]
            }
        }
        
        if os.path.exists(self.config_path):
            print(f"📁 بارگیری تنظیمات موجود...")
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"📝 ایجاد فایل تنظیمات جدید...")
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
    
    def setup_initial_system(self) -> bool:
        """راه‌اندازی اولیه سیستم"""
        print("🚀 راه‌اندازی سیستم بازی کارت تلگرام")
        print("=" * 50)
        
        try:
            # ایجاد تنظیمات
            config = self.create_config_file()
            
            # راه‌اندازی دیتابیس
            print("🗄️ راه‌اندازی دیتابیس...")
            db = DatabaseManager()
            manager = CardManager(db)
            
            # بررسی کارت‌ها
            existing_cards = db.get_all_cards()
            if not existing_cards:
                print("🎴 ایجاد کارت‌های اولیه...")
                added_count = manager.create_sample_cards()
                print(f"✅ {added_count} کارت اضافه شد!")
            else:
                print(f"✅ {len(existing_cards)} کارت در دیتابیس موجود است")
            
            # بررسی عکس‌ها
            self._check_images()
            
            # نمایش راهنمای راه‌اندازی
            self._show_setup_guide(config)
            
            return True
            
        except Exception as e:
            print(f"❌ خطا در راه‌اندازی: {e}")
            return False
    
    def _check_images(self):
        """بررسی وضعیت عکس‌های کارت‌ها"""
        print(f"\n🖼️ بررسی عکس‌های کارت‌ها در {self.images_path}/")
        
        if not os.path.exists(self.images_path):
            os.makedirs(self.images_path, exist_ok=True)
            print(f"✅ پوشه {self.images_path}/ ایجاد شد")
        
        image_files = []
        if os.path.exists(self.images_path):
            image_files = [f for f in os.listdir(self.images_path) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        
        if image_files:
            print(f"✅ {len(image_files)} عکس موجود است")
        else:
            print(f"⚠️ هیچ عکسی موجود نیست - ربات بدون عکس کار می‌کند")
    
    def _show_setup_guide(self, config: Dict):
        """نمایش راهنمای راه‌اندازی"""
        print(f"\n🎉 راه‌اندازی موفقیت‌آمیز بود!")
        print("=" * 30)
        print("📋 گام‌های بعدی:")
        print(f"1️⃣ فایل '{self.config_path}' را باز کنید")
        print("2️⃣ توکن ربات تلگرام را در 'bot_settings.token' قرار دهید")
        print("3️⃣ آیدی تلگرام خود را به 'admin_user_ids' اضافه کنید")
        print(f"4️⃣ عکس‌های کارت‌ها را در پوشه '{self.images_path}/' قرار دهید")
        print("5️⃣ ربات را اجرا کنید: python telegram_bot.py")
        
        if config['bot_settings']['token'] == 'YOUR_BOT_TOKEN_HERE':
            print(f"\n⚠️ هشدار: توکن ربات هنوز تنظیم نشده!")
            print("برای دریافت توکن:")
            print("• در تلگرام @BotFather را جستجو کنید")
            print("• دستور /newbot را بزنید")
            print("• مراحل ساخت ربات را دنبال کنید")
            print("• توکن دریافتی را در فایل تنظیمات قرار دهید")

# ==================== ADMIN PANEL ====================

class AdminPanel:
    def __init__(self):
        self.db = DatabaseManager()
        self.game = GameLogic(self.db)
        self.manager = CardManager(self.db)
    
    def show_main_menu(self):
        """منوی اصلی پنل مدیریت"""
        print("\n" + "="*50)
        print("👨‍💻 پنل مدیریت بازی کارت تلگرام")
        print("="*50)
        print("1️⃣ مدیریت کارت‌ها")
        print("2️⃣ مدیریت بازیکنان") 
        print("3️⃣ آمار و گزارشات")
        print("4️⃣ تنظیمات سیستم")
        print("5️⃣ پشتیبان‌گیری و بازیابی")
        print("6️⃣ راه‌اندازی اولیه")
        print("7️⃣ تست سیستم")
        print("8️⃣ اعطای کارت‌های شروعی")
        print("9️⃣ مدیریت Cooldown کارت‌ها")
        print("🔟 خروج")
        print("-" * 50)
    
    def run(self):
        """اجرای پنل مدیریت"""
        print("🎮 ورود به پنل مدیریت...")
        
        while True:
            self.show_main_menu()
            choice = input("انتخاب شما: ").strip()
            
            try:
                if choice == "1":
                    self.card_management_menu()
                elif choice == "2":
                    self.player_management_menu()
                elif choice == "3":
                    self.stats_and_reports_menu()
                elif choice == "4":
                    self.system_settings_menu()
                elif choice == "5":
                    self.backup_menu()
                elif choice == "6":
                    setup_manager = GameSetupManager()
                    setup_manager.setup_initial_system()
                elif choice == "7":
                    self.test_system()
                elif choice == "8":
                    self.grant_starter_cards_menu()
                elif choice == "9":
                    self.card_cooldown_management_menu()
                elif choice == "10":
                    print("👋 خداحافظ!")
                    break
                else:
                    print("❌ انتخاب نامعتبر!")
                    
            except KeyboardInterrupt:
                print("\n👋 خروج از پنل...")
                break
            except Exception as e:
                print(f"❌ خطا: {e}")
            
            input("\n⏸️ برای ادامه Enter بزنید...")
    
    # ==================== CARD MANAGEMENT ====================
    
    def card_management_menu(self):
        """منوی مدیریت کارت‌ها"""
        while True:
            print("\n🎴 مدیریت کارت‌ها")
            print("1. ➕ اضافه کردن کارت جدید")
            print("2. 📋 مشاهده همه کارت‌ها")
            print("3. 🔍 جستجوی کارت")
            print("4. ✏️ ویرایش کارت")
            print("5. 🗑️ حذف کارت") 
            print("6. 📊 آمار کارت‌ها")
            print("7. 🖼️ مدیریت عکس‌ها")
            print("8. ❤️ تنظیمات جان‌ها")
            print("9. 🔙 بازگشت")
            
            choice = input("انتخاب: ").strip()
            
            if choice == "1":
                self.add_new_card()
            elif choice == "2":
                self.list_all_cards()
            elif choice == "3":
                self.search_card()
            elif choice == "4":
                print("⚠️ ویرایش کارت در نسخه بعدی...")
            elif choice == "5":
                self.delete_card()
            elif choice == "6":
                self.show_card_stats()
            elif choice == "7":
                self.manage_images()
            elif choice == "8":
                self.heart_management_menu()
            elif choice == "9":
                break
            else:
                print("❌ انتخاب نامعتبر!")
    
    def add_new_card(self):
        """اضافه کردن کارت جدید"""
        print("\n➕ اضافه کردن کارت جدید")
        
        card = self.manager.add_card_interactive()
        if card:
            print(f"✅ کارت '{card.name}' با موفقیت اضافه شد!")
            self.show_card_details(card)
        else:
            print("❌ اضافه کردن کارت ناموفق بود!")
    
    def list_all_cards(self):
        """نمایش تمام کارت‌ها"""
        cards = self.db.get_all_cards()
        
        if not cards:
            print("📭 هیچ کارتی موجود نیست!")
            return
        
        print(f"\n📋 تمام کارت‌ها ({len(cards)} کارت)")
        print("=" * 60)
        
        # گروه‌بندی بر اساس کمیابی
        cards_by_rarity = {"legend": [], "epic": [], "normal": []}
        for card in cards:
            cards_by_rarity[card.rarity.value].append(card)
        
        rarity_info = {
            "legend": ("🟠 LEGEND", CardRarity.LEGEND),
            "epic": ("🟣 EPIC", CardRarity.EPIC), 
            "normal": ("🟢 NORMAL", CardRarity.NORMAL)
        }
        
        for rarity_key, (rarity_text, rarity_enum) in rarity_info.items():
            cards_list = cards_by_rarity[rarity_key]
            if cards_list:
                print(f"\n{rarity_text} ({len(cards_list)} کارت):")
                for card in cards_list:
                    stats = f"💪{card.power} ⚡{card.speed} 🧠{card.iq} ❤️{card.popularity}"
                    abilities_text = ", ".join(card.abilities[:2]) + ("..." if len(card.abilities) > 2 else "")
                    print(f"  • {card.name} ({stats}) - {abilities_text}")
    
    def search_card(self):
        """جستجوی کارت"""
        name = input("\n🔍 نام کارت: ").strip()
        if not name:
            print("❌ نام نمی‌تواند خالی باشد!")
            return
        
        card = self.db.get_card_by_name(name)
        if card:
            self.show_card_details(card)
        else:
            print(f"❌ کارت '{name}' یافت نشد!")
    
    def delete_card(self):
        """حذف کارت"""
        name = input("\n🗑️ نام کارت برای حذف: ").strip()
        if not name:
            return
        
        card = self.db.get_card_by_name(name)
        if not card:
            print(f"❌ کارت '{name}' یافت نشد!")
            return
        
        self.show_card_details(card)
        
        confirm = input("\n⚠️ آیا مطمئن هستید؟ (yes/no): ").strip().lower()
        if confirm in ['yes', 'y', 'بله']:
            if self.db.delete_card(card.card_id):
                print(f"✅ کارت '{name}' حذف شد!")
            else:
                print(f"❌ خطا در حذف کارت!")
    
    def show_card_details(self, card: Card):
        """نمایش جزئیات کارت"""
        rarity_colors = {
            CardRarity.NORMAL: "🟢",
            CardRarity.EPIC: "🟣",
            CardRarity.LEGEND: "🟠"
        }
        color = rarity_colors[card.rarity]
        
        print(f"\n{color} {card.name} ({card.rarity.value.upper()})")
        print(f"🆔 شناسه: {card.card_id}")
        print(f"📊 آمار: 💪{card.power} ⚡{card.speed} 🧠{card.iq} ❤️{card.popularity}")
        print(f"🎯 مجموع: {card.get_total_stats()}")
        print(f"✨ ابیلیتی‌ها ({len(card.abilities)}/{card.get_ability_count()}):")
        
        for i, ability in enumerate(card.abilities, 1):
            print(f"   {i}. {ability}")
        
        if card.image_path:
            image_status = "✅ موجود" if os.path.exists(card.image_path) else "❌ یافت نشد"
            print(f"🖼️ عکس: {card.image_path} ({image_status})")
        
        print(f"📅 ایجاد: {card.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def show_card_stats(self):
        """نمایش آمار کارت‌ها"""
        cards = self.db.get_all_cards()
        
        if not cards:
            print("📭 هیچ کارتی موجود نیست!")
            return
        
        print(f"\n📊 آمار کارت‌ها")
        print("=" * 30)
        
        # آمار کلی
        total_cards = len(cards)
        
        # آمار کمیابی
        rarity_stats = {rarity: 0 for rarity in CardRarity}
        for card in cards:
            rarity_stats[card.rarity] += 1
        
        print(f"🎴 تعداد کل: {total_cards}")
        print(f"🟢 Normal: {rarity_stats[CardRarity.NORMAL]} ({rarity_stats[CardRarity.NORMAL]*100//total_cards}%)")
        print(f"🟣 Epic: {rarity_stats[CardRarity.EPIC]} ({rarity_stats[CardRarity.EPIC]*100//total_cards}%)")
        print(f"🟠 Legend: {rarity_stats[CardRarity.LEGEND]} ({rarity_stats[CardRarity.LEGEND]*100//total_cards}%)")
        
        # آمار ویژگی‌ها
        if cards:
            avg_power = sum(card.power for card in cards) / total_cards
            avg_speed = sum(card.speed for card in cards) / total_cards
            avg_iq = sum(card.iq for card in cards) / total_cards
            avg_popularity = sum(card.popularity for card in cards) / total_cards
            
            print(f"\n⚡ میانگین آمار:")
            print(f"💪 قدرت: {avg_power:.1f}")
            print(f"⚡ سرعت: {avg_speed:.1f}")
            print(f"🧠 آی‌کیو: {avg_iq:.1f}")
            print(f"❤️ محبوبیت: {avg_popularity:.1f}")
            
            # قوی‌ترین کارت‌ها
            strongest = max(cards, key=lambda c: c.power)
            fastest = max(cards, key=lambda c: c.speed)
            smartest = max(cards, key=lambda c: c.iq)
            most_popular = max(cards, key=lambda c: c.popularity)
            
            print(f"\n🏆 رکوردداران:")
            print(f"💪 قوی‌ترین: {strongest.name} ({strongest.power})")
            print(f"⚡ سریع‌ترین: {fastest.name} ({fastest.speed})")
            print(f"🧠 باهوش‌ترین: {smartest.name} ({smartest.iq})")
            print(f"❤️ محبوب‌ترین: {most_popular.name} ({most_popular.popularity})")
    
    def manage_images(self):
        """مدیریت عکس‌ها"""
        print(f"\n🖼️ مدیریت عکس‌ها")
        images_dir = "card_images"
        
        if not os.path.exists(images_dir):
            os.makedirs(images_dir, exist_ok=True)
            print(f"✅ پوشه {images_dir}/ ایجاد شد")
        
        # نمایش عکس‌های موجود
        image_files = [f for f in os.listdir(images_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        
        if image_files:
            print(f"📸 عکس‌های موجود ({len(image_files)}):")
            for i, filename in enumerate(image_files, 1):
                file_path = os.path.join(images_dir, filename)
                file_size = os.path.getsize(file_path) / 1024  # KB
                print(f"   {i}. {filename} ({file_size:.1f} KB)")
        else:
            print("📭 هیچ عکسی موجود نیست!")
        
        print(f"\n💡 راهنما:")
        print(f"• عکس‌های کارت‌ها را در پوشه '{images_dir}/' قرار دهید")
        print(f"• فرمت‌های پشتیبانی: PNG, JPG, JPEG, GIF")
        print(f"• نام فایل: نام_کارت.png")
        print(f"• ابعاد پیشنهادی: 300x400 پیکسل")
    
    # ==================== PLAYER MANAGEMENT ====================
    
    def player_management_menu(self):
        """منوی مدیریت بازیکنان"""
        while True:
            print("\n👥 مدیریت بازیکنان")
            print("1. 📋 لیست همه بازیکنان")
            print("2. 🔍 جستجوی بازیکن")
            print("3. 📊 آمار بازیکنان")
            print("4. 🏆 لیدربورد کامل")
            print("5. ❤️ ریست قلب‌های همه")
            print("6. 🔙 بازگشت")
            
            choice = input("انتخاب: ").strip()
            
            if choice == "1":
                self.list_all_players()
            elif choice == "2":
                self.search_player()
            elif choice == "3":
                self.show_player_stats()
            elif choice == "4":
                self.show_full_leaderboard()
            elif choice == "5":
                self.reset_all_hearts()
            elif choice == "6":
                break
            else:
                print("❌ انتخاب نامعتبر!")
    
    def list_all_players(self):
        """نمایش همه بازیکنان"""
        leaderboard = self.db.get_leaderboard(100)  # همه بازیکنان
        
        if not leaderboard:
            print("👥 هیچ بازیکنی ثبت نشده!")
            return
        
        print(f"\n👥 همه بازیکنان ({len(leaderboard)} نفر)")
        print("=" * 60)
        
        for i, player_info in enumerate(leaderboard, 1):
            name = player_info.get('first_name', 'نامشخص')
            username = player_info.get('username', '')
            score = player_info.get('total_score', 0)
            card_count = player_info.get('card_count', 0)
            
            username_text = f"@{username}" if username else "بدون یوزرنیم"
            print(f"{i:2d}. {name} ({username_text}) - 🏆{score} امتیاز • 🎴{card_count} کارت")
    
    def search_player(self):
        """جستجوی بازیکن"""
        search_term = input("\n🔍 نام یا یوزرنیم بازیکن: ").strip()
        if not search_term:
            return
        
        leaderboard = self.db.get_leaderboard(100)
        found_players = []
        
        for player in leaderboard:
            name = player.get('first_name', '').lower()
            username = player.get('username', '').lower()
            
            if search_term.lower() in name or search_term.lower() in username:
                found_players.append(player)
        
        if found_players:
            print(f"✅ {len(found_players)} بازیکن یافت شد:")
            for player in found_players:
                name = player.get('first_name', 'نامشخص')
                username = player.get('username', '')
                score = player.get('total_score', 0)
                card_count = player.get('card_count', 0)
                user_id = player.get('user_id', 0)
                
                username_text = f"@{username}" if username else ""
                print(f"• {name} {username_text} (ID: {user_id})")
                print(f"  🏆 {score} امتیاز • 🎴 {card_count} کارت")
        else:
            print("❌ بازیکنی یافت نشد!")
    
    def show_player_stats(self):
        """نمایش آمار بازیکنان"""
        leaderboard = self.db.get_leaderboard(100)
        
        if not leaderboard:
            print("👥 هیچ بازیکنی موجود نیست!")
            return
        
        total_players = len(leaderboard)
        total_score = sum(p.get('total_score', 0) for p in leaderboard)
        total_cards = sum(p.get('card_count', 0) for p in leaderboard)
        
        active_players = len([p for p in leaderboard if p.get('total_score', 0) > 0])
        
        print(f"\n📊 آمار بازیکنان")
        print("=" * 25)
        print(f"👥 کل بازیکنان: {total_players}")
        print(f"🎮 بازیکنان فعال: {active_players}")
        print(f"🏆 کل امتیازات: {total_score}")
        print(f"🎴 کل کارت‌های توزیع شده: {total_cards}")
        
        if total_players > 0:
            avg_score = total_score / total_players
            avg_cards = total_cards / total_players
            print(f"📈 میانگین امتیاز: {avg_score:.1f}")
            print(f"📈 میانگین کارت: {avg_cards:.1f}")
        
        if leaderboard:
            top_player = leaderboard[0]
            print(f"\n🏆 بازیکن برتر: {top_player['first_name']} ({top_player['total_score']} امتیاز)")
    
    def show_full_leaderboard(self):
        """نمایش لیدربورد کامل"""
        leaderboard = self.db.get_leaderboard(50)  # تاپ 50
        
        if not leaderboard:
            print("🏆 لیدربورد خالی است!")
            return
        
        print(f"\n🏆 لیدربورد کامل (تاپ {min(len(leaderboard), 50)})")
        print("=" * 70)
        
        for i, player in enumerate(leaderboard, 1):
            name = player.get('first_name', 'نامشخص')
            score = player.get('total_score', 0)
            card_count = player.get('card_count', 0)
            
            if i <= 3:
                medals = {1: "🥇", 2: "🥈", 3: "🥉"}
                rank = medals[i]
            else:
                rank = f"{i:2d}."
            
            print(f"{rank} {name:20} 🏆{score:5} امتیاز • 🎴{card_count:2} کارت")
    
    def reset_all_hearts(self):
        """ریست قلب‌های همه بازیکنان"""
        confirm = input("⚠️ آیا مطمئن هستید که می‌خواهید قلب همه بازیکنان ریست شود؟ (yes/no): ").strip().lower()
        
        if confirm not in ['yes', 'y', 'بله']:
            print("❌ عملیات لغو شد!")
            return
        
        # این قسمت نیاز به پیاده‌سازی در DatabaseManager دارد
        print("⚠️ این قابلیت در نسخه بعدی پیاده‌سازی می‌شود!")
    
    # ==================== STATS AND REPORTS ====================
    
    def stats_and_reports_menu(self):
        """منوی آمار و گزارشات"""
        while True:
            print("\n📊 آمار و گزارشات")
            print("1. 📈 آمار کلی سیستم")
            print("2. 🎴 گزارش کارت‌ها")
            print("3. 👥 گزارش بازیکنان")
            print("4. ⚔️ آمار فایت‌ها")
            print("5. 📅 آمار روزانه")
            print("6. 🔙 بازگشت")
            
            choice = input("انتخاب: ").strip()
            
            if choice == "1":
                self.show_system_stats()
            elif choice == "2":
                self.show_card_stats()
            elif choice == "3":
                self.show_player_stats()
            elif choice == "4":
                self.show_fight_stats()
            elif choice == "5":
                self.show_daily_stats()
            elif choice == "6":
                break
            else:
                print("❌ انتخاب نامعتبر!")
    
    def show_system_stats(self):
        """نمایش آمار کلی سیستم"""
        cards = self.db.get_all_cards()
        players = self.db.get_leaderboard(1000)
        
        print(f"\n📈 آمار کلی سیستم")
        print("=" * 30)
        print(f"🎴 تعداد کارت‌ها: {len(cards)}")
        print(f"👥 تعداد بازیکنان: {len(players)}")
        
        # اطلاعات فایل‌ها
        db_size = os.path.getsize(self.db.db_path) / 1024 / 1024  # MB
        print(f"💾 حجم دیتابیس: {db_size:.2f} MB")
        
        images_dir = "card_images"
        if os.path.exists(images_dir):
            image_count = len([f for f in os.listdir(images_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))])
            print(f"🖼️ تعداد عکس‌ها: {image_count}")
        
        # وضعیت سیستم
        print(f"\n🟢 وضعیت سیستم: فعال")
        print(f"📅 تاریخ بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def show_fight_stats(self):
        """نمایش آمار فایت‌ها (اگر تاریخچه موجود باشد)"""
        print(f"\n⚔️ آمار فایت‌ها")
        print("⚠️ این قابلیت در نسخه بعدی پیاده‌سازی می‌شود!")
        print("برای دسترسی به تاریخچه فایت‌ها، جدول fight_history در دیتابیس را بررسی کنید.")
    
    def show_daily_stats(self):
        """نمایش آمار روزانه"""
        print(f"\n📅 آمار روزانه")
        print("⚠️ این قابلیت در نسخه بعدی پیاده‌سازی می‌شود!")
    
    # ==================== SYSTEM SETTINGS ====================
    
    def system_settings_menu(self):
        """منوی تنظیمات سیستم"""
        while True:
            print("\n⚙️ تنظیمات سیستم")
            print("1. 📝 مشاهده تنظیمات فعلی")
            print("2. ✏️ ویرایش تنظیمات")
            print("3. 🔄 ریست تنظیمات به حالت پیش‌فرض")
            print("4. 🔙 بازگشت")
            
            choice = input("انتخاب: ").strip()
            
            if choice == "1":
                self.show_current_settings()
            elif choice == "2":
                print("⚠️ ویرایش تنظیمات در نسخه بعدی...")
            elif choice == "3":
                self.reset_settings()
            elif choice == "4":
                break
            else:
                print("❌ انتخاب نامعتبر!")
    
    def show_current_settings(self):
        """نمایش تنظیمات فعلی"""
        config_path = "game_config.json"
        if not os.path.exists(config_path):
            print("❌ فایل تنظیمات یافت نشد!")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"\n📝 تنظیمات فعلی:")
        print("=" * 25)
        
        # تنظیمات ربات
        bot_settings = config.get('bot_settings', {})
        token_status = "تنظیم شده" if bot_settings.get('token', '') != 'YOUR_BOT_TOKEN_HERE' else "تنظیم نشده"
        admin_count = len(bot_settings.get('admin_user_ids', []))
        
        print(f"🤖 ربات:")
        print(f"   • توکن: {token_status}")
        print(f"   • تعداد ادمین‌ها: {admin_count}")
        
        # تنظیمات بازی
        game_settings = config.get('game_settings', {})
        print(f"\n🎮 بازی:")
        print(f"   • قلب‌های روزانه: {game_settings.get('daily_hearts', 5)}")
        print(f"   • کولدان کلیم: {game_settings.get('claim_cooldown_hours', 24)} ساعت")
        print(f"   • کولدان ابیلیتی: {game_settings.get('ability_cooldown_hours', 24)} ساعت")
        
        # نرخ ظهور کارت‌ها
        drop_rates = game_settings.get('card_drop_rates', {})
        print(f"\n🎴 نرخ ظهور کارت‌ها:")
        print(f"   • Normal: {drop_rates.get('normal', 65)}%")
        print(f"   • Epic: {drop_rates.get('epic', 25)}%")
        print(f"   • Legend: {drop_rates.get('legend', 10)}%")
    
    def reset_settings(self):
        """ریست تنظیمات"""
        confirm = input("⚠️ آیا مطمئن هستید؟ تمام تنظیمات به حالت پیش‌فرض برمی‌گردد! (yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y', 'بله']:
            setup_manager = GameSetupManager()
            os.remove(setup_manager.config_path)
            setup_manager.create_config_file()
            print("✅ تنظیمات ریست شد!")
        else:
            print("❌ عملیات لغو شد!")
    
    # ==================== BACKUP MENU ====================
    
    def backup_menu(self):
        """منوی پشتیبان‌گیری"""
        while True:
            print("\n💾 پشتیبان‌گیری و بازیابی")
            print("1. 📦 پشتیبان‌گیری کامل")
            print("2. 🗄️ پشتیبان‌گیری دیتابیس")
            print("3. 📋 مشاهده پشتیبان‌ها")
            print("4. 🔄 بازیابی از پشتیبان")
            print("5. 🗑️ حذف پشتیبان‌های قدیمی")
            print("6. 🔙 بازگشت")
            
            choice = input("انتخاب: ").strip()
            
            if choice == "1":
                self.create_full_backup()
            elif choice == "2":
                self.create_db_backup()
            elif choice == "3":
                self.list_backups()
            elif choice == "4":
                print("⚠️ بازیابی در نسخه بعدی...")
            elif choice == "5":
                self.clean_old_backups()
            elif choice == "6":
                break
            else:
                print("❌ انتخاب نامعتبر!")
    
    def create_full_backup(self):
        """ایجاد پشتیبان کامل"""
        backup_name = f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = os.path.join("backups", backup_name)
        
        try:
            os.makedirs(backup_path, exist_ok=True)
            
            # کپی دیتابیس
            if os.path.exists(self.db.db_path):
                shutil.copy2(self.db.db_path, os.path.join(backup_path, "game_bot.db"))
                print("✅ دیتابیس پشتیبان شد")
            
            # کپی تنظیمات
            if os.path.exists("game_config.json"):
                shutil.copy2("game_config.json", os.path.join(backup_path, "game_config.json"))
                print("✅ تنظیمات پشتیبان شد")
            
            # کپی عکس‌ها
            if os.path.exists("card_images"):
                shutil.copytree("card_images", os.path.join(backup_path, "card_images"), dirs_exist_ok=True)
                print("✅ عکس‌ها پشتیبان شد")
            
            print(f"🎉 پشتیبان کامل در {backup_path} ایجاد شد!")
            
        except Exception as e:
            print(f"❌ خطا در ایجاد پشتیبان: {e}")
    
    def create_db_backup(self):
        """پشتیبان‌گیری دیتابیس"""
        if not os.path.exists(self.db.db_path):
            print("❌ فایل دیتابیس یافت نشد!")
            return
        
        backup_name = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = os.path.join("backups", backup_name)
        
        try:
            os.makedirs("backups", exist_ok=True)
            shutil.copy2(self.db.db_path, backup_path)
            
            file_size = os.path.getsize(backup_path) / 1024  # KB
            print(f"✅ دیتابیس پشتیبان شد: {backup_name} ({file_size:.1f} KB)")
            
        except Exception as e:
            print(f"❌ خطا در پشتیبان‌گیری: {e}")
    
    def list_backups(self):
        """نمایش لیست پشتیبان‌ها"""
        if not os.path.exists("backups"):
            print("📭 هیچ پشتیبانی موجود نیست!")
            return
        
        backups = os.listdir("backups")
        if not backups:
            print("📭 هیچ پشتیبانی موجود نیست!")
            return
        
        print(f"\n📋 پشتیبان‌های موجود ({len(backups)}):")
        print("-" * 50)
        
        for backup in sorted(backups, reverse=True):
            backup_path = os.path.join("backups", backup)
            
            if os.path.isfile(backup_path):
                size = os.path.getsize(backup_path) / 1024  # KB
                mod_time = datetime.fromtimestamp(os.path.getmtime(backup_path))
                print(f"📁 {backup} ({size:.1f} KB) - {mod_time.strftime('%Y-%m-%d %H:%M')}")
            elif os.path.isdir(backup_path):
                mod_time = datetime.fromtimestamp(os.path.getmtime(backup_path))
                print(f"📂 {backup}/ - {mod_time.strftime('%Y-%m-%d %H:%M')}")
    
    def clean_old_backups(self):
        """حذف پشتیبان‌های قدیمی"""
        if not os.path.exists("backups"):
            print("📭 هیچ پشتیبانی موجود نیست!")
            return
        
        days = input("پشتیبان‌های قدیمی‌تر از چند روز حذف شوند؟ (پیش‌فرض: 30): ").strip()
        try:
            days = int(days) if days else 30
        except ValueError:
            days = 30
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for backup in os.listdir("backups"):
            backup_path = os.path.join("backups", backup)
            mod_time = datetime.fromtimestamp(os.path.getmtime(backup_path))
            
            if mod_time < cutoff_date:
                try:
                    if os.path.isfile(backup_path):
                        os.remove(backup_path)
                    elif os.path.isdir(backup_path):
                        shutil.rmtree(backup_path)
                    deleted_count += 1
                    print(f"🗑️ {backup} حذف شد")
                except Exception as e:
                    print(f"❌ خطا در حذف {backup}: {e}")
        
        if deleted_count > 0:
            print(f"✅ {deleted_count} پشتیبان قدیمی حذف شد!")
        else:
            print("✅ هیچ پشتیبان قدیمی برای حذف یافت نشد!")
    
    # ==================== TEST SYSTEM ====================
    
    def test_system(self):
        """تست سیستم"""
        print(f"\n🧪 تست سیستم")
        print("=" * 20)
        
        tests_passed = 0
        total_tests = 5
        
        # تست 1: دیتابیس
        try:
            cards = self.db.get_all_cards()
            print(f"✅ دیتابیس: {len(cards)} کارت موجود")
            tests_passed += 1
        except Exception as e:
            print(f"❌ دیتابیس: {e}")
        
        # تست 2: تنظیمات
        try:
            if os.path.exists("game_config.json"):
                print("✅ فایل تنظیمات: موجود")
                tests_passed += 1
            else:
                print("❌ فایل تنظیمات: یافت نشد")
        except Exception as e:
            print(f"❌ تنظیمات: {e}")
        
        # تست 3: پوشه عکس‌ها
        try:
            if os.path.exists("card_images"):
                print("✅ پوشه عکس‌ها: موجود")
                tests_passed += 1
            else:
                print("❌ پوشه عکس‌ها: یافت نشد")
        except Exception as e:
            print(f"❌ پوشه عکس‌ها: {e}")
        
        # تست 4: سیستم بازی
        try:
            game_test = self.db.get_all_cards()
            if game_test:
                print("✅ سیستم بازی: فعال")
                tests_passed += 1
            else:
                print("⚠️ سیستم بازی: هیچ کارتی موجود نیست")
        except Exception as e:
            print(f"❌ سیستم بازی: {e}")
        
        # تست 5: پشتیبان‌گیری
        try:
            os.makedirs("backups", exist_ok=True)
            print("✅ سیستم پشتیبان: فعال")
            tests_passed += 1
        except Exception as e:
            print(f"❌ سیستم پشتیبان: {e}")
        
        # نتیجه
        print(f"\n📊 نتیجه تست: {tests_passed}/{total_tests} موفق")
        
        if tests_passed == total_tests:
            print("🎉 همه تست‌ها موفق! سیستم آماده است.")
        elif tests_passed >= total_tests * 0.8:
            print("⚠️ اکثر تست‌ها موفق. سیستم قابل استفاده است.")
        else:
            print("❌ مشکلات مهمی وجود دارد. لطفاً مشکلات را برطرف کنید.")
    
    def grant_starter_cards_menu(self):
        """منوی اعطای کارت‌های شروعی به همه بازیکنان"""
        print("\n🎁 اعطای کارت‌های شروعی")
        print("=" * 40)
        print("این عملیات کارت‌های شروعی را به همه بازیکنان موجود می‌دهد:")
        print("• John Wick")
        print("• Heisenberg") 
        print("• Rehi")
        print()
        print("⚠️ توجه: فقط بازیکنانی که این کارت‌ها را ندارند، دریافت خواهند کرد.")
        
        confirm = input("\nآیا مطمئن هستید؟ (yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y', 'بله']:
            print("\n🔄 در حال اعطای کارت‌های شروعی...")
            
            # استفاده از CardManager برای اعطای کارت‌ها
            granted_count = self.manager.grant_starter_cards_to_all()
            
            if granted_count > 0:
                print(f"\n🎉 عملیات موفق! {granted_count} کارت به بازیکنان اعطا شد.")
            else:
                print("\n📝 همه بازیکنان قبلاً کارت‌های شروعی را دارند.")
        else:
            print("❌ عملیات لغو شد!")
        
        input("\nEnter برای ادامه...")
    
    def card_cooldown_management_menu(self):
        """منوی مدیریت Cooldown کارت‌ها"""
        while True:
            print("\n❄️ مدیریت Cooldown کارت‌ها")
            print("=" * 40)
            print("1. 📊 نمایش تنظیمات فعلی")
            print("2. ⚙️ تغییر تنظیمات کلی")
            print("3. 🎴 مدیریت Cooldown کارت خاص")
            print("4. 📋 لیست کارت‌های در Cooldown")
            print("5. 🔄 ریست همه Cooldown ها")
            print("6. 🔙 بازگشت")
            
            choice = input("انتخاب: ").strip()
            
            if choice == "1":
                self.show_cooldown_settings()
            elif choice == "2":
                self.change_cooldown_settings()
            elif choice == "3":
                self.manage_specific_card_cooldown()
            elif choice == "4":
                self.list_cards_in_cooldown()
            elif choice == "5":
                self.reset_all_cooldowns()
            elif choice == "6":
                break
            else:
                print("❌ انتخاب نامعتبر!")
    
    def show_cooldown_settings(self):
        """نمایش تنظیمات فعلی Cooldown"""
        print(f"\n📊 تنظیمات فعلی Cooldown")
        print("=" * 30)
        print(f"🔘 وضعیت: {'فعال' if self.game.CARD_COOLDOWN_ENABLED else 'غیرفعال'}")
        print(f"🎯 حد مجاز برد: {self.game.CARD_COOLDOWN_WIN_LIMIT}")
        print(f"⏰ مدت Cooldown: {self.game.CARD_COOLDOWN_HOURS} ساعت")
        print(f"🎴 کارت‌های مشمول: Epic و Legend")
        
        input("\nEnter برای ادامه...")
    
    def change_cooldown_settings(self):
        """تغییر تنظیمات کلی Cooldown"""
        print(f"\n⚙️ تغییر تنظیمات Cooldown")
        print("=" * 30)
        
        # تغییر وضعیت فعال/غیرفعال
        current_status = "فعال" if self.game.CARD_COOLDOWN_ENABLED else "غیرفعال"
        print(f"وضعیت فعلی: {current_status}")
        new_status = input("فعال کردن؟ (y/n): ").strip().lower()
        if new_status in ['y', 'yes', 'بله']:
            self.game.CARD_COOLDOWN_ENABLED = True
            print("✅ Cooldown فعال شد")
        elif new_status in ['n', 'no', 'نه']:
            self.game.CARD_COOLDOWN_ENABLED = False
            print("❌ Cooldown غیرفعال شد")
        
        # تغییر حد مجاز برد
        print(f"\nحد مجاز برد فعلی: {self.game.CARD_COOLDOWN_WIN_LIMIT}")
        try:
            new_limit = int(input("حد جدید (Enter برای عدم تغییر): ").strip())
            if new_limit > 0:
                self.game.CARD_COOLDOWN_WIN_LIMIT = new_limit
                print(f"✅ حد مجاز برد به {new_limit} تغییر یافت")
        except ValueError:
            pass
        
        # تغییر مدت Cooldown
        print(f"\nمدت Cooldown فعلی: {self.game.CARD_COOLDOWN_HOURS} ساعت")
        try:
            new_hours = int(input("مدت جدید به ساعت (Enter برای عدم تغییر): ").strip())
            if new_hours > 0:
                self.game.CARD_COOLDOWN_HOURS = new_hours
                print(f"✅ مدت Cooldown به {new_hours} ساعت تغییر یافت")
        except ValueError:
            pass
        
        print("\n💾 تنظیمات جدید اعمال شد!")
        input("Enter برای ادامه...")
    
    def manage_specific_card_cooldown(self):
        """مدیریت Cooldown کارت خاص"""
        print(f"\n🎴 مدیریت Cooldown کارت خاص")
        print("=" * 30)
        
        # نمایش لیست کارت‌های Epic و Legend
        all_cards = self.db.get_all_cards()
        epic_legend_cards = [card for card in all_cards if card.rarity.value in ['epic', 'legend']]
        
        if not epic_legend_cards:
            print("❌ هیچ کارت Epic یا Legend یافت نشد!")
            input("Enter برای ادامه...")
            return
        
        print("کارت‌های Epic و Legend:")
        for i, card in enumerate(epic_legend_cards, 1):
            rarity_icon = "🟣" if card.rarity.value == "epic" else "🟡"
            print(f"{i}. {rarity_icon} {card.name}")
        
        try:
            choice = int(input("\nانتخاب کارت (شماره): ").strip())
            if 1 <= choice <= len(epic_legend_cards):
                selected_card = epic_legend_cards[choice - 1]
                self.manage_card_cooldown_actions(selected_card)
            else:
                print("❌ انتخاب نامعتبر!")
        except ValueError:
            print("❌ لطفاً عدد وارد کنید!")
        
        input("Enter برای ادامه...")
    
    def manage_card_cooldown_actions(self, card):
        """اعمال عملیات روی کارت خاص"""
        print(f"\n🎴 مدیریت {card.name}")
        print("=" * 20)
        print("1. 📊 نمایش آمار Cooldown")
        print("2. 🔄 ریست Cooldown همه بازیکنان")
        print("3. 👤 ریست Cooldown بازیکن خاص")
        
        action = input("انتخاب: ").strip()
        
        if action == "1":
            self.show_card_cooldown_stats(card)
        elif action == "2":
            self.reset_card_cooldown_all_players(card)
        elif action == "3":
            self.reset_card_cooldown_specific_player(card)
    
    def show_card_cooldown_stats(self, card):
        """نمایش آمار Cooldown کارت"""
        # این تابع نیاز به پیاده‌سازی در game_core دارد
        print(f"\n📊 آمار Cooldown برای {card.name}")
        print("⚠️ این قابلیت در نسخه بعدی پیاده‌سازی می‌شود!")
    
    def reset_card_cooldown_all_players(self, card):
        """ریست Cooldown کارت برای همه بازیکنان"""
        confirm = input(f"⚠️ آیا مطمئن هستید که می‌خواهید Cooldown {card.name} را برای همه بازیکنان ریست کنید؟ (yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y', 'بله']:
            # پیاده‌سازی ریست در game_core
            print(f"🔄 در حال ریست Cooldown {card.name} برای همه بازیکنان...")
            print("⚠️ این قابلیت در نسخه بعدی پیاده‌سازی می‌شود!")
        else:
            print("❌ عملیات لغو شد!")
    
    def reset_card_cooldown_specific_player(self, card):
        """ریست Cooldown کارت برای بازیکن خاص"""
        try:
            user_id = int(input("User ID بازیکن: ").strip())
            print(f"🔄 در حال ریست Cooldown {card.name} برای بازیکن {user_id}...")
            print("⚠️ این قابلیت در نسخه بعدی پیاده‌سازی می‌شود!")
        except ValueError:
            print("❌ User ID نامعتبر!")
    
    def list_cards_in_cooldown(self):
        """لیست کارت‌های در حالت Cooldown"""
        print(f"\n📋 کارت‌های در حالت Cooldown")
        print("=" * 30)
        print("⚠️ این قابلیت در نسخه بعدی پیاده‌سازی می‌شود!")
        input("Enter برای ادامه...")
    
    def reset_all_cooldowns(self):
        """ریست همه Cooldown ها"""
        print(f"\n🔄 ریست همه Cooldown ها")
        print("=" * 25)
        
        confirm = input("⚠️ آیا مطمئن هستید که می‌خواهید همه Cooldown ها را ریست کنید؟ (yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y', 'بله']:
            print("🔄 در حال ریست همه Cooldown ها...")
            print("⚠️ این قابلیت در نسخه بعدی پیاده‌سازی می‌شود!")
        else:
            print("❌ عملیات لغو شد!")
        
        input("Enter برای ادامه...")
    
    def heart_management_menu(self):
        """منوی مدیریت جان‌ها"""
        while True:
            print("\n❤️ مدیریت جان‌ها")
            print("=" * 30)
            print("1. 📊 نمایش تنظیمات فعلی")
            print("2. ⚙️ تغییر تعداد جان روزانه")
            print("3. 🔄 ریست جان همه بازیکنان")
            print("4. 👤 تغییر جان بازیکن خاص")
            print("5. 📋 نمایش آمار جان‌ها")
            print("6. 🔙 بازگشت")
            
            choice = input("انتخاب: ").strip()
            
            if choice == "1":
                self.show_heart_settings()
            elif choice == "2":
                self.change_daily_hearts()
            elif choice == "3":
                self.reset_all_hearts()
            elif choice == "4":
                self.change_player_hearts()
            elif choice == "5":
                self.show_heart_stats()
            elif choice == "6":
                break
            else:
                print("❌ انتخاب نامعتبر!")
    
    def show_heart_settings(self):
        """نمایش تنظیمات فعلی جان‌ها"""
        print(f"\n📊 تنظیمات فعلی جان‌ها")
        print("=" * 30)
        print(f"❤️ جان روزانه: {self.game.DAILY_HEARTS}")
        print(f"⏰ ریست هر: {self.game.HEART_RESET_HOURS} ساعت")
        print(f"📜 قوانین کم شدن جان:")
        print(f"   • باخت عادی: -1 جان")
        print(f"   • Legend شکست از Normal: -2 جان")
        print(f"   • Normal شکست از Legend: 0 جان")
        print(f"   • Legend مساوی با Normal: -1 جان از Legend")
        
        input("\nEnter برای ادامه...")
    
    def change_daily_hearts(self):
        """تغییر تعداد جان روزانه"""
        print(f"\n⚙️ تغییر تعداد جان روزانه")
        print("=" * 30)
        print(f"تعداد فعلی: {self.game.DAILY_HEARTS} جان")
        
        try:
            new_hearts = int(input("تعداد جدید (1-50): ").strip())
            if 1 <= new_hearts <= 50:
                old_hearts = self.game.DAILY_HEARTS
                self.game.DAILY_HEARTS = new_hearts
                
                # بروزرسانی در فایل config (اختیاری)
                print(f"✅ تعداد جان روزانه از {old_hearts} به {new_hearts} تغییر یافت!")
                print("💡 این تغییر برای بازیکنان جدید و ریست‌های بعدی اعمال می‌شود.")
                
                # سوال برای اعمال فوری
                apply_now = input("آیا می‌خواهید این تغییر را فوراً برای همه بازیکنان اعمال کنید؟ (y/n): ").strip().lower()
                if apply_now in ['y', 'yes', 'بله']:
                    self.apply_new_hearts_to_all(new_hearts)
                
            else:
                print("❌ تعداد باید بین 1 تا 50 باشد!")
        except ValueError:
            print("❌ لطفاً عدد معتبر وارد کنید!")
        
        input("Enter برای ادامه...")
    
    def apply_new_hearts_to_all(self, new_hearts):
        """اعمال تعداد جان جدید برای همه بازیکنان"""
        print(f"🔄 در حال اعمال {new_hearts} جان برای همه بازیکنان...")
        
        # این قسمت نیاز به پیاده‌سازی در DatabaseManager دارد
        try:
            # فعلاً یک پیام نمایش می‌دهیم
            print("⚠️ این قابلیت در نسخه بعدی کامل پیاده‌سازی می‌شود!")
            print("💡 فعلاً فقط تنظیمات پیش‌فرض تغییر یافت.")
        except Exception as e:
            print(f"❌ خطا در اعمال تغییرات: {e}")
    
    def reset_all_hearts(self):
        """ریست جان همه بازیکنان"""
        print(f"\n🔄 ریست جان همه بازیکنان")
        print("=" * 30)
        
        confirm = input(f"⚠️ آیا مطمئن هستید که می‌خواهید جان همه بازیکنان به {self.game.DAILY_HEARTS} ریست شود؟ (yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y', 'بله']:
            print("🔄 در حال ریست جان همه بازیکنان...")
            print("⚠️ این قابلیت در نسخه بعدی کامل پیاده‌سازی می‌شود!")
        else:
            print("❌ عملیات لغو شد!")
        
        input("Enter برای ادامه...")
    
    def change_player_hearts(self):
        """تغییر جان بازیکن خاص"""
        print(f"\n👤 تغییر جان بازیکن خاص")
        print("=" * 30)
        
        try:
            user_id = int(input("User ID بازیکن: ").strip())
            new_hearts = int(input(f"تعداد جان جدید (0-{self.game.DAILY_HEARTS}): ").strip())
            
            if 0 <= new_hearts <= self.game.DAILY_HEARTS:
                print(f"🔄 در حال تغییر جان بازیکن {user_id} به {new_hearts}...")
                print("⚠️ این قابلیت در نسخه بعدی کامل پیاده‌سازی می‌شود!")
            else:
                print(f"❌ تعداد جان باید بین 0 تا {self.game.DAILY_HEARTS} باشد!")
                
        except ValueError:
            print("❌ لطفاً اعداد معتبر وارد کنید!")
        
        input("Enter برای ادامه...")
    
    def show_heart_stats(self):
        """نمایش آمار جان‌ها"""
        print(f"\n📋 آمار جان‌ها")
        print("=" * 20)
        print("⚠️ این قابلیت در نسخه بعدی کامل پیاده‌سازی می‌شود!")
        print("💡 آمار شامل:")
        print("   • توزیع جان بازیکنان")
        print("   • میانگین جان باقی‌مانده")
        print("   • بازیکنان با جان صفر")
        
        input("Enter برای ادامه...")

# ==================== MAIN FUNCTION ====================

def main():
    """اجرای اصلی پنل مدیریت"""
    print("🎮 پنل مدیریت بازی کارت تلگرام - فاز 1")
    print("نسخه: 1.0.0")
    print()
    
    try:
        panel = AdminPanel()
        panel.run()
    except KeyboardInterrupt:
        print("\n👋 خروج از پنل مدیریت!")
    except Exception as e:
        print(f"\n❌ خطا: {e}")

if __name__ == "__main__":
    main()