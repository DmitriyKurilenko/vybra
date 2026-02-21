from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import Http404


LEGAL_PAGES = {
    'terms': {
        'template': 'legal/terms.html',
        'title': 'Пользовательское соглашение',
    },
    'privacy': {
        'template': 'legal/privacy.html',
        'title': 'Политика конфиденциальности',
    },
    'contacts': {
        'template': 'legal/contacts.html',
        'title': 'Сведения об операторе и контакты',
    },
}


def dashboard(request):
    """Главная страница с дашбордом"""
    return render(request, 'wishlist/dashboard.html')


def compare(request):
    """Страница сравнения товаров"""
    return render(request, 'wishlist/compare.html')


def items(request):
    """Страница управления товарами"""
    return render(request, 'wishlist/items.html')


def profile(request):
    """Страница профиля"""
    return render(request, 'wishlist/profile.html')


def legal_document(request, doc):
    """Публичные юридические документы"""
    config = LEGAL_PAGES.get(doc)
    if not config:
        raise Http404("Документ не найден")

    return render(request, config['template'], {
        'page_title': config['title'],
    })
