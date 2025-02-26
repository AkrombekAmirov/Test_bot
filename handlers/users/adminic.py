from keyboards import admin_menu, yonalish_nomi_keyboard, list_faculty, faculty_file_map2
from utils.db_api.core import DatabaseService
from file_service import read_file, join_file
from aiogram.dispatcher import FSMContext
from data.config import engine, ADMINS
from datetime import datetime
from loader import dp, bot
from aiogram import types
from states import User
from uuid import uuid4
import logging

logging.basicConfig(filename='bot.log', filemode='w', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

db = DatabaseService()


@dp.message_handler(commands=["admin"])
async def admin(message: types.Message):
    await message.answer("Admin panelga keldingiz\nXizmat turini tanlang", reply_markup=admin_menu)


@dp.callback_query_handler(lambda call: call.data == "admin_add_test")
async def admin_add_department(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Yo'nalishni tanlang", reply_markup=yonalish_nomi_keyboard)
    await User.zero.set()


@dp.callback_query_handler(lambda call: call.data in list_faculty, state=User.zero)
async def admin_add_subject(call: types.CallbackQuery, state: FSMContext):
    await state.update_data({"faculty_": call.data})
    await call.message.answer("Tast tayyorlangan fileni yuboring!\nEslatma file nomiga etibor bering!")
    await User.one.set()


@dp.message_handler(content_types=types.ContentTypes.DOCUMENT, state=User.one)
async def handle_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    subject_id = await db.get_subject(name=faculty_file_map2.get(data["faculty_"]))
    await dp.bot.download_file(
        (await dp.bot.get_file(message.document.file_id)).file_path,
        await join_file(file_name=message.document.file_name)
    )
    await message.answer("Fayl saqlandi!")
    if not await read_file(file_path=message.document.file_name, subject_id=int(4)):
        await message.answer("Testlar bazasiga qo'shildi", reply_markup=admin_menu)
        await state.reset_state(with_data=False)
