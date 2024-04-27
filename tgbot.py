import asyncio
import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, StateFilter
import asyncpg
import decimal
# Извлечение токена из переменной окружения и инициализация объекта бота
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
if not bot_token:
    raise ValueError("Telegram bot token not found.")

bot = Bot(token=bot_token)
storage = MemoryStorage()

# Настройка диспетчера и роутера
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Словарь для хранения валют и их курсов
currencies_dict = {}

# Определение состояний FSM
class CurrencyStates(StatesGroup):
    currency_name = State()  # Состояние для ввода названия валюты
    currency_rate = State()  # Состояние для ввода курса
    delete_currency = State()  # Состояние для удаления валюты
    change_rate = State()  # Состояние для изменения курса валют (1)
    convert_currency = State()  # Состояние для конвертации валюты (1)
    change_name = State() #  Состояние для изменения курса валют (2)
    convert_amount = State() # Состояние для конвертации валюты (2)
# Список администраторов
ADMIN_USERS = [839078766]

# Меню для администратора
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/add_currency"), KeyboardButton(text="/delete_currency"),
         KeyboardButton(text="/change_currency"), KeyboardButton(text="/get_currencies"), KeyboardButton(text="/convert")],
    ],
    resize_keyboard=True,
)

# Меню для обычных пользователей
user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/get_currencies"), KeyboardButton(text="/convert")],
    ],
    resize_keyboard=True,
)

async def connect_to_database():
    connection = await asyncpg.connect(
        host='127.0.0.1',
        port='5432',
        database='tgbot',
        user='postgres',
        password='egor2003'
    )
    return connection


# Обработчик команды /start
@router.message(Command("start"))
async def start_command(message: types.Message):
    if message.from_user.id in ADMIN_USERS:
        await message.answer("Привет, администратор! Выберите действие:", reply_markup=admin_menu)
    else:
        await message.answer("Привет, пользователь! Выберите команду:", reply_markup=user_menu)

@router.message(Command("get_currencies"))
async def viewing_currency(message: types.Message):
    connection = await connect_to_database()
    currency = await connection.fetch("SELECT * FROM currencies")
    await connection.close()
    if currency:
        for currencys in currency:
            currency_name = currencys[1]
            currency_rate = currencys[2]

            answer_currency = f"Валюта: {currency_name} Номинал: {currency_rate}"
            await message.answer(answer_currency)
    else:
        await message.answer('Список пуст')


# Обработчик команды /add_currency
@router.message(Command("add_currency"))
async def request_currency_name(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_USERS:
        await message.answer("У вас нет доступа к этой команде.")
        return

    await message.answer("Введите название новой валюты:")
    await state.set_state(CurrencyStates.currency_name)


@router.message(StateFilter(CurrencyStates.currency_name))
async def set_currency_name(message: types.Message, state: FSMContext):
    currency_name = message.text.strip()

    connection = await connect_to_database()
    currency = await connection.fetchrow("SELECT * FROM currencies WHERE currency_name = $1", currency_name)
    if currency:
        await message.answer("Такая валюта уже существует. Попробуйте другое название.")
        await state.clear()
    else:
        await state.update_data(currency_name=currency_name)
        await state.set_state(CurrencyStates.currency_rate)
        await message.answer(f"Введите курс валюты {currency_name} к рублю:")


@router.message(StateFilter(CurrencyStates.currency_rate))
async def set_currency_rate(message: types.Message, state: FSMContext):
    try:
        currency_rate = float(message.text)
        data = await state.get_data()
        currency_name = data.get("currency_name")

        connection = await connect_to_database()
        await connection.execute("INSERT INTO currencies (currency_name, rate) VALUES ($1, $2)", currency_name, currency_rate)
        await connection.close()

        await message.answer(f"Валюта {currency_name} успешно добавлена с курсом {currency_rate} к рублю.")
        await state.clear()
    except ValueError:
        await message.answer("Некорректный формат курса. Введите число.")

# Обработчик команды /delete_currency
@router.message(Command("delete_currency"))
async def request_currency_name_for_deletion(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_USERS:
        await message.answer("У вас нет доступа к этой команде.")
        return

    await state.set_state(CurrencyStates.delete_currency)
    await message.answer("Введите название валюты, которую хотите удалить:")


# Обработчик состояния для удаления валюты
@router.message(StateFilter(CurrencyStates.delete_currency))
async def delete_currency_state(message: types.Message, state: FSMContext):
    currency_name = message.text.strip()

    connection = await connect_to_database()
    currency = await connection.fetch("SELECT currency_name FROM currencies WHERE currency_name=$1;", currency_name)
    await connection.close()
    if currency:
        connection = await connect_to_database()
        await connection.execute("DELETE FROM currencies WHERE currency_name=$1;", currency_name)
        await connection.close()

        answer_currency = f"Валюта: {currency_name} была удалена"
        await message.answer(answer_currency)
    else:
        await message.answer('Произошла техническая шоколадка :)')
    await state.clear()


# Обработчик команды /change_currency
@router.message(Command("change_currency"))
async def change_currency_request(message: types.Message, state: FSMContext):
    await state.set_state(CurrencyStates.change_name)
    if message.from_user.id not in ADMIN_USERS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer("Введите название валюты, для которой нужно изменить курс:")

# Обработчик состояния для изменения курса
@router.message(StateFilter(CurrencyStates.change_name))
async def update_currency_rate(message: types.Message, state: FSMContext):
    name = message.text.strip()
    connection = await connect_to_database()
    currency = await connection.fetch("SELECT currency_name FROM currencies WHERE  currency_name=$1;", name)
    if currency:
        await state.update_data(change_name=name)
        await state.set_state(CurrencyStates.change_rate)
        await message.answer('Введите новый курс валюты')
    else:
        await message.answer('А ТАКОЙ ВАЛЮТЫ НЕТУ :(')
    await connection.close()


@router.message(StateFilter(CurrencyStates.change_rate))
async def update_rate(message: types.Message, state: FSMContext):
    currency_rate = message.text.strip()
    data = await state.get_data()
    change_name = data.get('change_name')

    await state.update_data(change_rate=currency_rate)
    connection = await connect_to_database()
    currency = await connection.fetch("SELECT currency_name FROM currencies WHERE currency_name=$1;", change_name)
    if currency:
        connection = await connect_to_database()
        await connection.execute('UPDATE currencies SET rate = $1 WHERE currency_name = $2', currency_rate, change_name)
        await connection.close()
        await message.answer(f'Курс валюты {change_name} был изменён.')
    else:
        await message.answer('А ТАКОЙ ВАЛЮТЫ НЕТУ :(((')
    await state.clear()


# Обработчик команды /convert
@router.message(Command("convert"))
async def convert_command(message: types.Message, state: FSMContext):
    await state.set_state(CurrencyStates.convert_currency)
    await message.answer("Введите название валюты:")

# Обработчик состояния convert_currency
@router.message(StateFilter(CurrencyStates.convert_currency))
async def convert_currency(message: types.Message, state: FSMContext):
    name = message.text.strip()

    await state.update_data(convert_currency=name)
    await state.set_state(CurrencyStates.convert_amount)
    await message.answer('Введите кол-во валюты для конвертации')


    data = await state.get_data()
    currency_name = data.get('convert_currency')
    print(currency_name)
# Обработчик состояния для конвертации валюты
@router.message(StateFilter(CurrencyStates.convert_amount))
async def convert_currency_amount_state(message: types.Message, state: FSMContext):
    try:
        amount = decimal.Decimal(message.text)
        await state.update_data(convert_amount=amount)
        data = await state.get_data()
        currency_name = data.get('convert_currency')
        connection = await connect_to_database()
        rate = await connection.fetch("SELECT rate FROM currencies WHERE currency_name=$1;", currency_name)
        if rate:
            rate_value = rate[0]['rate']
            converted_amount = amount * rate_value
            await message.answer(f"{amount} {currency_name} равно {converted_amount} рублей.")
            await state.clear()
        else:
            await message.answer("Курс валюты не найден.")
    except ValueError:
        await message.answer("Некорректный формат. Введите число.")


# Асинхронный запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
