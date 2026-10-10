import re

from django.core.exceptions import ValidationError


class MixedCharacterPasswordValidator:
    message = (
        "Use at least 8 characters, including an uppercase letter, a lowercase "
        "letter, a number, and a special character."
    )

    def validate(self, password, user=None):
        checks = (
            re.search(r"[A-Z]", password),
            re.search(r"[a-z]", password),
            re.search(r"\d", password),
            re.search(r"[^A-Za-z0-9]", password),
        )
        if len(password) < 8 or not all(checks):
            raise ValidationError(self.message, code="password_not_mixed")

    def get_help_text(self):
        return self.message
