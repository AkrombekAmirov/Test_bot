from file_service.file_read import func_qrcode, process_contract, write_qabul
from file_service.file_database.file_path import get_file_database_path
from keyboards.inline.keyboards_inline import choose_visitor
from keyboards.inline.Dictionary import faculty_file_map1
from utils.db_api.postgresql1 import file_create_
from file_service.file_path import get_file_path
from utils.db_api.core import DatabaseService
from aiogram.dispatcher import FSMContext
from data.config import engine, ADMINS
from states.button import Form
from datetime import datetime
from loader import dp, bot
from aiogram import types
from uuid import uuid4
import logging

logging.basicConfig(filename='bot.log', filemode='w', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

db = DatabaseService(engine=engine)


@dp.callback_query_handler(lambda call: call.data in ['qabul_yes_admin', 'delete_no_admin'])
async def answer(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'qabul_yes_admin':
        await call.message.delete()
        await call.message.answer("Qabul qilish uchun ariza qoldiring.", reply_markup=choose_visitor)
