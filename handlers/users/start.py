from aiogram.dispatcher.filters.builtin import CommandStart
from keyboards import admin_menu, for_user
from utils import DatabaseService
from aiogram.types import Message
from data.config import ADMINS
from loader import dp

db = DatabaseService()


@dp.message_handler(CommandStart())
async def bot_start(message: Message):
    if str(message.from_user.id) == str(ADMINS):
        await message.answer(f"Salom, {message.from_user.full_name}!", reply_markup=admin_menu)
    else:
        await message.answer(f"Salom, {message.from_user.full_name}!\nPasportingiz seria va raqamini kiriting.\nNamuna: AA1234567")