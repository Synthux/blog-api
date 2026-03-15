import pytz
from django.utils import timezone, translation

SUPPORTED_LANGUAGES = ['en', 'ru', 'kk']
DEFAULT_LANGUAGE = 'en'


class LanguageMiddleware:
    """
    Determines the active language and timezone for every request.
    Priority: user profile > ?lang= param > Accept-Language header > default (en).
    Placed after AuthenticationMiddleware so request.user is available.
    """

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        lang = self._resolve_language(request)
        translation.activate(lang)
        request.LANGUAGE_CODE = lang

        self._activate_timezone(request)

        response = self.get_response(request)
        translation.deactivate()
        return response
    
    def _resolve_language(self, request) -> str:
        # 1. Authenticated user's saved preference
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            lang = getattr(user, 'preferred_language', '')
            if lang in SUPPORTED_LANGUAGES:
                return lang
            
        # 2. ?lang= query parameter
        lang = request.GET.get('lang', '')
        if lang in SUPPORTED_LANGUAGES:
            return lang
        
        # 3. Accept-Language header
        accept = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        for entry in accept.split(','):
            code = entry.strip().split(';')[0].split('-')[0].lower()
            if code in SUPPORTED_LANGUAGES:
                return code
            
        # 4. Default
        return DEFAULT_LANGUAGE
    
    def _activate_timezone(self, request) -> None:
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and getattr(user, 'timezone', ''):
            try:
                tz = pytz.timezone(user.timezone)
                timezone.activate(tz)
                return
            except pytz.exceptions.UnknownTimeZoneError:
                pass
        timezone.deactivate()   # falls back to UTC
