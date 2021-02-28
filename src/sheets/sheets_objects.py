import logging

from sheetfu.modules.table import Item
from typing import List

from ..consts import TrelloCardColor
from ..strings import load
from ..trello.trello_objects import CardCustomFields, TrelloCard


logger = logging.getLogger(__name__)


class RegistryPost:
    key_title_map = {
        'name': 'Название поста',
        'author': 'Автор',
        'rubric_1': 'Рубрика',
        'rubric_2': 'Доп.Рубрика',
        'google_doc': 'Гугл.док',
        'trello': 'Trello',
        'editor': 'Редактор',
        'cover_type': 'Тип обложки',
        'cover': 'Обложка',
        'illustrator': 'Иллюстратор',
        'date_site': 'Дата (сайт)',
        'status_site': 'Статус публикации (сайт)',
        'pin_site': '📌',
    }

    def __init__(
            self,
            card: TrelloCard,
            custom_fields: CardCustomFields,
            is_main_post: bool,
            is_archive_post: bool,
            all_rubrics: List,
    ):
        self.title = custom_fields.title
        self.authors = ','.join(custom_fields.authors)
        self.trello_url = card.url
        self.google_doc = custom_fields.google_doc
        self.editors = ','.join(custom_fields.editors)
        self.illustrators = ','.join(custom_fields.illustrators)
        self.cover = custom_fields.cover
        self.is_main_post = is_main_post
        self.is_archive_post = is_archive_post

        self._fill_rubrics(card, all_rubrics)

    def _fill_rubrics(self, card: TrelloCard, all_rubrics: List):
        # We filter BLACK cards as this is an auxiliary label
        card_rubrics = [
            label.name for label in card.labels
            if label.color != TrelloCardColor.BLACK
        ]
        self.rubric_1 = next((
            rubric.vk_tag for rubric in all_rubrics
            if rubric.name == card_rubrics[0]
        ), 'нет')
        self.rubric_2 = 'нет' if len(card_rubrics) == 1 else next((
            rubric.vk_tag for rubric in all_rubrics
            if rubric.name == card_rubrics[1]
        ), 'нет')

    def to_dict(self):
        return {
            RegistryPost.key_title_map['name']: self.title,
            RegistryPost.key_title_map['author']: self.authors,
            RegistryPost.key_title_map['rubric_1']: self.rubric_1,
            RegistryPost.key_title_map['rubric_2']: self.rubric_2,
            RegistryPost.key_title_map['google_doc']: self.google_doc,
            RegistryPost.key_title_map['trello']: self.trello_url,
            RegistryPost.key_title_map['editor']: self.editors,
            RegistryPost.key_title_map['cover_type']: 'нет' if self.is_archive_post else None,
            RegistryPost.key_title_map['cover']: 'нет' if self.is_archive_post else self.cover,
            RegistryPost.key_title_map['illustrator']: (
                'нет' if self.is_archive_post else self.illustrators
            ),
            RegistryPost.key_title_map['date_site']: 'нет' if self.is_archive_post else None,
            RegistryPost.key_title_map['status_site']: 'архив' if self.is_archive_post else None,
            RegistryPost.key_title_map['pin_site']: (
                'да' if not self.is_archive_post and self.is_main_post else 'нет'
            ),
        }


class HRPersonRaw:
    def __init__(self, item: Item):
        self.item = item # we need this for changing fields, TODO think about a generic approach
        self.ts = item.get_field_value(load('sheets__hr__timestamp'))
        self.name = item.get_field_value(load('sheets__hr__name'))
        self.interests = item.get_field_value(load('sheets__hr__interests'))
        self.other_contacts = item.get_field_value(load('sheets__hr__other_contacts'))
        self.about = item.get_field_value(load('sheets__hr__about'))
        self.email = item.get_field_value(load('sheets__hr__email'))
        self.telegram = item.get_field_value(load('sheets__hr__telegram'))
        self.status = item.get_field_value(load('sheets__hr__status'))
