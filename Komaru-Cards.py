# ---------------------------------------------------------------------------------
# Name: AutoKomaruCards
# meta developer: @Timur2287g_orig
# Commands:
# .kfarm, .kstats, .kview, .kreset
# ---------------------------------------------------------------------------------

import asyncio
import random
import time
import re
from .. import loader, utils

__version__ = (3, 1, 1)

@loader.tds
class AutoKomaruCardsModule(loader.Module):
    """Автоматический фарм карточек и костей в Komaru Cards."""

    strings = {"name": "AutoKomaruCards"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.running = False
        self.last_run_komaru = 0
        self.last_run_diceplay = 0
        self.processed_messages = set()

        self.cards_stats = {
            "total": self.db.get(self.strings["name"], "cards_count", 0),
            "common": self.db.get(self.strings["name"], "common_count", 0),
            "rare": self.db.get(self.strings["name"], "rare_count", 0),
            "mythical": self.db.get(self.strings["name"], "mythical_count", 0),
            "legendary": self.db.get(self.strings["name"], "legendary_count", 0),
            "coins": self.db.get(self.strings["name"], "coins_count", 0),
        }

        self.db.set(self.strings["name"], "profile_checked", False)
        self.db.set(self.strings["name"], "premium_active", None)
        self.db.set(self.strings["name"], "enabled", False)

        await self.check_premium_status()

        if self.db.get(self.strings["name"], "enabled", False):
            self.running = True
            await self.farming_loop()

    async def check_premium_status(self):
        msg = await self.client.send_message(7409912773, "/profile")
        await asyncio.sleep(3)
        a1 = await self.client.get_messages(7409912773, limit=1)
        cleaned_message = re.sub(r'[\u2068\u2069]', '', a1[0].raw_text)

        if "У вас активен Komaru Premium" in cleaned_message:
            self.var_x = True
        else:
            self.var_x = False

        await self.client.delete_messages(7409912773, [msg.id, a1[0].id])
        self.db.set(self.strings["name"], "premium_active", self.var_x)
        self.db.set(self.strings["name"], "profile_checked", True)
        
    async def farming_loop(self):
      while self.running:
        current_time = time.time()

        if current_time - self.last_run_komaru >= 14400: 
            await self.client.send_message(7409912773, "/komaru")
            self.last_run_komaru = current_time
            await asyncio.sleep(3)

            last_messages = await self.client.get_messages(7409912773, limit=1)
            if last_messages:
                message = last_messages[0].raw_text
                cooldown = self.extract_cooldown_time(message)
                await asyncio.sleep(cooldown)

        elapsed_time_diceplay = current_time - self.last_run_diceplay
        if elapsed_time_diceplay >= 360:
            await self.client.send_message(7409912773, "/diceplay")
            self.last_run_diceplay = current_time
            await asyncio.sleep(3)
            await self.update_coin_stats()

        cooldown_time = 360 if self.var_x else 480
        await asyncio.sleep(cooldown_time)
        
    def extract_cooldown_time(self, message):
        """Извлекает время кулдауна из сообщения и возвращает его в секундах."""
        
        match = re.search(r'(?:(\d+)\s*(?:ч(?:ас(?:ов)?)?)?\s*)?(?:(\d+)\s*(?:мин(?:ут(?:ы)?)?)?\s*)?(?:(\d+)\s*(?:сек(?:ун(?:ды)?)?)?)?', message)
        
        hours = minutes = seconds = 0  
        
        if match:
            if match.group(1):
                hours = int(match.group(1))
            
            if match.group(2):
                minutes = int(match.group(2))
            
            if match.group(3):
                seconds = int(match.group(3))
        
        return hours * 3600 + minutes * 60 + seconds

    async def update_coin_stats(self):
        """Обновляет статистику монет после выполнения команды /diceplay."""
        last_messages = await self.client.get_messages(7409912773, limit=1)

        if last_messages:
            message = last_messages[0].raw_text.lower()
            cleaned_message = re.sub(r'[\u2068\u2069]', '', message)

            if "выигрыш" in cleaned_message and "💰 монеты" in cleaned_message:
                coin_amount_match = re.search(r'💰 монеты • (\d+)', cleaned_message)
                if coin_amount_match:
                    coins = int(coin_amount_match.group(1))
                    self.cards_stats["coins"] += coins
                    self.db.set(self.strings["name"], "coins_count", self.cards_stats['coins'])
                    
    async def process_messages(self, message):
        all_messages = []
        limit = 100
        offset_id = 0

        while True:
            batch = await self.client.get_messages(7409912773, limit=limit, offset_id=offset_id)
            if not batch:
                break
            all_messages.extend(batch)
            offset_id = batch[-1].id

        for m2 in all_messages:
            if m2.sender_id == 7409912773:
                raw_text = m2.raw_text.lower()
                cleaned_text = re.sub(r'[\u2068\u2069]', '', raw_text)

                rarities = {
                    "редкость • обычная": "common",
                    "редкость • редкая": "rare",
                    "редкость • мифическая": "mythical",
                    "редкость • легендарная": "legendary",
                    "rarity • common": "common",
                    "rarity • rare": "rare",
                    "rarity • mythical": "mythical",
                    "rarity • legendary": "legendary"
                }

                for rarity_text, rarity in rarities.items():
                    if rarity_text in cleaned_text:
                        self.cards_stats[rarity] += 1
                        self.cards_stats['total'] += 1
                        break

                if "💰 монеты" in cleaned_text and "выигрыш" in cleaned_text:
                    coin_amount_match = re.search(r'💰 монеты • (\d+)', cleaned_text)
                    if coin_amount_match:
                        coins = int(coin_amount_match.group(1))
                        self.cards_stats["coins"] += coins

        self.db.set(self.strings["name"], "cards_count", self.cards_stats['total'])
        self.db.set(self.strings["name"], "common_count", self.cards_stats['common'])
        self.db.set(self.strings["name"], "rare_count", self.cards_stats['rare'])
        self.db.set(self.strings["name"], "mythical_count", self.cards_stats['mythical'])
        self.db.set(self.strings["name"], "legendary_count", self.cards_stats['legendary'])
        self.db.set(self.strings["name"], "coins_count", self.cards_stats['coins'])
                    
    @loader.command()
    async def kfarm(self, message):
        """Включает/выключает фарминг."""
        
        if not self.db.get(self.strings["name"], "profile_checked", False):
            await message.edit("<emoji document_id=5465665476971471368>❌</emoji> Сначала выполните проверку премиума.")
            await self.check_premium_status()
            return

        self.running = not self.running
        self.db.set(self.strings["name"], "enabled", self.running)

        if self.running:
            await message.edit("<emoji document_id=5427009714745517609>✅</emoji> Фарминг начался, цикл запущен.")
            await self.farming_loop()
        else:
            await message.edit("<emoji document_id=5465665476971471368>❌</emoji> Фарминг остановлен.")
            self.last_run_komaru = 0  
            self.last_run_diceplay = 0

    @loader.command()
    async def kstats(self, message):
        """Показывает статистику, нафармленную модулем в лс бота."""
        
        stats_message = (
            f"<blockquote> <emoji document_id=5431577498364158238>📊</emoji> Статистика: {self.cards_stats['total']}\n\n"
            f"<emoji document_id=5433713454319938373>🩶</emoji> <b>Обычных:</b> {self.cards_stats['common']}\n"
            f"<emoji document_id=5449380056201697322>💚</emoji> <b>Редких:</b> {self.cards_stats['rare']}\n"
            f"<emoji document_id=5449505950283078474>❤️</emoji> <b>Мифических:</b> {self.cards_stats['mythical']}\n"
            f"<emoji document_id=5449366943666543715>💛</emoji> <b>Легендарных:</b> {self.cards_stats['legendary']}\n\n"
            f"<emoji document_id=5375296873982604963>💰</emoji> Монет:</b> {self.cards_stats['coins']}\n </blockquote>"
        )
        await message.edit(stats_message, parse_mode="HTML")

    @loader.command()
    async def kview(self, message):
        """Проверяет всю переписку с ботом на полученные карточки и обновляет статистику"""
        start_time = time.time()

        await message.edit("<emoji document_id=5228686859663585439>👁‍🗨</emoji> Начинаю проверку всех карточек...")

        await self.process_messages(message)

        end_time = time.time()
        elapsed_time = round(end_time - start_time, 2)

        await message.edit(f"<emoji document_id=5228686859663585439>📊</emoji> Статистика обновлена.\nОбновление заняло {elapsed_time} секунд.")

    @loader.command()
    async def kreset(self, message):
        """Сбрасывает статистику"""
        self.cards_stats = {key: 0 for key in self.cards_stats}
        self.db.set(self.strings["name"], "cards_count", self.cards_stats['total'])
        self.db.set(self.strings["name"], "common_count", self.cards_stats['common'])
        self.db.set(self.strings["name"], "rare_count", self.cards_stats['rare'])
        self.db.set(self.strings["name"], "mythical_count", self.cards_stats['mythical'])
        self.db.set(self.strings["name"], "legendary_count", self.cards_stats['legendary'])
        self.db.set(self.strings["name"], "coins_count", self.cards_stats['coins'])
        await message.edit("<emoji document_id=5427009714745517609>✅</emoji> Статистика сброшена.")
