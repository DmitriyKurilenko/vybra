from django.shortcuts import render
from django.http import Http404


# Страницы приложения (dashboard/compare/items/profile) обслуживает SPA
# (front_redesign). Server-rendered остаются только юридические документы.

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


def legal_document(request, doc):
    """Публичные юридические документы"""
    config = LEGAL_PAGES.get(doc)
    if not config:
        raise Http404("Документ не найден")

    return render(request, config['template'], {
        'page_title': config['title'],
    })
