from aiogram.fsm.state import State, StatesGroup

class Onboarding(StatesGroup):
    """Шаги онбординга нового пользователя."""
    waiting_name = State()
    waiting_grade = State()
    waiting_timezone = State()
    waiting_notify_time = State()
    selecting_subjects = State()  # выбор предметов (мультиселект)
    selecting_wave = State()      # выбор волны для каждого предмета
    waiting_capsule = State()     # ожидание текста для «Капсулы времени»

class SettingsFlow(StatesGroup):
    """Редактирование настроек существующего пользователя."""
    main_menu = State()
    editing_time = State()
    editing_subjects = State()
    editing_wave = State()        # subject_name хранится в FSM data
    confirming_done = State()     # подтверждение /done для предмета