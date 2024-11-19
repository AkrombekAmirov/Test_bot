from keyboards import for_user, faculty_file_map2, keyboard, yonalish_nomi_keyboard
from aiogram.utils.exceptions import TelegramAPIError, Throttled
from tenacity import retry, stop_after_attempt, wait_exponential
from utils import DatabaseService, Question, User
from aiogram.dispatcher import FSMContext
from LoggerService import LoggerService
from states.button import User
from aiocache import cached
from functools import wraps
from aiogram import types
from loader import dp
import random
import json

# Database initialization
db = DatabaseService()

# Asynchronous cached function to check if user exists
@cached(ttl=60)
async def check_user_exists(telegram_id: str) -> bool:
    """Check if the user exists in cache."""
    LoggerService().logger.info(f"User {telegram_id}: Checking if user exists")
    return await db.get_user_by_id(int(telegram_id)) is not None


# Throttling decorator for callback queries to limit rate
def throttled_callback(rate_limit=2):
    def decorator(func):
        @wraps(func)
        async def wrapper(call, *args, **kwargs):
            try:
                # Add key parameter with call.from_user.id as unique key for throttling
                await dp.throttle(key=f"user:{call.from_user.id}", rate=rate_limit)
                return await func(call, *args, **kwargs)
            except Throttled as e:
                LoggerService().logger.warning(f"User {call.from_user.id}: Throttling limit reached: {e}")
                await call.answer("So‘rovlar tezligi cheklangan, iltimos, qayta urinib ko‘ring.")

        return wrapper

    return decorator


@dp.callback_query_handler(lambda call: call.data == "test_user")
async def start(call: types.CallbackQuery, state: FSMContext):
    LoggerService().logger.info(f"User {call.from_user.id}: Starting test")
    await call.message.answer("Familiya, Ism va Sharifingizni kiriting:")


@dp.message_handler(content_types=types.ContentType.TEXT)
async def start(message: types.Message, state: FSMContext):
    await state.update_data({"name": message.text})
    LoggerService().logger.info(f"User {message.from_user.id}: Started the test")
    if await db.get_user(user_id=int(message.from_user.id)):
        await message.answer("Testni boshlash", reply_markup=yonalish_nomi_keyboard)
    else:
        await message.answer("Telegram raqamingizni yuboring.", reply_markup=keyboard)


@dp.message_handler(content_types=types.ContentType.ANY)
async def test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    LoggerService().logger.info(f"User {message.from_user.id}: Contact received: {message.contact.phone_number}")
    if not await db.get_user(user_id=int(message.from_user.id)):
        await db.add_user(user_id=int(message.from_user.id), name=data["name"],
                          username=message.from_user.username if message.from_user.username else None,
                          phone_number=message.contact.phone_number)

    await state.reset_state(with_data=False)
    await message.answer("Testni boshlash", reply_markup=yonalish_nomi_keyboard)


@dp.message_handler(state=User.zero)
async def answer_seria(message: types.Message, state: FSMContext):
    try:
        await state.update_data({"seria": message.text})
        await message.answer("Familiya, Ism va Sharifingizni kiriting!")
        await User.next()
    except TelegramAPIError as e:
        LoggerService().logger.error(f"User {message.from_user.id}: Telegram API error: {e}")
        await message.answer("Xatolik yuz berdi, qayta urinib ko‘ring.")
    except Exception as e:
        LoggerService().logger.error(f"User {message.from_user.id}: Error during passport entry: {e}")
        await message.answer("Xatolik yuz berdi, qayta urinib ko‘ring.")


@dp.callback_query_handler(
    lambda call: call.data in ["faculty0", "faculty1", "faculty2", "faculty3", "faculty4", "faculty5", "faculty6"]
)
async def start_test(call: types.CallbackQuery, state: FSMContext):
    user_id = int(call.from_user.id)
    try:
        await state.update_data({"faculty": call.data})
        sub = await db.get_subject(faculty_file_map2.get(call.data))
        if sub is not None:
            # Faol natijani olish (status=True)
            result = await db.get_active_result(user_id=user_id)

            if result:
                await start_test_from_number(message=call.message, state=state, result_id=result.get("result_id"),
                                             number=result.get("number"))
                await state.update_data({
                    "result_id": result.get("result_id")
                })
            else:
                # Yangi test boshlash
                all_questions = await db.get(model=Question, filter_by={"subject_id": int(sub.subject_val)})
                selected_questions = random.sample(all_questions, k=25)

                # Test natijasini `Result` jadvalida boshlash
                new_result_id = await db.add_result(
                    user_id=user_id,
                    subject_id=sub.id,
                    question_ids=json.dumps([q.id for q in selected_questions])
                )
                await state.update_data({
                    "result_id": new_result_id,
                })

                # Birinchi yoki keyingi savolni yuborish
                await start_test_from_number(message=call.message, state=state, result_id=new_result_id, number=0)
        else:
            LoggerService().logger.warning(f"User {user_id}: Faculty {call.data} not found")
            await call.message.answer("Tanlangan yo'nalish mavjud emas.")

    except Exception as e:
        LoggerService().logger.error(f"User {user_id}: Error starting test: {e}")
        await call.message.answer("Xatolik yuz berdi, qayta urinib ko‘ring.")


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
async def start_test_from_number(message: types.Message, state: FSMContext, result_id: int, number: int):
    result = await db.get_result_id(result_id)
    if result.number >= 25:
        await end_test(message, state)
        return
    option_ = await db.get_questioin_by_id(question_id=json.loads(result.question_ids)[number])
    random_options = [option_.option1, option_.option2, option_.option3, option_.option4]
    random.shuffle(random_options)
    correct_option_index = random_options.index(option_.option1)
    keyboard_ = types.InlineKeyboardMarkup()
    for index, random_option in enumerate(random_options):
        # Indeks orqali `callback_data` ni o‘rnatish
        keyboard_.add(
            types.InlineKeyboardButton(text=random_option, callback_data=f"answer_{index}_{correct_option_index}"))
    await message.edit_text(text=f"{number + 1}-savol\n{option_.text}", reply_markup=keyboard_)


@dp.callback_query_handler(lambda call: call.data.startswith("answer_"))
@throttled_callback(rate_limit=1)
async def handle_answer(call: types.CallbackQuery, state: FSMContext):
    """Foydalanuvchi javobini qayta ishlash va natijani yangilash."""
    data = await state.get_data()
    result = await db.get_result_id(data["result_id"])
    _, selected_option_index, correct_option_index = call.data.split("_")  # Foydalanuvchi tanlagan indeks
    is_correct = selected_option_index == correct_option_index

    # To‘g‘ri yoki noto‘g‘ri javobni bildiruvchi xabar
    if is_correct:
        LoggerService().logger.info(f"User {call.from_user.id}: Correct answer!")
        await call.answer("To‘g‘ri javob! ✅")
    else:
        LoggerService().logger.info(f"User {call.from_user.id}: Incorrect answer.")
        await call.answer("Noto‘g‘ri javob. ❌")

    if result:
        if is_correct:
            result.correct_answers += 1
        else:
            result.wrong_answers += 1
        result.number += 1  # Hozirgi savol raqamini yangilash
        await db.result_update(data["result_id"], {'number': result.number, 'correct_answers': result.correct_answers,
                                                   'wrong_answers': result.wrong_answers})

        # Test yakunlangani tekshirish
        if result.number >= 25:
            await end_test(call.message, state)
            return
    await start_test_from_number(call.message, state, result_id=data["result_id"], number=result.number)


async def end_test(message: types.Message, state: FSMContext):
    """Test tugagach foydalanuvchiga natijani ko'rsatish."""
    data = await state.get_data()
    result = await db.get_result_id(data["result_id"])
    if result:
        accuracy = result.accuracy()
        summary = (
            f"Hurmatli {(await db.get_user_by_id(user_id=int(result.user_id))).name}!\n"
            f"Test yakunlandi!\n"
            f"To'g'ri javoblar: {result.correct_answers}\n"
            f"Noto'g'ri javoblar: {result.wrong_answers}\n"
            f"Umumiy savollar: {result.number}\n"
            f"Samaradorlik: {result.accuracy():.2f}%\n"
        )
        # await db._update(result)
        await message.edit_text(summary)
        await dp.bot.send_message("765135326", summary)
    await state.finish()
#
#
# # @dp.message_handler(state=User.one)
# # async def answer_name(message: types.Message, state: FSMContext):
# #     try:
# #         await state.update_data({"name": message.text})
# #         data = await state.get_data()
# #         await db.create_user(
# #             telegram_id=message.from_user.id, username=message.from_user.username,
# #             name=data.get("name"), passport=data.get("seria"),
# #             telegram_name=message.from_user.full_name, telegram_number=""
# #         )
# #         await message.answer("Testni boshlash tugmasini bosing", reply_markup=for_user)
# #         await User.next()
# #     except Exception as e:
# #         logging.error(f"Ro'yxatga olishda xatolik: {e}")
# #         await message.answer("Xatolik yuz berdi, qayta urinib ko‘ring.")
# #
# #
# # @dp.callback_query_handler(text="test_yes", state=User.two)
# # async def start_test(call: types.CallbackQuery, state: FSMContext):
# #     try:
# #         user_id = (await db.get_user_by_id(int(call.from_user.id))).id
# #         if await db.get_results_by_user_id(user_id):
# #             await call.message.answer("Har bir foydalanuvchi faqat bir martadan test topshirishlari mumkin!")
# #             await state.finish()
# #         else:
# #             all_questions = db.get_all_questions()
# #             selected_questions = random.sample(all_questions, 13)
# #             await state.update_data({"questions": selected_questions, "current_index": 0, "correct_answers": 0})
# #             await send_question(call.message, state)
# #             await Form.next()
# #     except TelegramAPIError as e:
# #         logging.error(f"Telegram API xatosi: {e}")
# #         await call.message.answer("Xatolik yuz berdi, qayta urinib ko‘ring.")
# #     except Exception as e:
# #         logging.error(f"Testni boshlashda xatolik: {e}")
# #         await call.message.answer("Xatolik yuz berdi, qayta urinib ko‘ring.")
# #
# #
# @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
# async def send_question(message: types.Message, state: FSMContext):
#     """Send question to the user with retries"""
#     try:
#         data = await state.get_data()
#         current_index = data.get("current_index")
#         questions = data.get("questions")
#
#         if current_index < len(questions):
#             question = questions[current_index]
#             options = [question.option1, question.option2, question.option3, question.option4]
#             random.shuffle(options)
#             keyboard_ = InlineKeyboardMarkup(row_width=2)
#             for index, option in enumerate(options):
#                 keyboard_.add(InlineKeyboardButton(option, callback_data=f"answer_{index}"))
#             await message.edit_text(question.question_text, reply_markup=keyboard_)
#             await state.update_data({"question_id": question.id, "options": options})
#         else:
#             correct_answers = data.get("correct_answers")
#             await message.edit_text(
#                 f"Test yakunlandi! ✅\nKo'rsatgichingiz: <b>{round(correct_answers / 13 * 100, 2)} %</b>\n"
#                 f"To‘g‘ri javoblar soni: <b>{correct_answers}</b>\n Jami savollar soni: <b>13 ta</b>"
#             )
#             await state.finish()
#     except MessageNotModified:
#         logging.warning("Xabar o‘zgartirilmadi.")
#     except Exception as e:
#         logging.error(f"Savol yuborishda xatolik: {e}")
#         await message.answer("Xatolik yuz berdi, qayta urinib ko‘ring.")
#
#
# @dp.callback_query_handler(lambda c: c.data.startswith("answer_"), state=User.three)
# @throttled_callback(rate_limit=1)
# async def process_application_response(call: types.CallbackQuery, state: FSMContext):
#     """Process user answer"""
#     try:
#         selected_option_index = int(call.data.split("_")[1])
#         data = await state.get_data()
#         question_id = data.get("question_id")
#         selected_answer = data["options"][selected_option_index]
#
#         question = db.get_question_by_id(question_id)
#         is_correct = selected_answer == question.correct_answer
#
#         user_id = (db.get_user_by_id(str(call.from_user.id))).id
#         db.create_result(user_id=user_id, question_id=question_id, selected_answer=selected_answer,
#                          is_correct=is_correct)
#
#         if is_correct:
#             await call.answer("To‘g‘ri javob! ✅")
#             data["correct_answers"] += 1
#         else:
#             await call.answer("Noto‘g‘ri javob. ❌")
#
#         data["current_index"] += 1
#         await state.update_data(data)
#         await send_question(call.message, state)
#     except Exception as e:
#         logging.error(f"Javobni qayta ishlashda xatolik: {e}")
#         await call.message.answer("Xatolik yuz berdi, qayta urinib ko‘ring.")
