import pyautogui

from dexter.service   import Service, Handler, Result
from dexter.core.log  import LOG
from dexter.core.util import get_pygame, fuzzy_list_range, to_alphanumeric

from playsound import playsound

_KEY_ACTION_PHRASES_DICT = {
    "Copy that": ("ctrl+c", False),
    "Paste that": ("ctrl+v", False),
    "Copy from terminal": ("ctrl+shift+c", False),
    "Paste to terminal": ("ctrl+shift+v", False),
    "Refresh": ("f5", False),
    "Open terminal": ("ctrl+alt+t", False),
    "Show applications": ("win", False),
    "Show notifications": ("win+m", False),
    "Open System Monitor": ("win+2", False),
    "Open Firefox": ("win+3", False),
    "Open Chrome": ("win+6", False),
    "Open Thunderbird": ("win+7", False),
    "Open Code": ("win+8", False),
    "Open Signal": ("win+9", False),
    "Open Slack": ("ctrl+alt+shift+s", False),
    "Next application": ("alt+tab", False),
    "Last application": ("alt+shift+tab", False),
    "Next window": ("alt+`", False),
    "Last window": ("alt+shift+`", False),
    "Press escape key": ("esc", False),
    "Move up": ("up", False),
    "Move down": ("down", False),
    "Page up": ("pageup", False),
    "Page down": ("pagedown", False),
}

class _KeyboardActionHandler(Handler):
    def __init__(self, service, tokens, reply, belief):
        super().__init__(service, tokens, belief, True)
        self._reply = reply

    def handle(self):
        return Result(self, self._reply, True, False)

class KeyboardActionService(Service):
    def __init__(self, state, belief=0.80):
        super().__init__("KeyboardAction", state)
        self._belief = float(belief)
        self._key_action_phrases_dict = {
            self._split_phrase(phrase): (key_action, is_prefix)
            for phrase, (key_action, is_prefix) in _KEY_ACTION_PHRASES_DICT.items()
        }

    def _split_phrase(self, phrase):
        return tuple(to_alphanumeric(word) for word in phrase.split())

    def evaluate(self, tokens):
        words = self._words(tokens)
        for phrase, (key_action, is_prefix) in self._key_action_phrases_dict.items():
            try:
                start, end, score = fuzzy_list_range(words, phrase)
                if start == 0 and (not is_prefix or end == len(phrase)):
                    self._execute_key_action(key_action)
                    # playsound('sounds/keystroke-success.ogg')
                    return _KeyboardActionHandler(self, tokens, None, self._belief)
            except ValueError:
                continue
        # playsound('sounds/keystroke-failure.ogg')
        return None

    def _execute_key_action(self, key_action):
        pyautogui.hotkey(*key_action.split('+'))
