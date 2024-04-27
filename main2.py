import asyncio
import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, StateFilter



#извлечение токена из переменной окружения и инициализация объекта бота
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=bot_token)
storage = MemoryStorage()

#Настройка диспетчера и роутов
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

#словарь
currencies_dict = {}

#Определение состояний FSM
class CurrencyStates(StatesGroup):
    currency_name = State()#Состояние для ввода названия валюты
    currency_rate = State()#Состояние для ввода курса
    delete_currency = State()#Состояние для удаления валюты
    change_rate = State()#Состояние для изменения курса
    convert_currency = State()#Состояние для конвертации валюты

#проверка на администратора (условное определение)
ADMIN_USERS = [123456789]

#меню админа
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить валюту"), KeyboardButton(text="Удалить валюту")],
        [KeyboardButton(text="Изменить курс валюты")],
    ],
    resize_keyboard=True,
)

#меню пользователя
user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/get_currencies"), KeyboardButton(text="/convert")],
    ],
    resize_keyboard=True,
)

#обработчик команды /start
@router.message(Command("start"))
async def start_command(message: types.Message):
    if message.from_user.id in ADMIN_USERS:
        await message.answer("Привет, администратор! Выберите действие:", reply_markup=admin_menu)
    else:
        await message.answer("Привет, пользователь! Выберите команду:", reply_markup=user_menu)

#Обработчик команды /manage_currency
@router.message(Command("manage_currency"))
async def manage_currency(message: types.Message):
    # Проверка, является ли пользователь администратором
    if message.from_user.id not in ADMIN_USERS:
        await message.answer("Нет доступа к команде")
    else:
        # Отображаем кнопки для управления валютами
        await message.answer("Выберите действие:", reply_markup=admin_menu)


#обработчик команды /get_currencies
@router.message(Command("get_currencies"))
async def get_currencies(message: types.Message):
    if currencies_dict:
        currencies_list = "\n".join([f"{currency}: {rate}" for currency, rate in currencies_dict.items()])
        await message.answer("Список валют:\n" + currencies_list)
    else:
        await message.answer("Список валют пуст")

#обработчик команды /convert
@router.message(Command("convert"))
async def convert_command(message: types.Message, state: FSMContext):
    await message.answer("Введите название валюты:")
    await state.set_state(CurrencyStates.convert_currency)

#обработчик состояния convert_currency state
@router.message(StateFilter(CurrencyStates.convert_currency))
async def convert_currency_state(message: types.Message, state: FSMContext):
    currency_name = message.text
    if currency_name not in currencies_dict:
        await message.answer("Валюта не найдена. Попробуйте снова")
        await state.finish()
        return

    async with state.proxy() as data:
        data["currency_name"] = currency_name

    await message.answer("Введите сумму:")
    await state.set_state(CurrencyStates.convert_currency)

#Обработчик состояния после ввода суммы
@router.message(StateFilter(CurrencyStates.convert_currency))
async def convert_currency_amount_state(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        async with state.proxy() as data:
            rate = currencies_dict[data["currency_name"]]
            converted_amount = amount * rate
            await message.answer(f"{amount} {data['currency_name']} равно {converted_amount} рублей")
    except ValueError:
        await message.answer("Некорректный формат. Введите число")
    finally:
        await state.finish()



@router.message(StateFilter(CurrencyStates.currency_name))
async def add_currency_command(message: types.Message):
    if message.text == "Добавить валюту":
        await message.answer("Введите название валюты:")
        await CurrencyStates.currency_name.set()


 #Обработчик кнопки "Добавить валюту"
#@router.message(StateFilter(CurrencyStates.currency_name))
#async def add_currency_command(message: types.Message, state: FSMContext):
    #await message.answer("Введите название валюты:")
    #await state.set_state(CurrencyStates.currency_name) # Устанавливаем состояние для ввода названия валюты

#Обработчик состояния currency_name
@router.message(StateFilter(CurrencyStates.currency_name))
async def add_currency_name(message: types.Message, state: FSMContext):
    currency_name = message.text
    if currency_name in currencies_dict:
        await message.answer("Данная валюта уже существует.")
        await state.finish()  # End the state
        return

    async with state.proxy() as data:
        data["currency_name"] = currency_name

    await message.answer(f"Введите курс валюты {currency_name} к рублю:")
    await state.set_state(CurrencyStates.currency_rate)  # Transition to currency rate state

#Обработчик состояния currency_rate
@router.message(StateFilter(CurrencyStates.currency_rate))
async def add_currency_rate(message: types.Message, state: FSMContext):
    try:
        currency_rate = float(message.text)
        async with state.proxy() as data:
            currencies_dict[data["currency_name"]] = currency_rate
            await message.answer(f"Валюта {data['currency_name']} успешно добавлена")
    except ValueError:
        await message.answer("Некорректный формат. Введите число")
    finally:
        await state.finish()

# #Обработчик кнопки "Удалить валюту"
# @router.message(StateFilter(CurrencyStates.delete_currency))
# async def delete_currency_command(message: types.Message, state: FSMContext):
#     await message.answer("Введите название валюты для удаления:")
#     await state.set_state(CurrencyStates.delete_currency)

# Обработчик кнопки "Удалить валюту" в manage_currency
@router.message(StateFilter(CurrencyStates.delete_currency))
async def delete_currency(message: types.Message):
    await message.answer("Введите название валюты для удаления:")
    await CurrencyStates.delete_currency.set()  # Устанавливаем состояние для удаления валюты



# Обработчик состояния delete_currency
@router.message(StateFilter(CurrencyStates.delete_currency))
async def delete_currency_state(message: types.Message, state: FSMContext):
    currency_name = message.text
    if currency_name in currencies_dict:
        del currencies_dict[currency_name]
        await message.answer(f"Валюта {currency_name} удалена")
    else:
        await message.answer("Валюта не найдена")
    await state.finish()

# Обработчик кнопки "Изменить курс валюты"
@router.message(StateFilter(CurrencyStates.change_rate))
async def change_currency_rate_command(message: types.Message, state: FSMContext):
    await message.answer("Введите название валюты для изменения курса:")
    await state.set_state(CurrencyStates.change_rate)

#Обработчик состояния change_rate
@router.message(StateFilter(CurrencyStates.change_rate))
async def change_currency_rate_state(message: types.Message, state: FSMContext):
    currency_name = message.text
    if currency_name not in currencies_dict:
        await message.answer("Валюта не найдена")
        await state.finish()
        return

    async with state.proxy() as data:
        data["currency_name"] = currency_name

    await message.answer("Введите новый курс к рублю:")
    await state.set_state(CurrencyStates.currency_rate)

# Обработчик состояния после изменения курса update_currency_rate_state
@router.message(StateFilter(CurrencyStates.currency_rate))
async def update_currency_rate_state(message: types.Message, state: FSMContext):
    try:
        new_rate = float(message.text)
        async with state.proxy() as data:
            currency_name = data["currency_name"]
            currencies_dict[currency_name] = new_rate
            await message.answer(f"Курс валюты {currency_name} обновлен")
    except ValueError:
        await message.answer("Некорректный формат курса. Введите число")
    finally:
        await state.finish()

#Асинхронный запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
