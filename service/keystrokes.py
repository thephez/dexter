import pyautogui  # Ensure this library is installed

from dexter.service   import Service, Handler, Result
from dexter.core.log  import LOG
from dexter.core.util import get_pygame, fuzzy_list_range, to_alphanumeric

_KEY_ACTION_PHRASES = (
    # Add phrases and corresponding keyboard actions here
    ("Copy that", "ctrl+c", False),
    ("Paste that", "ctrl+v", False),
    ("Refresh", "f5", False),
    ("Open terminal", "ctrl+alt+t", False),
    # You can add more phrases and actions as needed
)

class _KeyboardActionHandler(Handler):
    def __init__(self, service, tokens, reply, belief):
        super().__init__(service, tokens, belief, True)
        self._reply = reply

    def handle(self):
        return Result(self, self._reply, True, False)

class KeyboardActionService(Service):
    def __init__(self, state, belief=0.75):
        super().__init__("KeyboardAction", state)
        self._belief = float(belief)
        self._key_action_phrases = [
            (self._split_phrase(phrase), key_action, is_prefix)
            for phrase, key_action, is_prefix in _KEY_ACTION_PHRASES
        ]

    def _split_phrase(self, phrase):
        return tuple(to_alphanumeric(word) for word in phrase.split())

    def evaluate(self, tokens):
        words = self._words(tokens)
        for phrase, key_action, is_prefix in self._key_action_phrases:
            try:
                start, end, score = fuzzy_list_range(words, phrase)
                if start == 0 and (not is_prefix or end == len(phrase)):
                    self._execute_key_action(key_action)
                    return _KeyboardActionHandler(self, tokens, f"Executed {key_action}", self._belief)
            except ValueError as e:
                continue
        return None

    def _execute_key_action(self, key_action):
        pyautogui.hotkey(*key_action.split('+'))

# ... [Rest of your code or additional functionalities] ...

# When using the service, you will create an instance of KeyboardActionService
