#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic Handlers - start, help, profile, cards, claim, leaderboard
"""

import json
import os
import logging
import random
import sqlite3
from html import escape
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import telegram
import telegram.error
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, WebAppInfo
from telegram.ext import Application, ContextTypes

from game_core import DatabaseManager, GameLogic, CardManager, StatType, Card, CardRarity, Player, PvPFight, FightStatus
from systems.fusion_system import FusionSystem
from systems.phase2_systems import LevelSystem, TierSystem, format_xp_bar, format_tier_badge
from systems.economy_system import EconomySystem
from systems.tier_decay_system import TierDecaySystem
from systems.risk_mode_system import RiskModeSystem, RiskTable, RiskAction
from systems.battle_system_3rounds import BattleSystem3Rounds, BattleState, ARENAS
from systems.card_missions_system import CardMissionsSystem, MISSION_TYPES
from systems.skins_system import SkinsSystem, SKIN_TYPES

logger = logging.getLogger(__name__)

from bot.utils import (check_user_started_bot, handle_user_not_started, ensure_text_content,
    get_card_image_path, get_victory_dialog, send_card_image_safely, ensure_not_expired,
    REQUIRED_CHANNEL, PANEL_TIMEOUT)




class BasicHandlersMixin:
    """Basic Handlers - start, help, profile, cards, claim, leaderboard"""

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ط¯ط³طھظˆط± ط´ط±ظˆط¹ ط¨ط§ط²غŒ - غŒع©ط¨ط§ط± ط§ط¬ط±ط§ ظ…غŒâ€Œط´ظˆط¯"""
        user = update.effective_user
        chat_type = update.effective_chat.type
        logger.info(f"start_command invoked by user_id={getattr(user,'id',None)} chat_type={chat_type}")

        try:
            # Ensure player exists in private chats
            card_count = 0
            if chat_type == 'private':
                player = self.db.get_or_create_player(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name
                )
                player = self.game.check_and_reset_hearts(player)
                card_count = len(self.db.get_player_cards(user.id))

                # Grant starter cards once if player has none
                try:
                    if card_count == 0:
                        from systems.starter_cards_system import grant_starter_cards
                        granted = grant_starter_cards(self.db, user.id)
                        if granted:
                            try:
                                if hasattr(update, 'message') and update.message:
                                    await update.message.reply_text(
                                        f"ًںژ´ ع©ط§ط±طھâ€Œظ‡ط§غŒ ط´ط±ظˆط¹غŒ ط¨ظ‡طھ ط¯ط§ط¯ظ‡ ط´ط¯: {', '.join(granted)}"
                                    )
                                elif hasattr(update, 'callback_query') and update.callback_query:
                                    await update.callback_query.message.reply_text(
                                        f"ًںژ´ ع©ط§ط±طھâ€Œظ‡ط§غŒ ط´ط±ظˆط¹غŒ ط¨ظ‡طھ ط¯ط§ط¯ظ‡ ط´ط¯: {', '.join(granted)}"
                                    )
                            except Exception:
                                pass
                        # refresh card count after granting
                        card_count = len(self.db.get_player_cards(user.id))
                except Exception as e:
                    logger.warning(f"Failed to grant starter cards to {user.id}: {e}")
            else:
                player = None

            # Channel membership check
            if False:
                await self.send_channel_join_message(update)
                return

            # Telegram deep-link invitations for the new game modes must be
            # handled before rendering the normal private start menu.
            if chat_type == 'private' and await self.handle_game_invite_start(update, context):
                return

            # Group behavior
            if chat_type in ['group', 'supergroup']:
                active = self.db.get_active_fight_for_group(update.effective_chat.id)
                if active:
                    await update.message.reply_text("ًں¥ٹ غŒع© ع†ط§ظ„ط´ ظپط¹ط§ظ„ ط¯ط± ط§غŒظ† ع¯ط±ظˆظ‡ ط¬ط±غŒط§ظ† ط¯ط§ط±ط¯. ط§ط² ظ¾ظ†ظ„ ظ…ظˆط¬ظˆط¯ ط§ط³طھظپط§ط¯ظ‡ ع©ظ†غŒط¯.")
                else:
                    await update.message.reply_text("â„¹ï¸ڈ ط¨ط±ط§غŒ ط´ط±ظˆط¹ ط¨ط§ط²غŒ ط§ط² ظ¾غŒظˆغŒ ط§ط³طھظپط§ط¯ظ‡ ع©ظ†.")
                return

            # Private: send welcome/menu
            welcome_text = (
                'ًںژ® ط¨ظ‡ ظ†ط¨ط±ط¯ ط§ظپط³ط§ظ†ظ‡â€Œظ‡ط§ ط®ظˆط´ ط§ظˆظ…ط¯غŒ!\n'
                'ط¯ظ†غŒط§غŒغŒ ع©ظ‡ ظ‚ظ‡ط±ظ…ط§ظ†â€Œظ‡ط§ط´ ط§ط² طھظ…ط§ظ… ط¯ظ†غŒط§ظ‡ط§غŒ ط®غŒط§ظ„غŒ ط¬ظ…ط¹ ط´ط¯ظ†...\n'
                'ًں“œ ط¨ط±ط§غŒ ط¯غŒط¯ظ† ط¯ط§ط³طھط§ظ† ط¨ط§ط²غŒ ط¨ظ†ظˆغŒط³غŒط¯: /story'
            )

            miniapp_url = (
                os.environ.get("MINIAPP_URL")
                or self.config.get("miniapp_url", "")
            )
            keyboard = [
                *([[InlineKeyboardButton("ًںژ® Solo vs ط¢ط³ظˆ", web_app=WebAppInfo(url=miniapp_url))]] if miniapp_url else []),
                [InlineKeyboardButton("ًںژ´ ع©ط§ط±طھâ€Œظ‡ط§غŒ ظ…ظ†", callback_data="my_cards"),
                 InlineKeyboardButton("ًں—‚ï¸ڈ ط¯ع©â€Œظ‡ط§غŒ ظ…ظ†", callback_data="deck_menu")],
                [InlineKeyboardButton("âڑ”ï¸ڈ ع†ط§ظ„ط´ PvP", callback_data="request_pvp_fight"),
                 InlineKeyboardButton("ًںژ² Risk Mode", callback_data="risk_menu")],
                [InlineKeyboardButton("ًںژپ ع©ظ„غŒظ… ط±ظˆط²ط§ظ†ظ‡", callback_data="daily_claim"),
                 InlineKeyboardButton("ًںژں Silver Claim", callback_data="v2_silver_claim") if __import__("systems.progression_config", fromlist=["enabled"]).enabled(self.db) else InlineKeyboardButton("â›ڈï¸ڈ ظ…ط§غŒظ†غŒظ†ع¯", callback_data="mining_claim")],
                [InlineKeyboardButton("ًں”® Fusion ع©ط§ط±طھâ€Œظ‡ط§", callback_data="fusion_menu"),
                 InlineKeyboardButton("ًں›’ ط´ط§ظ¾", callback_data="shop_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
                elif hasattr(update, 'callback_query') and update.callback_query:
                    try:
                        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
                    except Exception:
                        await update.callback_query.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to send welcome text in start_command: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Unhandled exception in start_command: {e}", exc_info=True)
            try:
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text("â‌Œ ط®ط·ط§ ط¯ط± ط§ط¬ط±ط§غŒ ط¯ط³طھظˆط± /start. ظ„ط·ظپط§ظ‹ ط¯ظˆط¨ط§ط±ظ‡ طھظ„ط§ط´ ع©ظ†غŒط¯ غŒط§ ط¨ط§ ظ¾ط´طھغŒط¨ط§ظ†غŒ طھظ…ط§ط³ ط¨ع¯غŒط±غŒط¯.")
                elif hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.message.reply_text("â‌Œ ط®ط·ط§ ط¯ط± ط§ط¬ط±ط§غŒ ط¯ط±ط®ظˆط§ط³طھ. ظ„ط·ظپط§ظ‹ ط¯ظˆط¨ط§ط±ظ‡ /start ط±ط§ ط¯ط± ظ¾غŒظˆغŒ ط¨ط²ظ†غŒط¯.")
            except Exception:
                pass

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ط±ط§ظ‡ظ†ظ…ط§غŒ ط¨ط§ط²غŒ"""
        cfg_help = self.config.get('texts', {}).get('help')
        if cfg_help and isinstance(cfg_help, str) and cfg_help.strip():
            help_text = cfg_help
        else:
            help_text = (
                "ًں“– **ط±ط§ظ‡ظ†ظ…ط§غŒ ط¨ط§ط²غŒ ع©ط§ط±طھâ€Œظ‡ط§**\n\n"
                "ًںژ¯ ع©ط§ط±طھ ط¬ظ…ط¹ ع©ظ†طŒ ظ…ط¨ط§ط±ط²ظ‡ ع©ظ†طŒ ط§ظ…طھغŒط§ط² ط¨ع¯غŒط±!\n\n"
                "ًںƒڈ ط±ط±غŒطھغŒâ€Œظ‡ط§: ًںں¢ Normal â€¢ ًںں£ Epic â€¢ ًںں، Legend\n"
                f"ًںژپ ع©ط§ط±طھ ط±ظˆط²ط§ظ†ظ‡ ظ‡ط± {self.game.CLAIM_COOLDOWN_HOURS} ط³ط§ط¹طھ\n"
                "ًں¥ٹ PvP ط¯ط± ع¯ط±ظˆظ‡â€Œظ‡ط§: ع†ط§ظ„ط´ ط¨ط¯ظ‡ غŒط§ ظ‚ط¨ظˆظ„ ع©ظ†\n"
                "âڑ™ï¸ڈ ط¯ط± ظ…ط³ط§ظˆغŒ ط§ظ…طھغŒط§ط²/ظ‚ظ„ط¨غŒ ع©ظ… غŒط§ ط²غŒط§ط¯ ظ†ظ…غŒâ€Œط´ظˆط¯\n"
            )
        
        if update.callback_query:
            keyboard = [[InlineKeyboardButton("ًں”™ ط¨ط§ط²ع¯ط´طھ", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text(
                help_text, reply_markup=reply_markup, parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(help_text, parse_mode='Markdown')

    async def story_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ط§ط±ط³ط§ظ„ ط¯ط§ط³طھط§ظ† ط³غŒظ†ظ…ط§طھغŒع© ط¨ط§ط²غŒ (/story)"""
        story_text = (
            'ًں¤– ط¯ط± ط¢غŒظ†ط¯ظ‡â€Œط§غŒ ظ†ظ‡â€Œع†ظ†ط¯ط§ظ† ط¯ظˆط±طŒ ظ‡ظˆط´ ظ…طµظ†ظˆط¹غŒ ط¨ظ‡ ظ…ط±ط­ظ„ظ‡â€Œط§غŒ ظ…غŒâ€Œط±ط³ظ‡ ع©ظ‡ ظ…غŒâ€Œطھظˆظ†ظ‡ طھظ…ط§ظ… ط³ط±غŒط§ظ„â€Œظ‡ط§طŒ ظپغŒظ„ظ…â€Œظ‡ط§طŒ ط§ظ†غŒظ…غŒط´ظ†â€Œظ‡ط§ ظˆ ط¨ط§ط²غŒâ€Œظ‡ط§ ط±ظˆ ط¢ظ†ط§ظ„غŒط² ع©ظ†ظ‡.\n'
            'ط§ط² ط¯ظ„ ط§غŒظ† ط§ظ„ع¯ظˆط±غŒطھظ…â€Œظ‡ط§ ط´ط®طµغŒطھâ€Œظ‡ط§غŒ ط§ظپط³ط§ظ†ظ‡â€Œط§غŒ ط¨غŒط±ظˆظ† ظ…غŒط§ظ†...\n\n'
            'âڑ”ï¸ڈ ط§غŒظ† ظپظ‚ط· ط¨ط§ط²ط³ط§ط²غŒ ظ†غŒط³طھ â€” ط§غŒظ† ط¯ط¹ظˆطھ ط¨ظ‡ ظ†ط¨ط±ط¯ظ‡!\n\n'
            'ظ‡ظ…ظ‡â€ŒغŒ ظ†ظ…ط§ط¯ظ‡ط§غŒ ط¯ظ†غŒط§غŒ ط³ط±ع¯ط±ظ…غŒطŒ ط§ط² ط¯ط§ط±ط« ظˆغŒط¯ط± طھط§ ظ¾ط¯ط±ط®ظˆط§ظ†ط¯ظ‡طŒ ط§ط² ط¬ظˆع©ط± طھط§ ظ‡ط§ظ„ع©طŒ ط§ط² ع¯ط§ط³ ظپط±غŒظ†ع¯ طھط§ ظ‡ظˆظ…â€Œظ„ظ†ط¯ط±طŒ ظˆط§ط±ط¯ غŒع© ط¯ظ†غŒط§غŒ ط¨غŒâ€Œظ¾ط§غŒط§ظ† ظ…غŒâ€Œط´ظ†.\n'
            'ظ‚ط§ظ†ظˆظ† ظپظ‚ط· غŒع©غŒظ‡: ظ‚ط¯ط±طھ ظˆط§ظ‚ط¹غŒ ط±ظˆ ع©ط§ط±طھâ€Œظ‡ط§ طھط¹غŒغŒظ† ظ…غŒâ€Œع©ظ†ظ†.\n\n'
            'ًںژ´ طھظˆ ط§ظ†طھط®ط§ط¨ ظ…غŒâ€Œع©ظ†غŒ.\n'
            'ًںژ® طھظˆ ط¨ط§ط²غŒ ظ…غŒâ€Œع©ظ†غŒ.\n'
            'ًں”¥ طھظˆ طھطµظ…غŒظ… ظ…غŒâ€Œع¯غŒط±غŒ ع©ط¯ظˆظ… ظ†ظ…ط§ط¯طŒ ط§ظپط³ط§ظ†ظ‡â€ŒغŒ ظ†ظ‡ط§غŒغŒ ط¨ط´ظ‡.\n\n'
            'ًں•¹ ط¨ط§ط²غŒ ط´ط±ظˆط¹ ط´ط¯ظ‡...'
        )

        try:
            await update.message.reply_text(story_text, parse_mode='Markdown')
        except Exception:
            # fallback: plain text
            await update.message.reply_text(story_text)
    
    async def recalc_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ط¯ط³طھظˆط± admin ط¨ط±ط§غŒ recalculate ع©ط±ط¯ظ† total_score ظ‡ط§"""
        user_id = update.effective_user.id
        
        # ظپظ‚ط· admin ظ‡ط§ ظ…غŒâ€Œطھظˆظ†ظ† ط§ط³طھظپط§ط¯ظ‡ ع©ظ†ظ†
        admin_ids = [1685691201, 5735941901]  # IDs ط´ظ…ط§
        if user_id not in admin_ids:
            await update.message.reply_text("â‌Œ ط´ظ…ط§ ظ…ط¬ظˆط² ط§ط³طھظپط§ط¯ظ‡ ط§ط² ط§غŒظ† ط¯ط³طھظˆط± ط±ط§ ظ†ط¯ط§ط±غŒط¯.")
            return
        
        await update.message.reply_text("ًں”„ ط¯ط± ط­ط§ظ„ ظ…ط­ط§ط³ط¨ظ‡ ظ…ط¬ط¯ط¯ ط§ظ…طھغŒط§ط²ط§طھ...")
        
        try:
            updated_count = self.db.recalculate_all_total_scores()
            await update.message.reply_text(f"âœ… ط§ظ…طھغŒط§ط²ط§طھ {updated_count} ط¨ط§ط²غŒع©ظ† ط¨ط±ظˆط²ط±ط³ط§ظ†غŒ ط´ط¯!")
        except Exception as e:
            await update.message.reply_text(f"â‌Œ ط®ط·ط§: {str(e)}")

    async def check_membership_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ط¨ط±ط±ط³غŒ ط¹ط¶ظˆغŒطھ ع©ط§ط±ط¨ط± ط¨ط¹ط¯ ط§ط² ع©ظ„غŒع© ط¯ع©ظ…ظ‡"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if await self.is_user_in_channel(user.id, context):
            # ع©ط§ط±ط¨ط± ط¹ط¶ظˆ ط´ط¯ظ‡ - ط´ط±ظˆط¹ ط¨ط§ط²غŒ
            text = (
                f"âœ… **ط¹ط§ظ„غŒ! ط´ظ…ط§ ط¨ط§ظ…ظˆظپظ‚غŒطھ ط¯ط± ع©ط§ظ†ط§ظ„ ط¹ط¶ظˆ ط´ط¯غŒط¯.**\n\n"
                f"ًںژ‰ ط®ظˆط´ ط¢ظ…ط¯غŒط¯ {user.first_name}!\n"
                f"ًںژ® ط­ط§ظ„ط§ ظ…غŒâ€Œطھظˆط§ظ†غŒط¯ ط§ط² ط±ط¨ط§طھ ط§ط³طھظپط§ط¯ظ‡ ع©ظ†غŒط¯.\n\n"
                f"ط¨ط±ط§غŒ ط´ط±ظˆط¹ ط¯ظˆط¨ط§ط±ظ‡ /start ط¨ط²ظ†غŒط¯."
            )
            keyboard = [[InlineKeyboardButton("ًںژ® ط´ط±ظˆط¹ ط¨ط§ط²غŒ", callback_data="start_game")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            # ظ‡ظ†ظˆط² ط¹ط¶ظˆ ظ†ط´ط¯ظ‡
            await query.answer("â‌Œ ظ‡ظ†ظˆط² ط¯ط± ع©ط§ظ†ط§ظ„ ط¹ط¶ظˆ ظ†ط´ط¯ظ‡â€Œط§غŒط¯. ظ„ط·ظپط§ظ‹ ط§ط¨طھط¯ط§ ط¹ط¶ظˆ ط´ظˆغŒط¯.", show_alert=True)

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ†ظ…ط§غŒط´ ظ¾ط±ظˆظپط§غŒظ„ ع©ط§ط±ط¨ط±"""
        if not self._is_command_allowed_in_chat("profile", update.effective_chat.type):
            await update.message.reply_text(
                "ًںڑ« ط§غŒظ† ط¯ط³طھظˆط± ظپظ‚ط· ط¯ط± ع†طھ ط®طµظˆطµغŒ ظ‚ط§ط¨ظ„ ط§ط³طھظپط§ط¯ظ‡ ط§ط³طھ.\n"
                "ًں“± ط¨ط±ط§غŒ ظ…ط´ط§ظ‡ط¯ظ‡ ظ¾ط±ظˆظپط§غŒظ„ ط®ظˆط¯طŒ ط§ط² ظ¾غŒظˆغŒ ط±ط¨ط§طھ ط§ط³طھظپط§ط¯ظ‡ ع©ظ†غŒط¯."
            )
            return

        user = update.effective_user

        if False:
            await self.send_channel_join_message(update)
            return

        player = self.db.get_or_create_player(user.id, user.username, user.first_name)
        card_counts = self.db.get_player_card_counts(user.id)
        stats = self.db.get_player_stats(user.id)
        rank = self.db.get_player_rank(user.id)
        prog = self.db.get_or_create_progression(user.id)

        # Level & XP
        level = prog['level']
        total_xp = prog['total_xp']
        tier = prog['current_tier']
        tp = prog['tier_points']

        if level < 30:
            cur_lv, xp_in, xp_needed = LevelSystem.get_xp_progress(total_xp)
            xp_bar = format_xp_bar(xp_in, xp_needed)
            xp_text = f"{xp_bar} ({xp_in}/{xp_needed})"
        else:
            xp_text = "MAX LEVEL âœ¨"

        from systems.progression_config import enabled
        v2 = enabled(self.db)
        tier_badge = format_tier_badge(tier)
        level_line = f"â­گ Level {level}\n" if v2 else f"â­گ Level {level}  {tier_badge} {tier}  â€¢  {tp} TP\n"
        rank_text = f"#{rank}" if rank else "N/A"
        total_stats = stats.get('total', {'games_played': 0, 'wins': 0, 'losses': 0, 'ties': 0, 'win_rate': 0})

        text = (
            f"ًں‘¤ **{user.first_name}**\n\n"
            f"{level_line}"
            f"ًں“ˆ XP: {xp_text}\n\n"
            f"ًں’° ط³ع©ظ‡: {getattr(player, 'coins', 0):,}\n"
            f"â‌¤ï¸ڈ ط¬ط§ظ†: {player.hearts}/{getattr(player, 'max_hearts', self.game.DAILY_HEARTS)}\n"
            f"ًںڈ† ط§ظ…طھغŒط§ط²: {player.total_score}  â€¢  ط±طھط¨ظ‡: {rank_text}\n"
            f"ًںژ´ ع©ط§ط±طھâ€Œظ‡ط§: {card_counts.get('total', 0)} "
            f"(ًںں¢{card_counts.get('normal',0)} ًںں£{card_counts.get('epic',0)} ًںں،{card_counts.get('legend',0)})\n\n"
            f"âڑ”ï¸ڈ **ط¢ظ…ط§ط± ظپط§غŒطھ:**\n"
            f"  ط¨ط§ط²غŒ: {total_stats['games_played']}  â€¢  "
            f"ط¨ط±ط¯: {total_stats['wins']}  â€¢  "
            f"ط¨ط§ط®طھ: {total_stats['losses']}  â€¢  "
            f"ظ†ط±ط® ط¨ط±ط¯: {int(total_stats['win_rate'])}%"
        )

        keyboard = [
            [InlineKeyboardButton("ًںژ´ ع©ط§ط±طھâ€Œظ‡ط§غŒ ظ…ظ†", callback_data="my_cards"),
             InlineKeyboardButton("ًںڈ† ظ„غŒط¯ط±ط¨ط±ط¯", callback_data="leaderboard")],
            [InlineKeyboardButton("ًں”™ ظ…ظ†ظˆغŒ ط§طµظ„غŒ", callback_data="back_to_main")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def start_game_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline 'ط´ط±ظˆط¹ ط¨ط§ط²غŒ' button by invoking the start command flow."""
        query = update.callback_query
        await query.answer()

        # Perform the start flow directly for callback queries to avoid potential update/message differences
        try:
            user = query.from_user
            chat = query.message.chat

            # Ensure player exists and reset hearts
            player = self.db.get_or_create_player(user.id, user.username, user.first_name)
            player = self.game.check_and_reset_hearts(player)

            # Grant starter cards if none
            try:
                card_count = len(self.db.get_player_cards(user.id))
                if card_count == 0:
                    from systems.starter_cards_system import grant_starter_cards
                    granted = grant_starter_cards(self.db, user.id)
                    if granted:
                        await context.bot.send_message(chat_id=chat.id, text=f"ًںژ´ ع©ط§ط±طھâ€Œظ‡ط§غŒ ط´ط±ظˆط¹غŒ ط¨ظ‡طھ ط¯ط§ط¯ظ‡ ط´ط¯: {', '.join(granted)}")
            except Exception as e:
                logger.warning(f"Failed to grant starter cards in callback start_game for {user.id}: {e}")

            # Send the welcome/menu (same as private start)
            welcome_text = (
                'ًںژ® ط¨ظ‡ ظ†ط¨ط±ط¯ ط§ظپط³ط§ظ†ظ‡â€Œظ‡ط§ ط®ظˆط´ ط§ظˆظ…ط¯غŒ!\n'
                'ط¯ظ†غŒط§غŒغŒ ع©ظ‡ ظ‚ظ‡ط±ظ…ط§ظ†â€Œظ‡ط§ط´ ط§ط² طھظ…ط§ظ… ط¯ظ†غŒط§ظ‡ط§غŒ ط®غŒط§ظ„غŒ ط¬ظ…ط¹ ط´ط¯ظ†...\n'
                'ًں“œ ط¨ط±ط§غŒ ط¯غŒط¯ظ† ط¯ط§ط³طھط§ظ† ط¨ط§ط²غŒ ط¨ظ†ظˆغŒط³غŒط¯: /story'
            )

            keyboard = [
                [InlineKeyboardButton("ًںژ´ ع©ط§ط±طھâ€Œظ‡ط§غŒ ظ…ظ†", callback_data="my_cards")],
                [InlineKeyboardButton("âڑ”ï¸ڈ ع†ط§ظ„ط´ PvP", callback_data="request_pvp_fight")],
                [InlineKeyboardButton("ًںژپ ع©ظ„غŒظ… ط±ظˆط²ط§ظ†ظ‡", callback_data="daily_claim")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(chat_id=chat.id, text=welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error in start_game_handler: {e}", exc_info=True)
            try:
                await query.message.reply_text("â‌Œ ط®ط·ط§ ط¯ط± ط§ط¬ط±ط§غŒ ط´ط±ظˆط¹ ط¨ط§ط²غŒ. ظ„ط·ظپط§ظ‹ ط¯ظˆط¨ط§ط±ظ‡ /start ط±ط§ طھط§غŒظ¾ ع©ظ†غŒط¯.")
            except Exception:
                pass

    async def cards_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ†ظ…ط§غŒط´ ع©ط§ط±طھâ€Œظ‡ط§غŒ ع©ط§ط±ط¨ط± ط§ط² ط·ط±غŒظ‚ ط¯ط³طھظˆط± ط¨ط§ pagination"""
        # ط¨ط±ط±ط³غŒ ظ…ط¬ظˆط² ط¯ط³طھظˆط±
        if not self._is_command_allowed_in_chat("cards", update.effective_chat.type):
            await update.message.reply_text(
                "ًںڑ« ط§غŒظ† ط¯ط³طھظˆط± ظپظ‚ط· ط¯ط± ع†طھ ط®طµظˆطµغŒ ظ‚ط§ط¨ظ„ ط§ط³طھظپط§ط¯ظ‡ ط§ط³طھ.\n"
                "ًںƒڈ ط¨ط±ط§غŒ ظ…ط´ط§ظ‡ط¯ظ‡ ع©ط§ط±طھâ€Œظ‡ط§غŒ ط®ظˆط¯طŒ ط§ط² ظ¾غŒظˆغŒ ط±ط¨ط§طھ ط§ط³طھظپط§ط¯ظ‡ ع©ظ†غŒط¯."
            )
            return
        
        user = update.effective_user
        
        # ط¨ط±ط±ط³غŒ ط¹ط¶ظˆغŒطھ ع©ط§ظ†ط§ظ„
        if False:
            await self.send_channel_join_message(update)
            return
        
        user_id = update.effective_user.id
        cards = self.db.get_player_cards(user_id)
        
        if not cards:
            text = "ًں”­ ظ‡ظ†ظˆط² ع©ط§ط±طھغŒ ظ†ط¯ط§ط±غŒط¯! ط¨ط±ط§غŒ ط´ط±ظˆط¹طŒ ط¨ط§ ط¯ط³طھظˆط± /claim ط§ظˆظ„غŒظ† ع©ط§ط±طھ ط®ظˆط¯ ط±ط§ ط±ط§غŒع¯ط§ظ† ط¯ط±غŒط§ظپطھ ع©ظ†غŒط¯."
            await update.message.reply_text(text)
        else:
            # ظ†ظ…ط§غŒط´ ظ…ظ†ظˆغŒ ط¯ط³طھظ‡â€Œط¨ظ†ط¯غŒ ط¨ط§ pagination
            keyboard = self._create_my_cards_keyboard(user_id, category="menu", page=1)
            text = f"ًںژ´ **ع©ط§ط±طھâ€Œظ‡ط§غŒ ط´ظ…ط§ ({len(cards)} ع©ط§ط±طھ)**\n\nظ„ط·ظپط§ظ‹ ط¯ط³طھظ‡ ظ…ظˆط±ط¯ ظ†ط¸ط± ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯:"
            reply_markup = keyboard
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def mycards_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ†ظ…ط§غŒط´ ع©ط§ط±طھâ€Œظ‡ط§ ط¨ط§ ط§ظ…ع©ط§ظ† ظ…ط¯غŒط±غŒطھ"""
        if not self._is_command_allowed_in_chat("mycards", update.effective_chat.type):
            await update.message.reply_text("ًںڑ« ط§غŒظ† ط¯ط³طھظˆط± ظپظ‚ط· ط¯ط± ع†طھ ط®طµظˆطµغŒ ظ‚ط§ط¨ظ„ ط§ط³طھظپط§ط¯ظ‡ ط§ط³طھ.")
            return
        
        user_id = update.effective_user.id
        keyboard = self._create_mycards_keyboard(user_id, category="menu", page=1)
        
        text = "ًں“‹ **ظ…ط¯غŒط±غŒطھ ع©ط§ط±طھâ€Œظ‡ط§غŒ ظ…ظ†**\n\nظ„ط·ظپط§ظ‹ ط¯ط³طھظ‡ ظ…ظˆط±ط¯ ظ†ط¸ط± ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯:"
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    
    def _create_mycards_keyboard(self, user_id: int, category: str = "menu", page: int = 1) -> InlineKeyboardMarkup:
        """ط§غŒط¬ط§ط¯ ع©غŒط¨ظˆط±ط¯ ظ…ط¯غŒط±غŒطھ ع©ط§ط±طھâ€Œظ‡ط§"""
        keyboard = []
        
        if category == "menu":
            # ظ…ظ†ظˆغŒ ط§طµظ„غŒ
            rarity_counts = self.db.get_rarity_counts(user_id)
            favorite_cards, fav_count = self.db.get_favorite_cards(user_id, page=1, per_page=1)
            
            if fav_count > 0:
                keyboard.append([
                    InlineKeyboardButton(
                        f"â­گ ظ…ظˆط±ط¯ ط¹ظ„ط§ظ‚ظ‡ ({fav_count})",
                        callback_data=f"mycards_favorite_1"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton(
                    f"ًںں، Legendary ({rarity_counts.get(CardRarity.LEGEND.value, 0)})",
                    callback_data=f"mycards_legend_1"
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    f"ًںں£ Epic ({rarity_counts.get(CardRarity.EPIC.value, 0)})",
                    callback_data=f"mycards_epic_1"
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    f"ًںں¢ Normal ({rarity_counts.get(CardRarity.NORMAL.value, 0)})",
                    callback_data=f"mycards_normal_1"
                )
            ])
            if rarity_counts.get(CardRarity.RARE.value, 0):
                keyboard.append([InlineKeyboardButton(
                    f"ًںŒں Rare ({rarity_counts[CardRarity.RARE.value]})", callback_data="mycards_rare_1"
                )])
            keyboard.append([InlineKeyboardButton("ًں”™ ظ…ظ†ظˆغŒ ط§طµظ„غŒ", callback_data="back_to_main")])
            
        else:
            # ظ†ظ…ط§غŒط´ ع©ط§ط±طھâ€Œظ‡ط§غŒ غŒع© ط¯ط³طھظ‡
            if category == "favorite":
                cards, total_count = self.db.get_favorite_cards(user_id, page=page, per_page=6)
            else:
                rarity_map = {
                    "legend": CardRarity.LEGEND,
                    "epic": CardRarity.EPIC,
                    "normal": CardRarity.NORMAL,
                    "rare": CardRarity.RARE,
                }
                rarity = rarity_map.get(category)
                cards, total_count = self.db.get_player_cards_by_rarity(user_id, rarity=rarity, page=page, per_page=6)
            
            rarity_colors = {
                CardRarity.NORMAL: "ًںں¢",
                CardRarity.EPIC: "ًںں£",
                CardRarity.LEGEND: "ًںں،"
            }
            
            for card in cards:
                color = rarity_colors.get(card.rarity, "âڑھ")
                stats = f"ًں’ھ{card.power} âڑ،{card.speed} ًں§ {card.iq} â‌¤ï¸ڈ{card.popularity}"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{color} {card.name} ({stats})",
                        callback_data=f"cardinfo_{card.card_id}"
                    )
                ])
            
            # ط¯ع©ظ…ظ‡â€Œظ‡ط§غŒ navigation
            total_pages = (total_count + 5) // 6
            nav_buttons = []
            
            if page > 1:
                nav_buttons.append(
                    InlineKeyboardButton("آ« ظ‚ط¨ظ„غŒ", callback_data=f"mycards_{category}_{page-1}")
                )
            
            nav_buttons.append(
                InlineKeyboardButton("ًںڈ  ظ…ظ†ظˆ", callback_data=f"mycards_menu_1")
            )
            
            if page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton("ط¨ط¹ط¯غŒ آ»", callback_data=f"mycards_{category}_{page+1}")
                )
            
            if nav_buttons:
                keyboard.append(nav_buttons)
        
        return InlineKeyboardMarkup(keyboard)

    def _create_my_cards_keyboard(self, user_id: int, category: str = "menu", page: int = 1) -> InlineKeyboardMarkup:
        """Compatibility wrapper for older handlers that still call the spaced name."""
        return self._create_mycards_keyboard(user_id, category=category, page=page)

    async def claim_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /claim with the same daily-card flow as the start-menu button."""
        user = update.effective_user

        if False:
            await self.send_channel_join_message(update)
            return

        user_id = user.id
        message = update.effective_message
        success, card, error, quick_ability = self.game.claim_daily_card_with_ability(user_id)

        if success and card is None and quick_ability and quick_ability.get("silver_ticket"):
            await update.effective_message.reply_text("ًںژں غŒع© Silver Ticket ظˆ ط§ط¨غŒظ„غŒطھغŒ آ«" + quick_ability["title"] + "آ» ط¯ط±غŒط§ظپطھ ط´ط¯.")
            return
        if success and card:
            rarity_colors = {
                CardRarity.NORMAL: "ًںں¢",
                CardRarity.EPIC: "ًںں£",
                CardRarity.LEGEND: "ًںں،",
                CardRarity.RARE: "ًں”µ",
            }
            color = rarity_colors.get(card.rarity, "âڑھ")
            claim_dialog = get_victory_dialog(card.name, card.dialogs)
            image_sent = await send_card_image_safely(
                message,
                card.name,
                self.config,
                f"ًںژ‰ {card.name}\n\nâ€œ{claim_dialog}â€‌",
            )

            text = (
                f"ًںژ‰ **ع©ط§ط±طھ ط±ظˆط²ط§ظ†ظ‡ ط¯ط±غŒط§ظپطھ ط´ط¯!**\n\n"
                f"{color} **{card.name}** ({card.rarity.value.title()})\n\n"
                f"ًں“ٹ **ط¢ظ…ط§ط± ع©ط§ط±طھ:**\n"
                f"ًں’ھ ظ‚ط¯ط±طھ: {card.power}\n"
                f"âڑ، ط³ط±ط¹طھ: {card.speed}\n"
                f"ًں§  ط¢غŒâ€Œع©غŒظˆ: {card.iq}\n"
                f"â‌¤ï¸ڈ ظ…ط­ط¨ظˆط¨غŒطھ: {card.popularity}\n"
                f"ًںژ¯ ظ…ط¬ظ…ظˆط¹: {card.get_total_stats()}\n\n"
                f"âœ¨ **ط§ط¨غŒظ„غŒطھغŒâ€Œظ‡ط§:**\n"
            )

            for ability in card.abilities:
                text += f"â€¢ {ability}\n"
            text += f"\nًںژپ Ability ظ…طµط±ظپغŒ Quick: {quick_ability['title']} أ—غ±"
            text += "\nًں•گ ع©ط§ط±طھ ط¨ط¹ط¯غŒ: ظ¾ط³ ط§ط² ظ†غŒظ…ظ‡â€Œط´ط¨"

            if not image_sent:
                text = f"ًںژ´ (طھطµظˆغŒط± ط¯ط± ط¯ط³طھط±ط³ ظ†غŒط³طھ)\n\n{text}"

            keyboard = [
                [InlineKeyboardButton("ًںژ´ ظ…ط´ط§ظ‡ط¯ظ‡ ع©ط§ط±طھâ€Œظ‡ط§", callback_data="my_cards")],
                [InlineKeyboardButton("ًں”™ ظ…ظ†ظˆغŒ ط§طµظ„غŒ", callback_data="back_to_main")]
            ]
            await message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown',
            )
        else:
            text = f"âڑ  **ط®ط·ط§ ط¯ط± ط¯ط±غŒط§ظپطھ ع©ط§ط±طھ**\n\n{error if error else 'ط®ط·ط§غŒ ظ†ط§ظ…ط´ط®طµ!'}"
            keyboard = [
                [InlineKeyboardButton("ًںژ´ ظ…ط´ط§ظ‡ط¯ظ‡ ع©ط§ط±طھâ€Œظ‡ط§", callback_data="my_cards")],
                [InlineKeyboardButton("ًں”™ ظ…ظ†ظˆغŒ ط§طµظ„غŒ", callback_data="back_to_main")]
            ]
            await message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown',
            )

    async def my_cards_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ†ظ…ط§غŒط´ ع©ط§ط±طھâ€Œظ‡ط§غŒ ع©ط§ط±ط¨ط± ط¨ط§ pagination"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        cards = self.db.get_player_cards(user_id)
        
        if not cards:
            text = (
                "ًں”­ **ظ‡ظ†ظˆط² ع©ط§ط±طھغŒ ظ†ط¯ط§ط±غŒط¯!**\n\n"
                "ط¨ط±ط§غŒ ط´ط±ظˆط¹طŒ ط§ظˆظ„غŒظ† ع©ط§ط±طھ ط®ظˆط¯ ط±ط§ ط±ط§غŒع¯ط§ظ† ط¯ط±غŒط§ظپطھ ع©ظ†غŒط¯."
            )
            keyboard = [
                [InlineKeyboardButton("ًںژپ ط¯ط±غŒط§ظپطھ ع©ط§ط±طھ ط§ظˆظ„", callback_data="daily_claim")],
                [InlineKeyboardButton("ًں”™ ظ…ظ†ظˆغŒ ط§طµظ„غŒ", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            # ظ†ظ…ط§غŒط´ ظ…ظ†ظˆغŒ ط¯ط³طھظ‡â€Œط¨ظ†ط¯غŒ
            keyboard = self._create_my_cards_keyboard(user_id, category="menu", page=1)
            text = f"ًںژ´ **ع©ط§ط±طھâ€Œظ‡ط§غŒ ط´ظ…ط§ ({len(cards)} ع©ط§ط±طھ)**\n\nظ„ط·ظپط§ظ‹ ط¯ط³طھظ‡ ظ…ظˆط±ط¯ ظ†ط¸ط± ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯:"
            reply_markup = keyboard
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    def _get_card_bio(self, name: str) -> str:
        bios = {
            "Heisenberg": "ط´غŒظ…غŒط¯ط§ظ† ظ†ط§ط¨ط؛ظ‡ ع©ظ‡ ط¨ظ‡ ظ…ط³غŒط± طھط§ط±غŒع© ظ‚ط¯ظ… ع¯ط°ط§ط´طھ.",
            "Spongebob": "ط§ط³ظپظ†ط¬ ظ¾ط±ط§ظ†ط±عکغŒ ط§ط² ط²غŒط± ط¢ط¨ ع©ظ‡ ظ‡ظ…غŒط´ظ‡ ط¢ظ…ط§ط¯ظ‡ ط§ط³طھ.",
            "Kangfupanda": "ظ¾ط§ظ†ط¯ط§غŒ ط±ط²ظ…غŒâ€Œع©ط§ط± ط¨ط§ ظ‚ظ„ط¨ ط¨ط²ط±ع¯.",
            "Homelander": "ظ‚ظ‡ط±ظ…ط§ظ† ظ‚ط¯ط±طھظ…ظ†ط¯ ط¨ط§ ع†ظ‡ط±ظ‡â€Œط§غŒ ظ¾غŒع†غŒط¯ظ‡.",
            "Thanos": "طھط§غŒطھط§ظ† ظ…ط¬ظ†ظˆظ† ط¯ط± ط¬ط³طھط¬ظˆغŒ طھط¹ط§ط¯ظ„ ع©ط§ط¦ظ†ط§طھ."
        }
        return bios.get(name, "ط¨غŒظˆع¯ط±ط§ظپغŒ ط¯ط± ط¯ط³طھط±ط³ ظ†غŒط³طھ.")

    def _get_card_stats_summary(self, user_id: int, card_id: str) -> Dict[str, Any]:
        import sqlite3
        wins = losses = ties = 0
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT result, COUNT(*) FROM fight_history WHERE user_id=? AND user_card_id=? GROUP BY result",
                (user_id, card_id)
            )
            for res, cnt in cursor.fetchall():
                if res == 'win':
                    wins = cnt
                elif res in ('lose', 'loss'):
                    losses += cnt
                elif res == 'tie':
                    ties = cnt
            conn.close()
        except Exception:
            pass
        total = wins + losses + ties
        wp = round((wins / total) * 100) if total else 0
        lp = round((losses / total) * 100) if total else 0
        tp = round((ties / total) * 100) if total else 0
        return {"wins": wins, "losses": losses, "ties": ties, "total": total, "wp": wp, "lp": lp, "tp": tp}

    async def card_view_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        card_id = query.data.removeprefix("card_view_")
        user_id = query.from_user.id
        card = self.db.get_card_by_id_for_player(card_id, user_id)
        if card and card.origin=="custom" and query.message.chat_id!=user_id:card.image_path=""
        if not card:
            await query.edit_message_text("â‌Œ ع©ط§ط±طھ غŒط§ظپطھ ظ†ط´ط¯!")
            return
        stats = self.db.get_player_card_stats(card_id, user_id)
        rarity_map = {
            CardRarity.NORMAL: "ًںں¢ Normal",
            CardRarity.RARE: "ًںŒں Rare",
            CardRarity.EPIC: "ًںں£ Epic",
            CardRarity.LEGEND: "ًںں، Legend"
        }
        header = f"{rarity_map.get(card.rarity, 'ًں”¶ Card')} â€” {escape(card.name)}"
        if card.origin == 'custom':
            header += ' آ· ط³ظپط§ط±ط´غŒ'
        text = (
            f"{header}\n"
            f"ًں’ھ {card.power} âڑ، {card.speed} ًں§  {card.iq} â‌¤ï¸ڈ {card.popularity}\n"
            f"ًں“ٹ ط¨ط§ط²غŒâ€Œظ‡ط§: {stats['games_played']}\n"
            f"ًںڈ† ط¨ط±ط¯: {stats['wins']} | â‌Œ ط¨ط§ط®طھ: {stats['losses']} | ًں¤‌ ظ…ط³ط§ظˆغŒ: {stats['ties']}\n"
            f"ًں“ˆ Win Rate: {int(stats['win_rate'])}%\n\n"
            f"ًں“‌ <b>Biography:</b>\n{escape(card.biography or '')}"
        )
        # ط§ط±ط³ط§ظ„ طھطµظˆغŒط±
        if card.origin == 'custom':
            if card.image_path and query.message.chat_id == user_id:
                with open(card.image_path, 'rb') as picture:
                    await query.message.reply_photo(photo=picture)
        else:
            await send_card_image_safely(query.message, card.name, self.config)
        keyboard = [
            [InlineKeyboardButton("ًں”™ ط¨ط§ط²ع¯ط´طھ", callback_data="my_cards")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    # AI fight handler removed - AI fights are no longer supported

    # ai_select_card_handler removed - AI fights are no longer supported

    # ai_show_abilities_handler removed - AI fights are no longer supported

    # ai_fight_handler and _show_ai_fight_result removed - AI fights are no longer supported

    async def leaderboard_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ†ظ…ط§غŒط´ ظ…ظ†ظˆغŒ ط§طµظ„غŒ ظ„غŒط¯ط±ط¨ظˆط±ط¯"""
        query = update.callback_query
        await query.answer()
        
        # طھط´ط®غŒطµ ظ†ظˆط¹ ع†طھ
        chat_type = query.message.chat.type if query.message else "private"
        is_group = chat_type in ["group", "supergroup"]
        
        if is_group:
            # ظ…ظ†ظˆغŒ ظ„غŒط¯ط±ط¨ظˆط±ط¯ ع¯ط±ظˆظ‡
            text = "ًںڈ† <b>Leaderboard ع¯ط±ظˆظ‡</b>\n\nط¨ط§ط²ظ‡ ط²ظ…ط§ظ†غŒ ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯:"
            keyboard = [
                [InlineKeyboardButton("ًں“ٹ ظ‡ظپطھع¯غŒ", callback_data="lb_group_weekly_10")],
                [InlineKeyboardButton("ًں“ٹ ظ…ط§ظ‡ط§ظ†ظ‡", callback_data="lb_group_monthly_10")],
                [InlineKeyboardButton("ًں“ٹ ع©ظ„ ط²ظ…ط§ظ†â€Œظ‡ط§", callback_data="lb_group_all_10")]
            ]
        else:
            # ظ…ظ†ظˆغŒ ظ„غŒط¯ط±ط¨ظˆط±ط¯ ط¬ظ‡ط§ظ†غŒ
            text = "ًںڈ† <b>Leaderboard ط¬ظ‡ط§ظ†غŒ</b>\n\nط¨ط§ط²ظ‡ ط²ظ…ط§ظ†غŒ ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯:"
            keyboard = [
                [InlineKeyboardButton("ًں“ٹ ظ‡ظپطھع¯غŒ", callback_data="lb_global_weekly_10")],
                [InlineKeyboardButton("ًں“ٹ ظ…ط§ظ‡ط§ظ†ظ‡", callback_data="lb_global_monthly_10")],
                [InlineKeyboardButton("ًں“ٹ ع©ظ„ ط²ظ…ط§ظ†â€Œظ‡ط§", callback_data="lb_global_all_10")],
                [InlineKeyboardButton("ًں”™ ظ…ظ†ظˆغŒ ط§طµظ„غŒ", callback_data="back_to_main")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def leaderboard_display_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ†ظ…ط§غŒط´ ظ„غŒط¯ط±ط¨ظˆط±ط¯ ط¨ط§ ظپغŒظ„طھط±"""
        query = update.callback_query
        await query.answer()
        
        # Parse callback_data: lb_{scope}_{timeframe}_{limit}
        parts = query.data.split("_")
        scope = parts[1]  # "global" or "group"
        timeframe = parts[2]  # "weekly", "monthly", "all"
        limit = int(parts[3]) if len(parts) > 3 else 10
        
        chat_id = query.message.chat.id if scope == "group" else None
        is_group = scope == "group"
        
        # ط§ع¯ظ‡ ع¯ط±ظˆظ‡ظ‡طŒ ط§ظˆظ„ ظ„غŒط³طھ ط§ط¹ط¶ط§غŒ ع¯ط±ظˆظ‡ ط±ظˆ ط¨ع¯غŒط±
        group_member_ids = set()
        if is_group:
            try:
                # ط¯ط±غŒط§ظپطھ ط§ط¹ط¶ط§غŒ ع¯ط±ظˆظ‡ ط§ط² Telegram API
                async for member in context.bot.get_chat_administrators(chat_id):
                    group_member_ids.add(member.user.id)
                
                # ط¯ط±غŒط§ظپطھ طھط¹ط¯ط§ط¯ ط§ط¹ط¶ط§غŒ ع¯ط±ظˆظ‡ (ظ…ط­ط¯ظˆط¯ ط¨ظ‡ 200 ظ†ظپط± ط§ظˆظ„)
                member_count = await context.bot.get_chat_member_count(chat_id)
                if member_count <= 200:  # ظپظ‚ط· ط¨ط±ط§غŒ ع¯ط±ظˆظ‡â€Œظ‡ط§غŒ ع©ظˆع†ع©
                    # ط§غŒظ† API ظ…ط­ط¯ظˆط¯ ظ‡ط³طھطŒ ظپظ‚ط· ط¨ط±ط§غŒ ع¯ط±ظˆظ‡â€Œظ‡ط§غŒ ع©ظˆع†ع© ع©ط§ط± ظ…غŒâ€Œع©ظ†ظ‡
                    try:
                        # ظ…طھط§ط³ظپط§ظ†ظ‡ Telegram API ط¨ط±ط§غŒ ط¯ط±غŒط§ظپطھ ظ‡ظ…ظ‡ ط§ط¹ط¶ط§ ظ…ط­ط¯ظˆط¯غŒطھ ط¯ط§ط±ظ‡
                        # ظ¾ط³ ظپظ‚ط· admin ظ‡ط§ ط±ظˆ ظ…غŒâ€Œع¯غŒط±غŒظ… ظˆ ط¨ظ‚غŒظ‡ ط±ظˆ ط§ط² ط¯غŒطھط§ط¨غŒط³
                        pass
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Could not get group members for chat {chat_id}: {e}")
        
        # ط¯ط±غŒط§ظپطھ ظ„غŒط¯ط±ط¨ظˆط±ط¯
        leaderboard = self.db.get_leaderboard_by_timeframe(
            timeframe=timeframe,
            limit=limit if not is_group else 1000,
            chat_id=None  # ظپط¹ظ„ط§ ظ‡ظ…ظ‡ ط±ظˆ ط¨ع¯غŒط±طŒ ط¨ط¹ط¯ط§ ظپغŒظ„طھط± ظ…غŒâ€Œع©ظ†غŒظ…
        )
        
        # ط§ع¯ظ‡ ع¯ط±ظˆظ‡ظ‡طŒ ظپظ‚ط· ط§ط¹ط¶ط§غŒ ع¯ط±ظˆظ‡ ع©ظ‡ ط¨ط§ط²غŒ ع©ط±ط¯ظ† ط±ظˆ ظ†ع¯ظ‡ ط¯ط§ط±
        if is_group:
            # ع†ظˆظ† ظ†ظ…غŒâ€Œطھظˆظ†غŒظ… ظ‡ظ…ظ‡ ط§ط¹ط¶ط§غŒ ع¯ط±ظˆظ‡ ط±ظˆ ط¨ع¯غŒط±غŒظ…طŒ ط§ط² ط±ظˆط´ ط¯غŒع¯ظ‡ ط§ط³طھظپط§ط¯ظ‡ ظ…غŒâ€Œع©ظ†غŒظ…:
            # ظپظ‚ط· ع©ط³ط§غŒغŒ ع©ظ‡ ط¯ط± ط§غŒظ† ع¯ط±ظˆظ‡ ظپط¹ط§ظ„غŒطھ ط¯ط§ط´طھظ† (fight ع©ط±ط¯ظ†) ط±ظˆ ظ†ط´ظˆظ† ظ…غŒط¯غŒظ…
            filtered_leaderboard = []
            
            # ط¯ط±غŒط§ظپطھ user_id ظ‡ط§غŒغŒ ع©ظ‡ ط¯ط± ط§غŒظ† ع¯ط±ظˆظ‡ fight ع©ط±ط¯ظ†
            group_fighters = self.db.get_group_fighters(chat_id)
            group_fighter_ids = {fighter['user_id'] for fighter in group_fighters}
            
            for player in leaderboard:
                if player['user_id'] in group_fighter_ids:
                    filtered_leaderboard.append(player)
            
            leaderboard = filtered_leaderboard
        
        # ط¹ظ†ظˆط§ظ†
        timeframe_names = {
            "daily": "ط±ظˆط²ط§ظ†ظ‡",
            "weekly": "ظ‡ظپطھع¯غŒ",
            "monthly": "ظ…ط§ظ‡ط§ظ†ظ‡",
            "all": "ع©ظ„ ط²ظ…ط§ظ†â€Œظ‡ط§"
        }
        scope_name = "ع¯ط±ظˆظ‡" if is_group else "ط¬ظ‡ط§ظ†غŒ"
        
        if not leaderboard:
            text = f"ًںڈ† <b>Leaderboard {scope_name} - {timeframe_names[timeframe]}</b>\n\nظ‡ظ†ظˆط² ع©ط³غŒ ط¨ط§ط²غŒ ظ†ع©ط±ط¯ظ‡!"
        else:
            text = f"ًںڈ† <b>Leaderboard {scope_name} - {timeframe_names[timeframe]}</b>\n\n"
            
            medals = ["ًں¥‡", "ًں¥ˆ", "ًں¥‰"]
            
            # ظ…ط­ط¯ظˆط¯ ع©ط±ط¯ظ† طھط¹ط¯ط§ط¯ ظ†ظ…ط§غŒط´ ط¨ط±ط§غŒ ط¬ظ„ظˆع¯غŒط±غŒ ط§ط² ظ…طھظ† ط·ظˆظ„ط§ظ†غŒ
            display_limit = min(limit, 30)  # ط­ط¯ط§ع©ط«ط± 30 ظ†ظپط± ظ†ط´ظˆظ† ط¨ط¯ظ‡
            
            for i, player_info in enumerate(leaderboard[:display_limit]):
                display_rank = player_info.get('rank', i + 1)
                if display_rank <= 3:
                    medal = medals[display_rank - 1]
                else:
                    medal = f"{display_rank}."
                
                # ظ†ط§ظ… ط¨ط§ط²غŒع©ظ† - escape ع©ط±ط¯ظ† ع©ط§ط±ط§ع©طھط±ظ‡ط§غŒ HTML
                first_name = player_info.get('first_name', '').strip()
                username = player_info.get('username', '').strip()
                
                if username:
                    # ط­ط°ظپ @ ط§ط² username ط§ع¯ط± ظˆط¬ظˆط¯ ط¯ط§ط´طھ
                    username = username.lstrip('@')
                    name = f"@{username[:15]}"
                elif first_name:
                    # escape ع©ط±ط¯ظ† ع©ط§ط±ط§ع©طھط±ظ‡ط§غŒ ط®ط§طµ HTML
                    name = first_name[:15].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                else:
                    name = "ط¨ط§ط²غŒع©ظ†"
                
                score = player_info.get('period_score', 0)
                
                # Level ظˆ Tier
                try:
                    prog = self.db.get_or_create_progression(player_info['user_id'])
                    from systems.progression_config import enabled
                    tier_badge = "" if enabled(self.db) else format_tier_badge(prog['current_tier'])
                    level = prog['level']
                    extra = f" {tier_badge}Lv{level}"
                except Exception:
                    extra = ""
                
                text += f"{medal} {name}{extra} â€” {score} ط§ظ…طھغŒط§ط²\n"
            
            # ط±طھط¨ظ‡ ع©ط§ط±ط¨ط± ط§ط² ظ„غŒط¯ط±ط¨ظˆط±ط¯ ظپغŒظ„طھط± ط´ط¯ظ‡
            user_id = query.from_user.id
            user_rank = None
            user_score = 0
            
            for i, player in enumerate(leaderboard):
                if player['user_id'] == user_id:
                    user_rank = i + 1
                    user_score = player['period_score']
                    break
            
            if user_rank:
                text += f"\nًں“چ ط±طھط¨ظ‡ ط´ظ…ط§: #{user_rank} ({user_score} ط§ظ…طھغŒط§ط²)"
        
        # ط¯ع©ظ…ظ‡â€Œظ‡ط§
        keyboard = []
        
        if not is_group:
            # ط¨ط±ط§غŒ ط¬ظ‡ط§ظ†غŒ: ط¯ع©ظ…ظ‡â€Œظ‡ط§غŒ طھط¹ط¯ط§ط¯ ظ†ظ…ط§غŒط´
            if limit == 10:
                keyboard.append([
                    InlineKeyboardButton("ًں¥ˆ Top 50", callback_data=f"lb_global_{timeframe}_50"),
                    InlineKeyboardButton("ًں¥‰ Top 100", callback_data=f"lb_global_{timeframe}_100")
                ])
            elif limit == 50:
                keyboard.append([
                    InlineKeyboardButton("ًں¥‡ Top 10", callback_data=f"lb_global_{timeframe}_10"),
                    InlineKeyboardButton("ًں¥‰ Top 100", callback_data=f"lb_global_{timeframe}_100")
                ])
            else:  # 100
                keyboard.append([
                    InlineKeyboardButton("ًں¥‡ Top 10", callback_data=f"lb_global_{timeframe}_10"),
                    InlineKeyboardButton("ًں¥ˆ Top 50", callback_data=f"lb_global_{timeframe}_50")
                ])
            
            # ط¯ع©ظ…ظ‡ ط¨ط§ط²ع¯ط´طھ ط¨ط±ط§غŒ private chat
            keyboard.append([InlineKeyboardButton("ًں”™ ط¨ط§ط²ع¯ط´طھ", callback_data="leaderboard")])
            keyboard.append([InlineKeyboardButton("ًں”™ ظ…ظ†ظˆغŒ ط§طµظ„غŒ", callback_data="back_to_main")])
        else:
            # ط¯ع©ظ…ظ‡ ط¨ط§ط²ع¯ط´طھ ط¨ط±ط§غŒ ع¯ط±ظˆظ‡
            keyboard.append([InlineKeyboardButton("ًں”™ ط¨ط§ط²ع¯ط´طھ", callback_data="leaderboard")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to edit leaderboard message: {e}")
            # ط§ع¯ط± edit ظ†ط´ط¯طŒ ظ¾غŒط§ظ… ط¬ط¯غŒط¯ ط¨ظپط±ط³طھ
            try:
                await query.message.reply_text(text=text, reply_markup=reply_markup, parse_mode='HTML')
            except Exception:
                pass

    async def match_info_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ†ظ…ط§غŒط´ ط§ط·ظ„ط§ط¹ط§طھ ع©ط§ظ…ظ„ ظ…ط¨ط§ط±ط²ظ‡ ظ¾ط³ ط§ط² ع©ظ„غŒع© ط±ظˆغŒ ط¯ع©ظ…ظ‡ 'â„¹ï¸ڈ ط§ط·ظ„ط§ط¹ط§طھ ط¨غŒط´طھط±'"""
        query = update.callback_query
        await query.answer()
        # Robust extraction of fight_id from callback_data
        data = (query.data or "")
        fight_id = None
        if data.startswith('match_info_'):
            fight_id = data[len('match_info_'):]

        if not fight_id:
            await query.answer("â‌Œ ط¯ط§ط¯ظ‡ ظ†ط§ظ…ط¹طھط¨ط±", show_alert=True)
            return

        result = self.recent_matches.get(str(fight_id))
        if not result:
            # Provide a clear inline alert and a fallback message in chat
            try:
                await query.answer("â„¹ï¸ڈ ط§ط·ظ„ط§ط¹ط§طھ ط§غŒظ† ظ…ط¨ط§ط±ط²ظ‡ ط¯ط± ط¯ط³طھط±ط³ ظ†غŒط³طھ غŒط§ ظ…ظ†ظ‚ط¶غŒ ط´ط¯ظ‡ ط§ط³طھ.", show_alert=True)
            except Exception:
                pass
            try:
                await context.bot.send_message(chat_id=query.message.chat_id, text="â„¹ï¸ڈ ط§ط·ظ„ط§ط¹ط§طھ ط§غŒظ† ظ…ط¨ط§ط±ط²ظ‡ ط¯ط± ط¯ط³طھط±ط³ ظ†غŒط³طھ غŒط§ ظ…ظ†ظ‚ط¶غŒ ط´ط¯ظ‡ ط§ط³طھ.")
            except Exception:
                logger.info(f"Could not send fallback match info missing message to chat {getattr(query.message, 'chat_id', 'unknown')}")
            return

        try:
            # The result dict comes from game_core.resolve_pvp_fight and contains 'challenger' and 'opponent'
            challenger = result.get('challenger', {})
            opponent = result.get('opponent', {})
            winner_ref = result.get('winner') or {}

            # Determine winner and loser records
            winner_user_id = winner_ref.get('user_id')
            if winner_user_id == challenger.get('user_id'):
                winner_data = challenger
                loser_data = opponent
            elif winner_user_id == opponent.get('user_id'):
                winner_data = opponent
                loser_data = challenger
            else:
                # Fallback: infer from result_type
                rt = result.get('result_type', '')
                if rt == 'challenger_wins':
                    winner_data = challenger
                    loser_data = opponent
                elif rt == 'opponent_wins':
                    winner_data = opponent
                    loser_data = challenger
                elif rt == 'tie':
                    # ط­ط§ظ„طھ ظ…ط³ط§ظˆغŒ - ظ‡غŒع† ط¨ط±ظ†ط¯ظ‡â€Œط§غŒ ظ†غŒط³طھ
                    await self.handle_tie_match_info(query, context, result, fight_id)
                    return
                else:
                    await context.bot.send_message(chat_id=query.message.chat_id, text="â„¹ï¸ڈ ط§ط·ظ„ط§ط¹ط§طھ ع©ط§ظ…ظ„ ط§غŒظ† ظ…ط¨ط§ط±ط²ظ‡ ط¯ط± ط¯ط³طھط±ط³ ظ†غŒط³طھ.")
                    return

            winner_card = winner_data.get('card')
            loser_card = loser_data.get('card')

            # ط¯ط±غŒط§ظپطھ ظ†ط§ظ…â€Œظ‡ط§ - ط§ظˆظ„ظˆغŒطھ ط¨ط§ username ط¨ط±ط§غŒ ط¬ظ„ظˆع¯غŒط±غŒ ط§ط² ظ…ط´ع©ظ„ encoding
            winner_username = "ط¨ط§ط²غŒع©ظ†"
            loser_username = "ط¨ط§ط²غŒع©ظ†"
            
            try:
                winner_chat = await context.bot.get_chat(winner_data.get('user_id'))
                # ط§ظˆظ„ظˆغŒطھ ط¨ط§ username ط¨ط±ط§غŒ ط¬ظ„ظˆع¯غŒط±غŒ ط§ط² ظ…ط´ع©ظ„ ظ†ط§ظ…â€Œظ‡ط§غŒ ظپط§ط±ط³غŒ
                if winner_chat.username:
                    winner_username = winner_chat.username
                elif winner_chat.first_name:
                    winner_username = winner_chat.first_name
            except Exception:
                # ط§ع¯ط± ظ†طھظˆط§ظ†ط³طھ ط§ط² API ط¨ع¯غŒط±ط¯طŒ ط§ط² ط¯غŒطھط§ط¨غŒط³ ط§ط³طھظپط§ط¯ظ‡ ع©ظ†
                winner_player = self.db.get_or_create_player(winner_data.get('user_id'))
                winner_username_raw = getattr(winner_player, 'username', '').strip()
                winner_first_name = getattr(winner_player, 'first_name', '').strip()
                
                if winner_username_raw:
                    winner_username = winner_username_raw
                elif winner_first_name and winner_first_name != 'ط¨ط§ط²غŒع©ظ†':
                    winner_username = winner_first_name
            
            try:
                loser_chat = await context.bot.get_chat(loser_data.get('user_id'))
                # ط§ظˆظ„ظˆغŒطھ ط¨ط§ username ط¨ط±ط§غŒ ط¬ظ„ظˆع¯غŒط±غŒ ط§ط² ظ…ط´ع©ظ„ ظ†ط§ظ…â€Œظ‡ط§غŒ ظپط§ط±ط³غŒ
                if loser_chat.username:
                    loser_username = loser_chat.username
                elif loser_chat.first_name:
                    loser_username = loser_chat.first_name
            except Exception:
                # ط§ع¯ط± ظ†طھظˆط§ظ†ط³طھ ط§ط² API ط¨ع¯غŒط±ط¯طŒ ط§ط² ط¯غŒطھط§ط¨غŒط³ ط§ط³طھظپط§ط¯ظ‡ ع©ظ†
                loser_player = self.db.get_or_create_player(loser_data.get('user_id'))
                loser_username_raw = getattr(loser_player, 'username', '').strip()
                loser_first_name = getattr(loser_player, 'first_name', '').strip()
                
                if loser_username_raw:
                    loser_username = loser_username_raw
                elif loser_first_name and loser_first_name != 'ط¨ط§ط²غŒع©ظ†':
                    loser_username = loser_first_name

            winner_stat = winner_data.get('stat_type') or winner_data.get('stat')
            loser_stat = loser_data.get('stat_type') or loser_data.get('stat')

            # Safely fetch numeric stat values
            v1 = getattr(winner_card, winner_stat, 0) if winner_card and winner_stat else 0
            v2 = getattr(winner_card, loser_stat, 0) if winner_card and loser_stat else 0
            sum_winner = v1 + v2

            v3 = getattr(loser_card, loser_stat, 0) if loser_card and loser_stat else 0
            v4 = getattr(loser_card, winner_stat, 0) if loser_card and winner_stat else 0
            sum_loser = v3 + v4

            text = (
                f"ًں‘‘ Winner: @{winner_username} آ«{getattr(winner_card, 'name', 'Unknown')}آ»\n"
                f"ًںڈ† Score gained: +{winner_data.get('score_gained', 0)} â€” آ«{getattr(winner_card, 'name', 'Unknown')}آ»\n\n"
                f"ًں’€ Loser: @{loser_username}\n"
                f"â‌¤ï¸ڈ Hearts lost: {loser_data.get('hearts_lost', 1)}\n"
                f"ًں“‰ @{loser_username} lost {abs(loser_data.get('score_gained', 0))} points\n\n"
                f"ًںژ¯ Choices:\n"
                f"â€¢ @{winner_username} â†’ {winner_stat or 'N/A'}\n"
                f"â€¢ @{loser_username} â†’ {loser_stat or 'N/A'}\n\n"
                f"ًں“ٹ Comparison:\n"
                f"{getattr(winner_card, 'name', 'Winner')} â†’ {winner_stat or 'stat'} {v1} + {loser_stat or 'stat'} {v2} = {sum_winner}\n"
                f"{getattr(loser_card, 'name', 'Loser')} â†’ {loser_stat or 'stat'} {v3} + {winner_stat or 'stat'} {v4} = {sum_loser}"
            )

            keyboard = [[InlineKeyboardButton("ًںڈ† Leaderboard", callback_data="leaderboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=text,
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in match_info_handler for fight {fight_id}: {e}", exc_info=True)
            await context.bot.send_message(chat_id=query.message.chat_id, text="â‌Œ غŒع© ط®ط·ط§غŒ ظ¾غŒط´â€Œط¨غŒظ†غŒ ظ†ط´ط¯ظ‡ ط±ط® ط¯ط§ط¯.")
    
    async def send_no_hearts_message(self, query, context, player):
        """ط§ط±ط³ط§ظ„ ظ¾غŒط§ظ… ط¹ط¯ظ… ظˆط¬ظˆط¯ ط¬ط§ظ† ط¨ظ‡ ع©ط§ط±ط¨ط±"""
        time_remaining = self.game.get_heart_reset_time_remaining(player)
        if time_remaining:
            time_str = self.game.format_time_remaining(time_remaining)
            full_message = f"ًں’€ ط¬ط§ظ† ط´ظ…ط§ طھظ…ط§ظ… ط´ط¯ظ‡!\n\nâڈ° طھط§ {time_str} ط¯غŒع¯ط± ظ†ظ…غŒâ€Œطھظˆط§ظ†غŒط¯ ط¨ط§ط²غŒ ع©ظ†غŒط¯.\n\nًں’‌ ظ‡ط± غ²غ´ ط³ط§ط¹طھ غŒع©ط¨ط§ط± غµ ط¬ط§ظ† ط´ط§ط±عک ظ…غŒâ€Œط´ظˆط¯."
            short_message = f"ًں’€ ط¬ط§ظ† طھظ…ط§ظ… ط´ط¯ظ‡! طھط§ {time_str} طµط¨ط± ع©ظ†غŒط¯."
        else:
            full_message = "ًں’€ ط¬ط§ظ† ط´ظ…ط§ طھظ…ط§ظ… ط´ط¯ظ‡! ظ„ط·ظپط§ظ‹ ع†ظ†ط¯ ظ„ط­ط¸ظ‡ طµط¨ط± ع©ظ†غŒط¯ طھط§ ط¬ط§ظ†â€Œظ‡ط§ ط±غŒط³طھ ط´ظˆظ†ط¯."
            short_message = "ًں’€ ط¬ط§ظ† طھظ…ط§ظ… ط´ط¯ظ‡!"
        
        # ظ†ظ…ط§غŒط´ popup ع©ظˆطھط§ظ‡
        await query.answer(short_message, show_alert=True)
        
        # ط§ط±ط³ط§ظ„ ظ¾غŒط§ظ… ع©ط§ظ…ظ„ ط¯ط± ظ¾غŒâ€ŒظˆغŒ
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=full_message
            )
        except Exception:
            pass  # ط§ع¯ط± ظ†طھظˆط§ظ†ط³طھ ظ¾غŒط§ظ… ظ¾غŒâ€ŒظˆغŒ ط¨ظپط±ط³طھط¯
    
    async def handle_tie_match_info(self, query, context, result, fight_id):
        """ظ†ظ…ط§غŒط´ ط§ط·ظ„ط§ط¹ط§طھ ع©ط§ظ…ظ„ ط¨ط±ط§غŒ ظ†طھط§غŒط¬ ظ…ط³ط§ظˆغŒ"""
        try:
            challenger = result.get('challenger', {})
            opponent = result.get('opponent', {})
            
            challenger_card = challenger.get('card')
            opponent_card = opponent.get('card')
            
            # ط¯ط±غŒط§ظپطھ ظ†ط§ظ…â€Œظ‡ط§
            challenger_username = "ط¨ط§ط²غŒع©ظ†"
            opponent_username = "ط¨ط§ط²غŒع©ظ†"
            
            try:
                challenger_chat = await context.bot.get_chat(challenger.get('user_id'))
                if challenger_chat.username:
                    challenger_username = challenger_chat.username
                elif challenger_chat.first_name:
                    challenger_username = challenger_chat.first_name
            except Exception:
                challenger_player = self.db.get_or_create_player(challenger.get('user_id'))
                challenger_username_raw = getattr(challenger_player, 'username', '').strip()
                challenger_first_name = getattr(challenger_player, 'first_name', '').strip()
                
                if challenger_username_raw:
                    challenger_username = challenger_username_raw
                elif challenger_first_name and challenger_first_name != 'ط¨ط§ط²غŒع©ظ†':
                    challenger_username = challenger_first_name
            
            try:
                opponent_chat = await context.bot.get_chat(opponent.get('user_id'))
                if opponent_chat.username:
                    opponent_username = opponent_chat.username
                elif opponent_chat.first_name:
                    opponent_username = opponent_chat.first_name
            except Exception:
                opponent_player = self.db.get_or_create_player(opponent.get('user_id'))
                opponent_username_raw = getattr(opponent_player, 'username', '').strip()
                opponent_first_name = getattr(opponent_player, 'first_name', '').strip()
                
                if opponent_username_raw:
                    opponent_username = opponent_username_raw
                elif opponent_first_name and opponent_first_name != 'ط¨ط§ط²غŒع©ظ†':
                    opponent_username = opponent_first_name
            
            challenger_stat = challenger.get('stat_type') or challenger.get('stat')
            opponent_stat = opponent.get('stat_type') or opponent.get('stat')
            
            # ظ…ط­ط§ط³ط¨ظ‡ ط§ظ…طھغŒط§ط²ط§طھ
            c1 = getattr(challenger_card, challenger_stat, 0) if challenger_card and challenger_stat else 0
            c2 = getattr(challenger_card, opponent_stat, 0) if challenger_card and opponent_stat else 0
            challenger_sum = c1 + c2
            
            o1 = getattr(opponent_card, opponent_stat, 0) if opponent_card and opponent_stat else 0
            o2 = getattr(opponent_card, challenger_stat, 0) if opponent_card and challenger_stat else 0
            opponent_sum = o1 + o2
            
            text = (
                f"ًں¤‌ **ظ…ط³ط§ظˆغŒ!**\n\n"
                f"ًں”¥ @{challenger_username} ًں†ڑ @{opponent_username}\n\n"
                f"ًںژ¯ ط§ظ†طھط®ط§ط¨â€Œظ‡ط§:\n"
                f"â€¢ @{challenger_username} â†’ {challenger_stat or 'N/A'}\n"
                f"â€¢ @{opponent_username} â†’ {opponent_stat or 'N/A'}\n\n"
                f"ًں“ٹ ظ…ظ‚ط§غŒط³ظ‡:\n"
                f"{getattr(challenger_card, 'name', 'ع©ط§ط±طھ')} â†’ {challenger_stat or 'stat'} {c1} + {opponent_stat or 'stat'} {c2} = {challenger_sum}\n"
                f"{getattr(opponent_card, 'name', 'ع©ط§ط±طھ')} â†’ {opponent_stat or 'stat'} {o1} + {challenger_stat or 'stat'} {o2} = {opponent_sum}\n\n"
                f"ًں¤‌ ظ†طھغŒط¬ظ‡: {challenger_sum} = {opponent_sum}\n"
                f"ًں’« ظ‡غŒع† غŒع© ط§ط² ط¨ط§ط²غŒع©ظ†ط§ظ† ط§ظ…طھغŒط§ط² غŒط§ ظ‚ظ„ط¨ ط§ط² ط¯ط³طھ ظ†ط¯ط§ط¯!"
            )
            
            keyboard = [
                [InlineKeyboardButton("ًں¥ٹ ع†ط§ظ„ط´ ط¬ط¯غŒط¯", callback_data="request_pvp_fight")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in handle_tie_match_info for fight {fight_id}: {e}", exc_info=True)
            await context.bot.send_message(chat_id=query.message.chat_id, text="â‌Œ ط®ط·ط§ ط¯ط± ظ†ظ…ط§غŒط´ ط§ط·ظ„ط§ط¹ط§طھ ظ…ط³ط§ظˆغŒ.")
    
    async def cooldown_card_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ†ظ…ط§غŒط´ ظ¾غŒط§ظ… cooldown ع©ط§ط±طھ"""
        query = update.callback_query
        await query.answer()
        
        # ط§ط³طھط®ط±ط§ط¬ card_id ط§ط² callback_data
        data = query.data
        if not data.startswith("cooldown_card_"):
            return
        
        card_id = data[len("cooldown_card_"):]
        user_id = query.from_user.id
        
        # ط¯ط±غŒط§ظپطھ ط§ط·ظ„ط§ط¹ط§طھ cooldown
        is_in_cooldown, cooldown_until = self.game.is_card_in_cooldown(user_id, card_id)
        
        if is_in_cooldown and cooldown_until:
            time_remaining = cooldown_until - datetime.now()
            if time_remaining.total_seconds() > 0:
                time_str = self.game.format_time_remaining(time_remaining)
                message = f"â‌„ï¸ڈ ط§غŒظ† ع©ط§ط±طھ ط¯ط± ط­ط§ظ„طھ Cooldown ط§ط³طھ!\n\nâڈ° طھط§ {time_str} ط¯غŒع¯ط± ظ†ظ…غŒâ€Œطھظˆط§ظ†غŒط¯ ط§ط² ط¢ظ† ط§ط³طھظپط§ط¯ظ‡ ع©ظ†غŒط¯.\n\nًں’، ع©ط§ط±طھâ€Œظ‡ط§غŒ Epic ظˆ Legend ظ¾ط³ ط§ط² 10 ط¨ط±ط¯ ظˆط§ط±ط¯ Cooldown ظ…غŒâ€Œط´ظˆظ†ط¯."
            else:
                message = "â‌„ï¸ڈ ط§غŒظ† ع©ط§ط±طھ ط¯ط± ط­ط§ظ„طھ Cooldown ط¨ظˆط¯ ط§ظ…ط§ ط§ع©ظ†ظˆظ† ط¢ط²ط§ط¯ ط´ط¯ظ‡ ط§ط³طھ. ظ„ط·ظپط§ظ‹ ط¯ظˆط¨ط§ط±ظ‡ طھظ„ط§ط´ ع©ظ†غŒط¯."
        else:
            message = "â‌„ï¸ڈ ط§غŒظ† ع©ط§ط±طھ ط¯ط± ط­ط§ظ„طھ Cooldown ظ†غŒط³طھ."
        
        # ط§ط±ط³ط§ظ„ ظ¾غŒط§ظ… ط¯ط± ظ¾غŒâ€ŒظˆغŒ
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message
            )
            await query.answer("ظ¾غŒط§ظ… ط¯ط± ظ¾غŒâ€ŒظˆغŒ ط§ط±ط³ط§ظ„ ط´ط¯.", show_alert=False)
        except Exception:
            await query.answer(message, show_alert=True)
    
    async def back_to_main_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ط¨ط§ط²ع¯ط´طھ ط¨ظ‡ ظ…ظ†ظˆغŒ ط§طµظ„غŒ"""
        query = update.callback_query
        await query.answer()
        
        # No expiration check needed for back_to_main as it should always work
        
        user = query.from_user
        user_id = user.id
        
        player = self.db.get_or_create_player(user_id)
        card_count = len(self.db.get_player_cards(user_id))
        prog = self.db.get_or_create_progression(user_id)
        from systems.progression_config import enabled
        tier_badge = "" if enabled(self.db) else format_tier_badge(prog['current_tier'])

        text = (
            f"ًںژ® **ظ…ظ†ظˆغŒ ط§طµظ„غŒ**\n\n"
            f"ط³ظ„ط§ظ… {user.first_name}! ًں‘‹\n\n"
            f"â­گ Level {prog['level']}  {tier_badge} {'' if enabled(self.db) else prog['current_tier']}\n"
            f"â‌¤ï¸ڈ ط¬ط§ظ†: {player.hearts}/{getattr(player, 'max_hearts', self.game.DAILY_HEARTS)}  "
            f"ًں’° ط³ع©ظ‡: {getattr(player, 'coins', 0):,}\n"
            f"ًںژ´ ع©ط§ط±طھâ€Œظ‡ط§: {card_count}  â€¢  ًںڈ† ط§ظ…طھغŒط§ط²: {player.total_score}\n\n"
            f"ط¹ظ…ظ„غŒط§طھ ظ…ظˆط±ط¯ ظ†ط¸ط± ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯:"
        )
        
        keyboard = [
            [InlineKeyboardButton("ًںژ´ ع©ط§ط±طھâ€Œظ‡ط§غŒ ظ…ظ†", callback_data="my_cards")],
            [InlineKeyboardButton("âڑ”ï¸ڈ ع†ط§ظ„ط´ PvP", callback_data="request_pvp_fight"),
             InlineKeyboardButton("ًںژ² Risk Mode", callback_data="risk_menu")],
            [InlineKeyboardButton("ًںژپ ع©ظ„غŒظ… ط±ظˆط²ط§ظ†ظ‡", callback_data="daily_claim"),
             InlineKeyboardButton("ًںژں Silver Claim", callback_data="v2_silver_claim") if __import__("systems.progression_config", fromlist=["enabled"]).enabled(self.db) else InlineKeyboardButton("â›ڈï¸ڈ ظ…ط§غŒظ†غŒظ†ع¯", callback_data="mining_claim")],
            [InlineKeyboardButton("ًں”® Fusion ع©ط§ط±طھâ€Œظ‡ط§", callback_data="fusion_menu"),
             InlineKeyboardButton("ًں›’ ط´ط§ظ¾", callback_data="shop_menu")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    # ==================== MYCARDS HANDLERS ====================
    
    async def mycards_navigation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ…ط¯غŒط±غŒطھ navigation ط¯ط± mycards"""
        query = update.callback_query
        await query.answer()
        
        # mycards_{category}_{page}
        payload = query.data.removeprefix("my_cards_nav_") if query.data.startswith("my_cards_nav_") else query.data.removeprefix("mycards_")
        try:
            category, raw_page = payload.rsplit("_", 1)
            page = max(1, int(raw_page))
            if category not in {"menu", "favorite", "normal", "epic", "legend", "rare"}:
                raise ValueError("invalid_category")
        except ValueError:
            await query.message.reply_text("â‌Œ ط¯ط³طھظ‡ ع©ط§ط±طھ ظ†ط§ظ…ط¹طھط¨ط± ط§ط³طھط› ط¯ظˆط¨ط§ط±ظ‡ ع©ط§ط±طھâ€Œظ‡ط§غŒ ظ…ظ† ط±ط§ ط¨ط§ط² ع©ظ†.")
            return
        user_id = query.from_user.id
        
        if category == "menu":
            text = "ًں“‹ **ظ…ط¯غŒط±غŒطھ ع©ط§ط±طھâ€Œظ‡ط§غŒ ظ…ظ†**\n\nظ„ط·ظپط§ظ‹ ط¯ط³طھظ‡ ظ…ظˆط±ط¯ ظ†ط¸ط± ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯:"
        else:
            category_names = {
                "favorite": "â­گ ظ…ظˆط±ط¯ ط¹ظ„ط§ظ‚ظ‡",
                "legend": "ًںں، Legendary",
                "epic": "ًںں£ Epic",
                "normal": "ًںں¢ Normal",
                "rare": "ًںŒں Rare",
            }
            category_name = category_names.get(category, category)
            
            if category == "favorite":
                cards, total_count = self.db.get_favorite_cards(user_id, page=page, per_page=6)
            else:
                rarity_map = {
                    "legend": CardRarity.LEGEND,
                    "epic": CardRarity.EPIC,
                    "normal": CardRarity.NORMAL,
                    "rare": CardRarity.RARE,
                }
                rarity = rarity_map.get(category)
                cards, total_count = self.db.get_player_cards_by_rarity(user_id, rarity=rarity, page=page, per_page=6)
            
            total_pages = max(1, (total_count + 5) // 6)
            page = min(page, total_pages)
            text = f"ًں“‹ **{category_name}** (طµظپط­ظ‡ {page}/{total_pages})\n\nط±ظˆغŒ ع©ط§ط±طھ ع©ظ„غŒع© ع©ظ†غŒط¯ طھط§ ط¬ط²ط¦غŒط§طھ ط¢ظ† ط±ط§ ط¨ط¨غŒظ†غŒط¯:"
            if not total_count:
                text = f"ًں“‹ **{category_name}**\n\nظ‡ظ†ظˆط² ع©ط§ط±طھغŒ ط¯ط± ط§غŒظ† ط¯ط³طھظ‡ ظ†ط¯ط§ط±غŒ."
        
        keyboard = self._create_mycards_keyboard(user_id, category=category, page=page)
        try:
            await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='Markdown')
        except telegram.error.BadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise
    
    async def cardinfo_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ظ†ظ…ط§غŒط´ ط§ط·ظ„ط§ط¹ط§طھ ع©ط§ط±طھ ط¨ط§ ط§ظ…ع©ط§ظ† favorite"""
        query = update.callback_query
        await query.answer()
        
        card_id = query.data.removeprefix("cardinfo_")
        await self._show_card_info(query, card_id)

    async def _show_card_info(self, query, card_id: str):
        """Render a card without re-parsing or mutating the triggering callback."""
        user_id = query.from_user.id
        
        # ط¨ط§ rarity_override ط¨ط§ط²غŒع©ظ†
        owned_card=self.db.get_card_by_id_for_player(card_id,user_id)
        card=owned_card or self.db.get_card_by_id(card_id)
        if card and card.origin=="custom" and not owned_card:card=None
        if card and card.origin=="custom" and query.message.chat_id!=user_id:card.image_path=""
        if not card:
            await query.answer("â‌Œ ع©ط§ط±طھ غŒط§ظپطھ ظ†ط´ط¯!", show_alert=True)
            return
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT is_favorite, usage_count FROM player_cards WHERE user_id = ? AND card_id = ?', (user_id, card_id))
        result = cursor.fetchone()
        conn.close()
        
        is_favorite = result[0] if result else 0
        usage_count = result[1] if result else 0
        
        rarity_colors = {
            CardRarity.NORMAL: "ًںں¢", CardRarity.EPIC: "ًںں£",
            CardRarity.LEGEND: "ًںں،", CardRarity.RARE: "ًںŒں"
        }
        color = rarity_colors.get(card.rarity, "âڑھ")
        
        # card_type ظ†ظ…ط§غŒط´
        type_labels = {
            "POWER_TYPE": "ًں’ھ ظ‚ط¯ط±طھ",
            "SPEED_TYPE": "âڑ، ط³ط±ط¹طھ",
            "IQ_TYPE": "ًں§  ظ‡ظˆط´",
            "POPULARITY_TYPE": "â‌¤ï¸ڈ ظ…ط­ط¨ظˆط¨غŒطھ"
        }
        type_label = type_labels.get(getattr(card, 'card_type', ''), "â‌“")
        
        # ط¨غŒظˆع¯ط±ط§ظپغŒ ع©ظˆطھط§ظ‡
        bio = getattr(card, 'biography', '') or ''
        bio_text = f"\nًں“– <i>{escape(bio[:80])}{'...' if len(bio) > 80 else ''}</i>\n" if bio else ""
        if card.origin == 'custom':
            bio_text = '\nًںڈ· ط³ظپط§ط±ط´غŒ\n' + bio_text
        
        text = (
            f"{color} <b>{escape(card.name)}</b> ({card.rarity.value.title()})\n"
            f"ًںڈ·ï¸ڈ طھط§غŒظ¾: {type_label}\n"
            f"{bio_text}\n"
            f"ًں’ھ ظ‚ط¯ط±طھ: {card.power}  âڑ، ط³ط±ط¹طھ: {card.speed}\n"
            f"ًں§  ظ‡ظˆط´: {card.iq}  â‌¤ï¸ڈ ظ…ط­ط¨ظˆط¨غŒطھ: {card.popularity}\n"
            f"ًں“ٹ ظ…ط¬ظ…ظˆط¹: {card.get_total_stats()}\n\n"
            f"ًںژ® ط§ط³طھظپط§ط¯ظ‡: {usage_count} ط¨ط§ط±"
            f"{'  â­گ' if is_favorite else ''}"
        )
        
        fav_text = "ًں’” ط­ط°ظپ ط§ط² ط¹ظ„ط§ظ‚ظ‡â€Œظ…ظ†ط¯غŒâ€Œظ‡ط§" if is_favorite else "â­گ ط§ظپط²ظˆط¯ظ† ط¨ظ‡ ط¹ظ„ط§ظ‚ظ‡â€Œظ…ظ†ط¯غŒâ€Œظ‡ط§"
        
        keyboard = [
            [InlineKeyboardButton(fav_text, callback_data=f"toggle_fav_{card_id}")],
        ]
        
        # ط§ع¯ظ‡ ع©ط§ط±طھ Epic ظ‡ط³طھطŒ ظ…ط§ظ…ظˆط±غŒطھ ط±ظˆ ظ†ط´ظˆظ† ط¨ط¯ظ‡
        if card.rarity == CardRarity.EPIC:
            from systems.progression_config import enabled
            mission_progress = None if enabled(self.db) else self.missions.get_player_mission_progress(user_id, card_id)
            if mission_progress:
                prog = mission_progress['current_progress']
                tgt = mission_progress['target']
                pct = mission_progress['progress_percent']
                mission_line = f"\n\nًںژ¯ <b>ظ…ط§ظ…ظˆط±غŒطھ:</b> {escape(mission_progress['description'])}\nًں“ˆ ظ¾غŒط´ط±ظپطھ: {prog}/{tgt} ({pct}%)"
                text += mission_line
                
                if mission_progress['completed'] and not mission_progress.get('reward_claimed'):
                    keyboard.append([InlineKeyboardButton(
                        "ًںڈ† ط¯ط±غŒط§ظپطھ ظ¾ط§ط¯ط§ط´ Legend!", callback_data=f"mission_claim_{card_id}"
                    )])
        
        # ط¯ع©ظ…ظ‡ ط§ط³ع©غŒظ†
        all_skins = self.skins.get_card_skins(card_id) if card.origin == 'official' else []
        if all_skins:
            keyboard.append([InlineKeyboardButton("ًںژ¨ ط§ط³ع©غŒظ†â€Œظ‡ط§", callback_data=f"skins_menu_{card_id}")])
        
        keyboard.append([InlineKeyboardButton("ًں”™ ط¨ط§ط²ع¯ط´طھ", callback_data="mycards_menu_1")])
        
        try:
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        except telegram.error.BadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise
    
    async def toggle_favorite_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """طھط؛غŒغŒط± ظˆط¶ط¹غŒطھ favorite ع©ط§ط±طھ"""
        query = update.callback_query
        
        card_id = query.data.removeprefix("toggle_fav_")
        user_id = query.from_user.id
        
        success = self.db.toggle_favorite_card(user_id, card_id)
        
        if success:
            await query.answer("âœ… ظˆط¶ط¹غŒطھ ع©ط§ط±طھ طھط؛غŒغŒط± ع©ط±ط¯!", show_alert=False)
            # ط¨ط±ظˆط²ط±ط³ط§ظ†غŒ ظ¾غŒط§ظ…
            await self._show_card_info(query, card_id)
        else:
            await query.answer("â‌Œ ط®ط·ط§ ط¯ط± طھط؛غŒغŒط± ظˆط¶ط¹غŒطھ!", show_alert=True)

    # ==================== 3-ROUND BATTLE SYSTEM ====================

