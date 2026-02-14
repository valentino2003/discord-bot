import discord
from discord.ext import commands, tasks
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# === LOAD KONFIGURASI DARI .env ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
FIVEM_IP = os.getenv("FIVEM_IP")
FIVEM_PORT = os.getenv("FIVEM_PORT")

# === DISCORD BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True   # WAJIB supaya bot bisa baca command
bot = commands.Bot(command_prefix="!", intents=intents)

# === SIMPAN PLAYER TERAKHIR UNTUK MONITORING ===
last_players = {}

# === FUNGSI AMBIL DATA PLAYERS ===
def get_players():
    try:
        url = f"http://{FIVEM_IP}:{FIVEM_PORT}/players.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print("Error get_players:", e)
        return None

# === FUNGSI AMBIL INFO SERVER ===
def get_server_info():
    try:
        url = f"http://{FIVEM_IP}:{FIVEM_PORT}/info.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print("Error get_server_info:", e)
        return None

# === COMMAND !players ===
@bot.command()
async def players(ctx):
    print(f"[DEBUG] Command !players dipanggil oleh {ctx.author}")
    players = get_players()
    if not players:
        await ctx.send("❌ Server offline atau gagal ambil data.")
        return

    jumlah = len(players)
    embed = discord.Embed(
        title="👥 Players Online on EXE",
        description=f"Total: **{jumlah}** player",
        color=discord.Color.green()
    )
    embed.set_footer(text="FiveM Server Monitor")

    for p in players:
        name = p.get("name", "Unknown")
        player_id = p.get("id", "N/A")

        # hitung jam connect
        connected_seconds = p.get("connected", 0)
        join_time = datetime.now() - timedelta(seconds=connected_seconds)
        join_time_str = join_time.strftime("%H:%M:%S")

        embed.add_field(
            name=f"🆔 {player_id} | {name}",
            value=f"⏰ Join: {join_time_str}",
            inline=False
        )

    await ctx.send(embed=embed)

# === COMMAND !serverinfo ===
@bot.command()
async def serverinfo(ctx):
    print(f"[DEBUG] Command !serverinfo dipanggil oleh {ctx.author}")
    info = get_server_info()
    if not info:
        await ctx.send("❌ Gagal ambil info server.")
        return

    max_clients = info.get("vars", {}).get("sv_maxClients", "Unknown")
    hostname = info.get("vars", {}).get("sv_hostname", "Unknown Server")

    embed = discord.Embed(
        title="📡 Server Info",
        color=discord.Color.blue()
    )
    embed.add_field(name="🏷️ Nama Server", value=hostname, inline=False)
    embed.add_field(name="👥 Max Slot", value=max_clients, inline=True)
    embed.set_footer(text="FiveM Server Monitor")

    await ctx.send(embed=embed)

# === COMMAND !player <id> ===
@bot.command()
async def player(ctx, player_id: int):
    print(f"[DEBUG] Command !player {player_id} dipanggil oleh {ctx.author}")
    players = get_players()
    if not players:
        await ctx.send("❌ Server offline atau gagal ambil data.")
        return

    # cari player dengan ID
    player = next((p for p in players if p.get("id") == player_id), None)

    if not player:
        await ctx.send(f"⚠️ Player dengan ID {player_id} tidak ditemukan.")
        return

    # embed untuk detail player
    embed = discord.Embed(
        title=f"🧍 Detail Player ID {player_id}",
        color=discord.Color.orange()
    )

    # tampilkan semua key-value yang ada di JSON player
    for key, value in player.items():
        if isinstance(value, list):
            value = "\n".join(value)
        embed.add_field(name=key, value=str(value), inline=False)

    embed.set_footer(text="FiveM Server Monitor")

    await ctx.send(embed=embed)

# === LOOP UNTUK UPDATE STATUS BOT ===
@tasks.loop(seconds=15)  # update setiap 60 detik
async def update_status():
    players = get_players()
    if players is not None:
        jumlah = len(players)
        await bot.change_presence(
            activity=discord.Game(name=f"👥 {jumlah} Players On EXECUTIVERP ")
        )
    else:
        await bot.change_presence(
            activity=discord.Game(name="❌ Server Offline")
        )

# === LOOP MONITOR REALTIME CONNECT/DISCONNECT ===
# === LOOP MONITOR REALTIME CONNECT/DISCONNECT ===
# === LOOP MONITOR REALTIME CONNECT/DISCONNECT ===
@tasks.loop(seconds=1)  # cek tiap 10 detik
async def monitor_players():
    global last_players
    players = get_players()

    if players is None:
        return

    current_players = {p["id"]: p for p in players}

    joined = set(current_players.keys()) - set(last_players.keys())
    left = set(last_players.keys()) - set(current_players.keys())

    channel = discord.utils.get(bot.get_all_channels(), name="bot-dump")
    if channel:
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")  # tanggal + jam

        # === PLAYER CONNECT ===
        for pid in joined:
            p = current_players[pid]
            embed = discord.Embed(
                title="🟢 Player Connect",
                color=discord.Color.green()
            )
            embed.add_field(name="🆔 ID", value=str(pid), inline=True)
            embed.add_field(name="🧍 Nama", value=p.get("name", "Unknown"), inline=True)
            embed.add_field(name="⏰ Waktu", value=now, inline=False)
            embed.set_footer(text="FiveM Server Monitor")

            await channel.send(embed=embed)

        # === PLAYER DISCONNECT ===
        for pid in left:
            p = last_players[pid]
            embed = discord.Embed(
                title="🔴 Player Disconnect",
                color=discord.Color.red()
            )
            embed.add_field(name="🆔 ID", value=str(pid), inline=True)
            embed.add_field(name="🧍 Nama", value=p.get("name", "Unknown"), inline=True)
            embed.add_field(name="⏰ Waktu", value=now, inline=False)
            embed.set_footer(text="FiveM Server Monitor")

            await channel.send(embed=embed)

    last_players = current_players


# === EVENT SAAT BOT SIAP ===
@bot.event
async def on_ready():
    print(f"✅ Bot sudah login sebagai {bot.user}")
    update_status.start()
    monitor_players.start()

# === JALANKAN BOT ===
bot.run(TOKEN)
