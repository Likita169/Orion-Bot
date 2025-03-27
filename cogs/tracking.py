import discord
from discord.ext import commands
import json
from datetime import datetime

class Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.activity_data = self.load_data()

    def load_data(self):
        try:
            with open("activity_data.json", "r") as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_data(self):
        with open("activity_data.json", "w") as file:
            json.dump(self.activity_data, file, indent=4)

    async def check_and_assign_role(self, member):
        guild = member.guild
        user_id = str(member.id)
        days_active = self.activity_data[user_id]["days_active"]

        with open("config.json", "r") as file:
            config = json.load(file)

        for days_required, role_id in config["ROLE_THRESHOLDS"].items():
            if days_active >= int(days_required):  
                role = guild.get_role(int(role_id))
                if role and role not in member.roles:
                    await member.add_roles(role)
                    await member.send(f"🎉 Chúc mừng! Bạn đã đạt {days_active} ngày hoạt động và nhận role **{role.name}**!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = str(message.author.id)
        today = datetime.now().strftime("%Y-%m-%d")

        if user_id not in self.activity_data:
            self.activity_data[user_id] = {"days_active": 1, "last_active_date": today}
        else:
            last_active = self.activity_data[user_id]["last_active_date"]
            if last_active != today:
                self.activity_data[user_id]["days_active"] += 1
                self.activity_data[user_id]["last_active_date"] = today
                
                await self.check_and_assign_role(message.author)

        self.save_data()

async def setup(bot):
    await bot.add_cog(Tracking(bot))
