import discord
import asyncio
import os
from datetime import datetime as dt
from discord.ext import tasks
from discord.ui import Button, View
import sqlite3 as sl
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.all()
intents.members = True

discordClient = discord.Bot(intents=intents)

con = sl.connect('coles.db', isolation_level=None)
cursor = con.cursor()

from coles_api import *

@discordClient.event
async def on_ready():
	print(f'{discordClient.user} is now online!')
	await discordClient.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="prices"))
	
@tasks.loop(minutes=180)
async def coles_specials_bg():
	try:
		user = discordClient.get_user(int(os.getenv('ME')))
		items = cursor.execute("SELECT * FROM coles_specials").fetchall()
		for product in items:
			special_status = get_item_by_id(product[0])
			if isinstance(special_status, tuple):
				if special_status[6] == False:
					await user.send(f"{product[2]} {product[1]} is no longer avaliable for purchase and will be deleted from your tracking list.")
					print(product[0])
					cursor.execute("DELETE FROM coles_specials WHERE id = ?", (product[0],))
				if product[5] != special_status[5]:
					if special_status[5]:
						cursor.execute("UPDATE coles_specials SET on_sale = ? WHERE id = ?", (special_status[5], product[0]))
						await user.send(f"{product[2]} {product[1]} is on sale for ${special_status[4]}!")
					else:
						cursor.execute("UPDATE coles_specials SET on_sale = ? WHERE id = ?", (special_status[5], product[0]))
						await user.send(f"{product[2]} {product[1]} is no longer on sale and back to its usual price of ${special_status[4]}")
				if (product[4] != special_status[4]):
					cursor.execute("UPDATE coles_specials SET current_price = ? WHERE id = ?", (special_status[4], product[0]))
					if product[4] > special_status[4]:
						await user.send(f"The price of {product[2]} {product[1]} was reduced from ${product[4]} to ${special_status[4]}")
					else:
						await user.send(f"The price of {product[2]} {product[1]} was increased from ${product[4]} to ${special_status[4]}")
			else:
				if special_status == "nah":
					await user.send(f"{product[2]} {product[1]} returned a 404. It may no longer be available.")
	except Exception as e:
		await user.send("Something went wrong getting item details from Coles: " + str(repr(e)) + "\nRestarting internal task in 3 hours")
		await asyncio.sleep(10800)
		coles_specials_bg.restart()

@discordClient.slash_command(description="[Owner] Track an item from Coles")
async def add_coles_item(ctx, id):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		await ctx.respond(add_item_to_db_by_id(id))

@discordClient.slash_command(description="Search a Coles item by name")
async def search_coles_item(ctx, name):
	await ctx.defer()
	try:
		result = search_item(name)
		if result[0] == 0:
			await ctx.respond("No results")
			return
		list_str = "```" + "\n".join([f"{i}. {item[1]} ({item[2]}) - ID: {item[0]}" for i, item in enumerate(result[1:], start=1)]) + "```"
		response = f"{list_str}"
		await ctx.respond(response)
	except discord.errors.HTTPException as e:
		if "Must be 2000 or fewer in length." in str(e):
			await ctx.respond(f"Your search returned {result[0]} results. Please make your search term more specific.")