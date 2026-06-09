import discord
from discord.ext import commands
import datetime
import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()  # โหลดค่าจาก .env

TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")



intents = discord.Intents.default()
intents.voice_states = True  # สำคัญมาก! เพื่อให้บอทรู้ว่าใครเข้า-ออก VC
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DATA_FILE = "vc_records.json"
active_users = {}

def load_record():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"user_id": None, "user_name": "ยังไม่มี", "duration_seconds": 0}


def save_record(record):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=4)

def send_to_webhook(content):
    data = {"content": content}
    requests.post(WEBHOOK_URL, json=data)

# แปลงวินาทีเป็นข้อความอ่านง่าย (ชั่วโมง:นาที:วินาที)
def format_time(seconds):
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours} ชั่วโมง {minutes} นาที {secs} วินาที"

@bot.event
async def on_ready():
    print(f'บอทกรรมการสถิติ {bot.user} พร้อมทำงาน!')

# 4. ดักจับเหตุการณ์ คนเข้า-ออกจากห้องเสียง
@bot.event
async def on_voice_state_update(member, before, after):
    # กรณีที่ 1: ผู้ใช้กดเข้าห้อง VC (จากเดิมไม่ได้อยู่ห้องไหนเลย หรือย้ายห้อง)
    if before.channel is None and after.channel is not None:
        # บันทึกเวลาที่เริ่มเข้า
        active_users[member.id] = datetime.datetime.now()
        print(f"[+] {member.name} เข้าห้อง {after.channel.name}")

    # กรณีที่ 2: ผู้ใช้กดออกจากห้อง VC (หรือหลุด)
    elif before.channel is not None and after.channel is None:
        if member.id in active_users:
            join_time = active_users.pop(member.id)
            leave_time = datetime.datetime.now()
            
            # คำนวณเวลาที่อยู่ในห้อง (หน่วยเป็นวินาที)
            duration = (leave_time - join_time).total_seconds()
            print(f"[-] {member.name} ออกจากห้อง อยู่ไปทั้งหมด: {format_time(duration)}")

            # โหลดสถิติโลกปัจจุบันมาเทียบ
            current_record = load_record()

            # ถ้าทำลายสถิติเก่าได้!
            if duration > current_record["duration_seconds"]:
                new_record = {
                    "user_id": member.id,
                    "user_name": member.name,
                    "duration_seconds": duration
                }
                save_record(new_record)
                
                # ข้อความแสดงความยินดีส่งผ่าน Webhook
                message = (
                    f"🏆 **Record** 🏆\n"
                    f"👑 **{member.name}** ได้ทำลายสถิติการสิงสถิตใน VC นานที่สุด!\n"
                    f"⏱️ เวลาเดิม: `{format_time(current_record['duration_seconds'])}` (โดย {current_record['user_name']})\n"
                    f"🔥 **เวลาใหม่: `{format_time(duration)}`**"
                )
                send_to_webhook(message)

# 5. แถมคำสั่งพิมพ์เช็คสถิติในดิสคอร์ดได้ด้วย (!record)
@bot.command()
async def record(ctx):
    current_record = load_record()
    time_str = format_time(current_record['duration_seconds'])
    await ctx.send(f"👑 **World Record คนสิง VC นานที่สุดในตอนนี้:**\n> ผู้ครองแชมป์: **{current_record['user_name']}**\n> เวลาสถิติ: `{time_str}`")

bot.run(TOKEN)
