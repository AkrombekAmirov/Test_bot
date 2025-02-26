from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

for_user = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Testni boshlash", callback_data="test_user")
        ],
    ]
)

admin_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Test qushish", callback_data="admin_add_test")
        ],
        [
            InlineKeyboardButton(text="Yangi test qo'shish", callback_data="admin_add_test")
        ],
    ]
)


yonalish_nomi_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        # [
        #     InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti tarbiyachisi", callback_data="faculty0"),
        # ],
        # [
        #     InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti psixologi", callback_data="faculty1"),
        # ],
        # [
        #     InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti direktori", callback_data="faculty2"),
        # ],
        # [
        #     InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti metodisti", callback_data="faculty3"),
        # ],
        [
            InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti defektologi/logopedi", callback_data="faculty4"),
        ],
        # [
        #     InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti musiqa rahbari", callback_data="faculty5"),

        # [
        #     InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti metodisti", callback_data="faculty3"),
        # ],
        # [
        #     InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti defektologi/logopedi", callback_data="faculty4"),
        # ],
        # [
        #     InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti musiqa rahbari", callback_data="faculty5"),
        # ],
        # [
        #     InlineKeyboardButton(text="Maktabgacha ta’lim tashkiloti oshpazi", callback_data="faculty6"),
        # ]
    ])

keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
button = KeyboardButton(text="📞 Telefon raqamingizni yuboring", request_contact=True)
keyboard.add(button)
