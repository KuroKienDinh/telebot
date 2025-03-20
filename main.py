#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Filename:    main.py
# @Author:      Kuro
# @Time:        3/20/2025 2:47 PM
import itertools
import logging
import math
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# States
TOTAL_BILL, LEVEL_COUNT, LEVEL_DETAILS, PEOPLE_NAMES = range(4)

# Data storage per conversation
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {
        'current_level': 1,
        'levels': {},
    }
    await update.message.reply_text("Welcome! Please enter the total bill after discount:")
    return TOTAL_BILL

async def get_total_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        total_bill = float(update.message.text)
        user_data[update.effective_chat.id]['total_bill'] = total_bill
        await update.message.reply_text("Enter how many levels (max 5):")
        return LEVEL_COUNT
    except ValueError:
        await update.message.reply_text("Please enter a valid number for total bill.")
        return TOTAL_BILL

async def get_level_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text)
        if count < 1 or count > 5:
            await update.message.reply_text("Number of levels should be between 1 and 5.")
            return LEVEL_COUNT
        user_data[update.effective_chat.id]['level_count'] = count
        await update.message.reply_text(f"Enter max price (before discount) for level 1:")
        return LEVEL_DETAILS
    except ValueError:
        await update.message.reply_text("Please enter a valid integer number.")
        return LEVEL_COUNT

async def get_level_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        max_price = float(update.message.text)
        current_level = user_data[chat_id]['current_level']
        user_data[chat_id]['levels'][current_level] = {'max_price': max_price, 'people': []}
        await update.message.reply_text(f"Enter names for level {current_level}, separated by commas:")
        return PEOPLE_NAMES
    except ValueError:
        await update.message.reply_text("Please enter a valid number for max price.")
        return LEVEL_DETAILS

async def get_people_names(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_level = user_data[chat_id]['current_level']
    names = [name.strip() for name in update.message.text.split(",") if name.strip()]
    if not names:
        await update.message.reply_text("Please enter at least one name.")
        return PEOPLE_NAMES
    user_data[chat_id]['levels'][current_level]['people'] = names

    if current_level < user_data[chat_id]['level_count']:
        user_data[chat_id]['current_level'] += 1
        await update.message.reply_text(f"Enter max price (before discount) for level {user_data[chat_id]['current_level']}:")
        return LEVEL_DETAILS
    else:
        return await calculate_and_show_result(update, context)


async def calculate_and_show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = user_data[chat_id]
    total_bill = data['total_bill']
    levels = data['levels']

    level_data = []
    total_weight = 0

    for level_num, info in levels.items():
        weight = info['max_price'] * len(info['people'])
        total_weight += weight
        level_data.append({
            'level': level_num,
            'max_price': info['max_price'],
            'people': info['people'],
            'weight': weight
        })

    # Step 1: Compute exact share per level
    total_sum = 0
    for level in level_data:
        level_share = (level['weight'] / total_weight) * total_bill
        level['level_total_exact'] = level_share
        level['per_person_exact'] = level_share / len(level['people'])
        level['floor_price'] = math.floor(level['per_person_exact'])
        level['ceil_price'] = math.ceil(level['per_person_exact'])
        level['fractional'] = level['per_person_exact'] - level['floor_price']
        level['final_price'] = level['floor_price']
        level['total_floor_sum'] = level['floor_price'] * len(level['people'])
        total_sum += level['total_floor_sum']

    # Step 2: Sort levels by fractional part descending
    level_data.sort(key=lambda x: x['fractional'], reverse=True)

    # Step 3: Round up levels one by one if needed
    i = 0
    while total_sum < total_bill and i < len(level_data):
        level = level_data[i]
        increment = (level['ceil_price'] - level['floor_price']) * len(level['people'])
        total_sum += increment
        level['final_price'] = level['ceil_price']
        i += 1

    # Step 4: Prepare output
    result_message = "Final prices:\n"
    for level in sorted(level_data, key=lambda x: x['level']):  # Keep original level order
        price = level['final_price']
        for person in level['people']:
            result_message += f"{person}: {price}\n"

    await update.message.reply_text(result_message)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

def main():
    TOKEN =   # Replace with your bot token
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TOTAL_BILL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_total_bill)],
            LEVEL_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_level_count)],
            LEVEL_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_level_details)],
            PEOPLE_NAMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_people_names)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()


