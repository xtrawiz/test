import gettext
import os
from babel.support import Translations

# Assuming crypto_bot is the project root.
# locale directory should be crypto_bot/locale
# Docker WORKDIR is /app, and crypto_bot is a subdirectory, so /app/crypto_bot
# If this file is /app/crypto_bot/core/translations.py, then locale is ../locale
# For simplicity and consistency with how other paths are treated (e.g., in Dockerfiles)
# we assume that the relevant CWD for finding 'locale' is the project root.
# When running inside Docker, if WORKDIR is /app, then paths like 'crypto_bot/locale'
# would be relative to /app.
# Let's ensure this works correctly by using an absolute path derived from this file's location.

current_dir = os.path.dirname(os.path.abspath(__file__)) # core/
project_root_dir = os.path.abspath(os.path.join(current_dir, '..')) # crypto_bot/
LOCALE_DIR = os.path.join(project_root_dir, 'locale')

DEFAULT_LANG = 'fa' # Persian

# Global cache for translations objects
_translations_cache = {}

def get_translations_for_lang(lang: str = DEFAULT_LANG) -> Translations:
    """
    Loads and returns a Translations object for the given language.
    Caches the loaded object to avoid reloading from disk.
    """
    if lang not in _translations_cache:
        try:
            _translations_cache[lang] = Translations.load(LOCALE_DIR, [lang], domain='messages')
        except Exception as e:
            # Fallback to a NullTranslations if loading fails, and log an error.
            # This prevents the app from crashing if translations are missing for a language.
            print(f"Error loading translations for lang '{lang}' from '{LOCALE_DIR}': {e}")
            print(f"Ensure .mo files exist in {LOCALE_DIR}/{lang}/LC_MESSAGES/messages.mo")
            # You might want to use a more robust logging mechanism here.
            _translations_cache[lang] = gettext.NullTranslations()
            
    return _translations_cache[lang]

def gettext_provider(text: str, lang: str = DEFAULT_LANG) -> str:
    """
    Translates the given text to the specified language.
    Uses the 'gettext' method of the loaded Translations object.
    """
    translations = get_translations_for_lang(lang)
    return translations.gettext(text)

def ngettext_provider(singular: str, plural: str, n: int, lang: str = DEFAULT_LANG) -> str:
    """
    Translates a singular/plural string based on the number 'n' to the specified language.
    Uses the 'ngettext' method of the loaded Translations object.
    """
    translations = get_translations_for_lang(lang)
    return translations.ngettext(singular, plural, n)

# Alias for convenience, often used as _() in templates or code.
_ = gettext_provider

# Example usage (for testing or demonstration):
if __name__ == '__main__':
    # This example assumes you have run pybabel init/compile for 'fa' and 'en' (optional for en)
    # and messages.pot contains "Hello, world!"
    
    # To test this, you would need to:
    # 1. mkdir -p crypto_bot/locale
    # 2. In some code/template: _("Hello, world!")
    # 3. pybabel extract -F crypto_bot/babel.cfg -o crypto_bot/locale/messages.pot crypto_bot/
    # 4. pybabel init -i crypto_bot/locale/messages.pot -d crypto_bot/locale -l fa
    # 5. Edit crypto_bot/locale/fa/LC_MESSAGES/messages.po: msgstr "سلام دنیا!"
    # 6. pybabel compile -d crypto_bot/locale
    
    print(f"Locale directory configured at: {LOCALE_DIR}")
    
    # Simulate settings if your core.settings.config is complex or relies on env vars
    # from core.settings.config import settings # This might fail if env vars not set

    print(f"Default language: {DEFAULT_LANG}")
    
    # Test with a known string (assuming it's in your .po/.mo files)
    test_string_original = "Hello from FastAPI with Jinja2!" # Match a string in test_page.html
    
    # Test Persian translation
    translated_text_fa = gettext_provider(test_string_original, lang='fa')
    print(f"Original: '{test_string_original}'")
    print(f"Persian Translation: '{translated_text_fa}'")

    # Test with a non-existent language (should use NullTranslations and return original)
    translated_text_xx = gettext_provider(test_string_original, lang='xx')
    print(f"Non-existent lang 'xx' Translation: '{translated_text_xx}' (should be original)")

    # Test ngettext
    singular_item = "%(num)d item"
    plural_items = "%(num)d items"
    
    # Assuming these are in your .po files:
    # msgid "%(num)d item"
    # msgid_plural "%(num)d items"
    # msgstr[0] "%(num)d مورد"  (for Persian n=1)
    # msgstr[1] "%(num)d موارد" (for Persian n!=1)

    translated_n_fa_singular = ngettext_provider(singular_item, plural_items, 1, lang='fa')
    translated_n_fa_plural = ngettext_provider(singular_item, plural_items, 5, lang='fa')
    
    print(f"Singular (fa): {translated_n_fa_singular % {'num': 1}}")
    print(f"Plural (fa): {translated_n_fa_plural % {'num': 5}}")

    # Ensure the global alias works
    message_fa = _(test_string_original, lang='fa')
    print(f"Using alias _() for Persian: '{message_fa}'")
