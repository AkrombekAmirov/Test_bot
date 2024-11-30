from aiogram.utils.exceptions import TelegramAPIError, Throttled
from tenacity import retry, stop_after_attempt, wait_exponential
from keyboards import faculty_file_map2, yonalish_nomi_keyboard
from utils import DatabaseService, Question
from aiogram.dispatcher import FSMContext
from LoggerService import LoggerService
from aiocache import cached
from functools import wraps
from aiogram import types
from loader import dp
import random
import json
from file_service import read_user_info

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
    if await db.get_active_result(user_id=call.from_user.id):
        LoggerService().logger.info(f"User {call.from_user.id}: Starting test")
        await call.message.answer("Pasportingiz seria va raqamini kiriting.\n Namuna: AA1234567")


@dp.message_handler(content_types=types.ContentType.TEXT)
async def start(message: types.Message, state: FSMContext):
    try:
        if await read_user_info(message.text):
            user_info = await read_user_info(message.text)
            await message.answer(f"{user_info[0]} testni boshlang!", reply_markup=yonalish_nomi_keyboard)
            if await db.get_user_by_id(user_id=int(message.from_user.id)) is None:
                await db.add_user(user_id=int(message.from_user.id), name=str(user_info[0]),
                                  username=str(user_info[1]),
                                  phone_number=str(user_info[2]))
        elif not await read_user_info(message.text):
            await message.answer("Pasport ma'lumotingiz topilmadi qayta urinib ko‘ring!\nNamuna: AA1234567")
    except TelegramAPIError as e:
        LoggerService().logger.error(f"Unexpected error for user {message.from_user.id}: {e}")
    except Exception as e:
        LoggerService().logger.error(f"Unexpected error for user {message.from_user.id}: {e}")
        await message.answer("Xatolik yuz berdi, iltimos, keyinroq qayta urinib ko'ring.")


@dp.callback_query_handler(
    lambda call: call.data in ["faculty0", "faculty1", "faculty2", "faculty3", "faculty4", "faculty5", "faculty6"]
)
async def start_test(call: types.CallbackQuery, state: FSMContext):
    user_id = int(call.from_user.id)
    try:
        if await db.get_user_by_id(user_id=user_id) is not None:
            user_info = await db.get_user_by_id(user_id=user_id)
            sub = await db.get_subject(faculty_file_map2.get(f"faculty{user_info.phone_number}"))
            await call.message.answer(
                f"❗️Sizga {sub.name} yunalishi buyicha testlar taqdim qilindi. Agar yo'nalishingizga mos bo'lmagan test taqdim qilingan holatda testni to'xtatib adminga murojaat qiling❗️")
            if sub is not None:
                if await db.get_active_result(user_id=user_id) is not None:
                    result = await db.get_active_result(user_id=user_id)
                    await start_test_from_number(message=call.message, state=state, result_id=result.get("result_id"),
                                                 number=result.get("number"), user_id=call.from_user.id)
                    await state.update_data({
                        "result_id": result.get("result_id")
                    })
                elif await db.get_active_result(user_id=user_id) is None:
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
                    await start_test_from_number(message=call.message, state=state, result_id=new_result_id, number=0,
                                                 user_id=call.from_user.id)
        else:
            LoggerService().logger.warning(f"User {user_id}: Faculty {call.data} not found")
            await call.message.answer("Tanlangan yo'nalish mavjud emas.")
    except Exception as e:
        LoggerService().logger.error(f"User {user_id}: Error starting test: {e}")
        await call.message.answer("Xatolik yuz berdi, qayta urinib ko‘ring.")


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
async def start_test_from_number(message: types.Message, state: FSMContext, result_id: int, number: int, user_id: str,
                                 correct_answer: str = 0):
    if await db.get_user_by_id(int(user_id)) is None:
        await message.answer("Pasportingiz seria va raqamini kiriting.\nNamuna: AA1234567")
        return
    result = await db.get_result_id(result_id)
    await state.update_data({"res": number})
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
    await message.edit_text(text=f"{number + 1}-savol\nTo'g'ri javob: {correct_answer}\n{option_.text}",
                            reply_markup=keyboard_)


@dp.callback_query_handler(lambda call: call.data.startswith("answer_"))
@throttled_callback(rate_limit=1)
async def handle_answer(call: types.CallbackQuery, state: FSMContext):
    """Foydalanuvchi javobini qayta ishlash va natijani yangilash."""
    user_ = await db.get_active_result(int(call.from_user.id))
    if user_ is None:
        await call.message.answer("Pasportingiz seria va raqamini kiriting.\nNamuna: AA1234567")
        return
    result = await db.get_result_id(int(user_.get("result_id")))

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
        await db.result_update(user_.get("result_id"),
                               {'number': result.number, 'correct_answers': result.correct_answers,
                                'wrong_answers': result.wrong_answers})

        # Test yakunlangani tekshirish
        if result.number >= 25:
            await end_test(call.message, state)
            return
    await start_test_from_number(call.message, state, result_id=user_.get("result_id"), number=result.number,
                                 correct_answer=result.correct_answers, user_id=call.from_user.id)


async def end_test(message: types.Message, state: FSMContext):
    """Test tugagach foydalanuvchiga natijani ko'rsatish."""
    data = await state.get_data()
    result = await db.get_result_id(data["result_id"])
    if result:
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
        await dp.bot.send_message("6365813018", summary)
    await state.finish()
