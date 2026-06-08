import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup  # ИСПРАВЛЕНО!
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8815700368:AAG99Kd5rhSwT-F-Vs9Zz1S5isI7-SmJo0E"
ADMIN_ID = 8426562283  # ЗАМЕНИТЕ НА ВАШ ID

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Хранилище активных диалогов
active_dialogs = {}

# ============ КЛАВИАТУРЫ ============
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📞 Позвать Вельвета")],
        [KeyboardButton(text="✉️ Отправить сообщение")]
    ],
    resize_keyboard=True
)

anon_choice = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🕵️ Анонимно", callback_data="send_anon")],
        [InlineKeyboardButton(text="👤 Не анонимно", callback_data="send_not_anon")]
    ]
)

# ============ СОСТОЯНИЯ ============
class MsgState(StatesGroup):
    waiting_for_message = State()
    waiting_for_reply = State()

# ============ СТАРТ ============
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привет, дружище! Спешу сообщить, что на тебя заказали деанон... \n\nЛадно, это шутка 😄 Что хочешь?",
        reply_markup=main_menu
    )

# ============ ПОЗВАТЬ ВЕЛЬВЕТА ============
@dp.message(F.text == "📞 Позвать Вельвета")
async def call_velvet(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    
    if user_id in active_dialogs:
        await message.answer("У вас уже активный диалог с Вельветом. Напишите ваше сообщение.")
        return
    
    await bot.send_message(
        ADMIN_ID,
        f"🔔 *Вас зовут!*\n\nПользователь: @{username} (ID: `{user_id}`)\nХочет пообщаться неанонимно.\n\nИспользуй /reply {user_id} [текст] чтобы ответить.",
        parse_mode="Markdown"
    )
    
    active_dialogs[user_id] = True
    await state.set_state(MsgState.waiting_for_message)
    await state.update_data(partner_id=ADMIN_ID, dialog_type="call")
    await message.answer("✅ Вельвет получил уведомление. Как только он ответит — вы увидите сообщение здесь.\n\nМожете писать первым.", reply_markup=main_menu)

# ============ КОМАНДА /reply ДЛЯ АДМИНА ============
@dp.message(Command("reply"))
async def reply_to_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: `/reply user_id текст`", parse_mode="Markdown")
        return
    
    _, user_id_str, reply_text = parts
    try:
        user_id = int(user_id_str)
    except:
        await message.answer("Неверный ID пользователя")
        return
    
    if user_id not in active_dialogs:
        await message.answer("Этот пользователь не в активном диалоге или завершил сессию.")
        return
    
    await bot.send_message(user_id, f"✉️ *Вельвет:* {reply_text}", parse_mode="Markdown")
    await message.answer(f"✅ Ответ отправлен пользователю {user_id}")

# ============ ОТПРАВИТЬ СООБЩЕНИЕ ============
@dp.message(F.text == "✉️ Отправить сообщение")
async def ask_anon(message: types.Message, state: FSMContext):
    await state.set_state(MsgState.waiting_for_message)
    await state.update_data(partner_id=ADMIN_ID, dialog_type="message")
    await message.answer(
        "Выберите режим отправки:",
        reply_markup=anon_choice
    )

@dp.callback_query(lambda c: c.data in ["send_anon", "send_not_anon"])
async def choose_mode(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data
    await state.update_data(mode=mode)
    await callback.message.edit_text("✏️ Напишите ваше сообщение:")
    await callback.answer()

# ============ ОБРАБОТКА СООБЩЕНИЙ ============
@dp.message(StateFilter(MsgState.waiting_for_message))
async def receive_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    mode = data.get("mode")
    dialog_type = data.get("dialog_type")
    username = message.from_user.username or message.from_user.full_name
    
    if dialog_type == "call":
        await bot.send_message(
            ADMIN_ID,
            f"💬 *Сообщение от пользователя* (ID: `{user_id}`):\n\n{message.text}\n\nОтветь: /reply {user_id} [текст]",
            parse_mode="Markdown"
        )
        await message.answer("📤 Ваше сообщение отправлено Вельвету. Ожидайте ответа.")
        await state.clear()
        return
    
    if mode == "send_anon":
        await bot.send_message(
            ADMIN_ID,
            f"📩 *Новое сообщение (выбрано «Анонимно», но вы видите отправителя)*\n\nОт: `{user_id}` (@{username})\n\nТекст:\n{message.text}",
            parse_mode="Markdown"
        )
        await message.answer("✅ Ваше обращение отправлено.")
    else:
        await bot.send_message(
            ADMIN_ID,
            f"📩 *Новое сообщение (выбрано «Не анонимно»)*\n\nОт: `{user_id}` (@{username})\n\nТекст:\n{message.text}",
            parse_mode="Markdown"
        )
        await message.answer("✅ Ваше обращение отправлено.")
    
    await state.clear()
    await message.answer("Вернуться в меню?", reply_markup=main_menu)

# ============ ЗАВЕРШЕНИЕ ДИАЛОГА ============
@dp.message(Command("end"))
async def end_dialog(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_dialogs:
        del active_dialogs[user_id]
        await message.answer("✅ Диалог завершён. Чтобы начать новый — нажмите «Позвать Вельвета».")
    else:
        await message.answer("У вас нет активного диалога.")

# ============ ОБРАБОТКА ЛЮБЫХ ДРУГИХ СООБЩЕНИЙ ============
@dp.message()
async def unknown(message: types.Message):
    await message.answer("Используйте кнопки меню.", reply_markup=main_menu)

# ============ ЗАПУСК ============
async def main():
    print("✅ Бот запущен и работает 24/7")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())