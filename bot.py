import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timedelta, timezone
import asyncio
import aiofiles

# Đọc cấu hình từ file config.json
try:
    with open("config.json", "r") as file:
        config = json.load(file)
    TOKEN = config["TOKEN"]
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    print("❌ Lỗi: Không thể đọc config.json hoặc thiếu thông tin!")
    exit()

# Lưu trữ dữ liệu
activity_data = {}
role_thresholds = {}
streak_data = {}
notification_channels = {}  # {guild_id: channel_id}

# Khởi tạo bot với intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cơ chế lưu dữ liệu an toàn với temp file
def save_data(force=False):
    if not force and not getattr(save_data, "dirty", False):
        return

    temp_files = {
        "activity": "temp_activity.json",
        "role": "temp_role.json",
        "streak": "temp_streak.json",
        "notify": "temp_notify.json"
    }

    try:
        # Ghi vào temp file trước
        with open(temp_files["activity"], "w") as f:
            json.dump(activity_data, f, indent=4)
        with open(temp_files["role"], "w") as f:
            json.dump(role_thresholds, f, indent=4)
        with open(temp_files["streak"], "w") as f:
            json.dump(streak_data, f, indent=4)
        with open(temp_files["notify"], "w") as f:
            json.dump(notification_channels, f, indent=4)
        
        # Thay thế file chính thức
        os.replace(temp_files["activity"], "activity_data.json")
        os.replace(temp_files["role"], "role_thresholds.json")
        os.replace(temp_files["streak"], "streak_data.json")
        os.replace(temp_files["notify"], "notification_channels.json")
        
        save_data.dirty = False
    except Exception as e:
        print(f"❌ Lỗi khi lưu dữ liệu: {e}")
        # Xóa temp file nếu có lỗi
        for temp in temp_files.values():
            try:
                os.remove(temp)
            except:
                pass

save_data.dirty = False

# Tải dữ liệu từ file JSON
def load_data():
    global activity_data, role_thresholds, streak_data, notification_channels
    try:
        with open("activity_data.json", "r") as file:
            activity_data = json.load(file)
    except Exception as e:
        print(f"⚠️ Lỗi load activity_data.json: {e}")
        activity_data = {}

    try:
        with open("role_thresholds.json", "r") as file:
            role_thresholds = json.load(file)
    except Exception as e:
        print(f"⚠️ Lỗi load role_thresholds.json: {e}")
        role_thresholds = {}

    try:
        with open("streak_data.json", "r") as file:
            streak_data = json.load(file)
    except Exception as e:
        print(f"⚠️ Lỗi load streak_data.json: {e}")
        streak_data = {}
    
    try:
        with open("notification_channels.json", "r") as file:
            notification_channels = json.load(file)
    except Exception as e:
        print(f"⚠️ Lỗi load notification_channels.json: {e}")
        notification_channels = {}

# Task lưu dữ liệu định kỳ 5 phút
@tasks.loop(minutes=5)
async def periodic_save():
    save_data()

# Chờ đến 0h UTC
async def wait_until_midnight():
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    midnight = datetime(
        year=tomorrow.year,
        month=tomorrow.month,
        day=tomorrow.day,
        hour=0,
        minute=0,
        second=0,
        tzinfo=timezone.utc
    )
    await asyncio.sleep((midnight - now).total_seconds())

# Khi bot khởi động
@bot.event
async def on_ready():
    load_data()
    if not hasattr(bot, "synced"):
        await bot.tree.sync()
        bot.synced = True
    print(f"✅ Bot {bot.user} đã sẵn sàng!")
    await bot.wait_until_ready()
    
    if not reset_streaks.is_running():
        reset_streaks.start()
    if not periodic_save.is_running():
        periodic_save.start()

# Theo dõi hoạt động voice & chat
async def track_activity(member):
    user_id = str(member.id)
    today = datetime.now(timezone.utc).date().isoformat()

    if user_id not in activity_data:
        activity_data[user_id] = {"days_active": 0, "last_active_date": None}
    if user_id not in streak_data:
        streak_data[user_id] = {"streak": 0, "last_active_date": None}

    updated = False
    if activity_data[user_id]["last_active_date"] != today:
        activity_data[user_id]["days_active"] += 1
        activity_data[user_id]["last_active_date"] = today
        updated = True

    if streak_data[user_id]["last_active_date"] != today:
        streak_data[user_id]["streak"] += 1
        streak_data[user_id]["last_active_date"] = today
        updated = True

        # Gửi thông báo
        
        channel_id = notification_channels.get(str(guild.id))
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel and channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(f"🚀 {member.mention} đang trên đà **{streak_data[user_id]['streak']} ngày liên tiếp**! 🔥 Hãy giữ vững phong độ nhé!")
                except Exception as e:
                    print("❌ Lỗi khi gửi thông báo:", e)
        else:
            try:
                await channel.send(f"🔥 {interaction.user.mention} đã duy trì streak {streak_data[user_id]['streak']} ngày liên tiếp!")
            except discord.Forbidden:
                print(f"❌ Không thể gửi tin nhắn đến {channel.name} (Guild: {guild.name})")
            except Exception as e:
                print(f"⚠️ Lỗi không xác định khi gửi tin nhắn: {e}")

    if updated:
        save_data.dirty = True
        await check_and_assign_role(member)

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and not before.channel:
        await track_activity(member)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await track_activity(message.author)
    await bot.process_commands(message)

# Kiểm tra và cấp role
async def check_and_assign_role(member):
    guild = member.guild
    if not guild:
        return

    user_id = str(member.id)
    days_active = activity_data.get(user_id, {}).get("days_active", 0)

    sorted_roles = sorted(
        role_thresholds.items(),
        key=lambda x: int(x[0]) if x[0].isdigit() else 0,
        reverse=True
    )

    for days_required_str, role_id in sorted_roles:
        if not days_required_str.isdigit() or not role_id.isdigit():
            continue
        days_required = int(days_required_str)
        if days_active >= days_required:
            role = guild.get_role(int(role_id))
            if role and role not in member.roles:
                await member.add_roles(role)
                try:
                    await member.send(f"🎉 Bạn đã nhận role **{role.name}** vì đạt {days_required} ngày hoạt động!")
                except discord.Forbidden:
                    pass
            break

@bot.tree.command(name="addrole", description="Thêm role được cấp theo số ngày hoạt động (Chỉ Admin)")
async def add_role(interaction: discord.Interaction, days: int, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Bạn không có quyền dùng lệnh này!", ephemeral=True)
        return
    
    # Lưu role vào cấu hình
    role_thresholds[str(days)] = str(role.id)
    save_data.dirty = True  # Đánh dấu cần lưu
    
    await interaction.response.send_message(
        f"✅ Đã thiết lập role **{role.name}** cho mốc **{days} ngày** hoạt động!",
        ephemeral=True
    )

@bot.tree.command(name="listroles", description="Xem các role được cấp theo số ngày hoạt động")
async def list_roles(interaction: discord.Interaction):
    if not role_thresholds:
        await interaction.response.send_message("❌ Hiện chưa có role nào được thiết lập!", ephemeral=True)
        return

    msg = "**📌 Danh sách role theo ngày hoạt động:**\n"
    for days, role_id in role_thresholds.items():
        role = interaction.guild.get_role(int(role_id))
        if role:
            msg += f"🔹 **{role.name}** - {days} ngày\n"

    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="delrole", description="Xóa role ra khỏi danh sách cấp role (Chỉ Admin)")
async def delete_role(interaction: discord.Interaction, days: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Bạn không có quyền dùng lệnh này!", ephemeral=True)
        return

    if str(days) in role_thresholds:
        del role_thresholds[str(days)]
        save_data()
        await interaction.response.send_message(f"✅ Role cho **{days} ngày** đã bị xóa!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Không tìm thấy role cho số ngày này!", ephemeral=True)

# Lệnh xem streak
@bot.tree.command(name="streak", description="Xem streak cá nhân hoặc của người khác")
async def streak(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    user_id = str(member.id)
    streak_count = streak_data.get(user_id, {}).get("streak", 0)

    message = f"🔥 Bạn đã hoạt động liên tiếp **{streak_count} ngày**!" if member == interaction.user else f"🔥 **{member.name}** đã hoạt động liên tiếp **{streak_count} ngày**!"
    await interaction.response.send_message(message, ephemeral=True)

# Lệnh set kênh thông báo
@bot.tree.command(name="setchannel", description="Thiết lập kênh thông báo của bot")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ Bạn không có quyền quản lý kênh.", ephemeral=True)
        return

    if not channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.response.send_message(f"❌ Bot không có quyền gửi tin nhắn trong {channel.mention}.", ephemeral=True)
        return

    notification_channels[str(interaction.guild.id)] = str(channel.id)
    save_data.dirty = True
    await interaction.response.send_message(f"✅ Đã thiết lập kênh thông báo: {channel.mention}", ephemeral=True)

@bot.tree.command(name="reset", description="Reset toàn bộ dữ liệu hoạt động")
async def reset(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Bạn không có quyền dùng lệnh này!", ephemeral=True)
        return
    
    global activity_data
    activity_data = {}
    save_data()
    await interaction.response.send_message("🔄 **Dữ liệu hoạt động đã được reset!**", ephemeral=True)

# Task reset streak hàng ngày
@tasks.loop(hours=24)
async def reset_streaks():
    await wait_until_midnight()
    today = datetime.now(timezone.utc).date().isoformat()

    for user_id in list(streak_data.keys()):
        user_data = streak_data[user_id]
        if user_data.get("last_active_date") != today:
            user_data["streak"] = 0
            user_data["last_active_date"] = today  # Cập nhật ngày cuối

    save_data.dirty = True
    save_data(force=True)

# Chạy bot
bot.run(TOKEN)
